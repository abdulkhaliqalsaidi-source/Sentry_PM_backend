(function (window) {
    // Immediate Debug: Log script execution
    console.log("Tracker: script loaded. Window keys:", Object.keys(window).length);
    console.log("Tracker: Checking for rrweb immediately...", typeof window.rrweb);
    if (window.rrweb) console.log("Tracker: rrweb keys:", Object.keys(window.rrweb));

    // Polyfill for Element.matches (fix rrweb error)
    if (typeof Element !== 'undefined' && Element.prototype && !Element.prototype.matches) {
        Element.prototype.matches = 
            Element.prototype.matchesSelector || 
            Element.prototype.mozMatchesSelector ||
            Element.prototype.msMatchesSelector || 
            Element.prototype.oMatchesSelector || 
            Element.prototype.webkitMatchesSelector ||
            function(s) {
                try {
                    var matches = (this.document || this.ownerDocument).querySelectorAll(s),
                        i = matches.length;
                    while (--i >= 0 && matches.item(i) !== this) {}
                    return i > -1;
                } catch (e) {
                    return false;
                }
            };
        console.log("✅ Element.matches polyfill applied globally");
    }

    // Default Configuration
    const DEFAULT_CONFIG = {
        trackerUrl: 'http://127.0.0.1:3535', // Base URL of your Django server
        project: 'Default Project',
        userId: 'guest_' + Math.random().toString(36).substr(2, 5)
    };

    const Tracker = {
        config: { ...DEFAULT_CONFIG },
        sessionId: 'sess_' + Math.random().toString(36).substr(2, 9),

        eventsBuffer: [],
        networkBuffer: [],
        consoleBuffer: [],
        breadcrumbs: [],
        fullSnapshotIndex: -1,
        MAX_BUFFER_SIZE: 100,

        /**
         * Initialize the Tracker
         * @param {Object} options - { trackerUrl, project, userId }
         */
        init: function (options = {}) {
            // Merge config
            this.config = { ...this.config, ...options };

            console.log("Tracker Initialized:", this.config);

            // Prevent double initialization of background tasks
            if (this._initialized) {
                console.warn("Tracker: Already initialized, skipping setup.");
                return;
            }
            this._initialized = true;

            console.log("Session ID:", this.sessionId);

            // إصلاح مشكلة matches في rrweb
            this.patchDOMMatches();

            try {
                this.startRecording();
                this.startNetworkLogging();
                this.startConsoleLogging();

                // Periodic flush REMOVED as per user request (restore online behavior: send on error only)
                // setInterval(() => {
                //     this.flushEvents();
                // }, 5000);

            } catch (e) {
                console.error("Tracker: Failed to start recording", e);
            }
            this.setupGlobalHandlers();
            this.setupBreadcrumbs();
        },

        /**
         * إصلاح مشكلة matches في DOM elements
         */
        patchDOMMatches: function() {
            // التأكد من أن جميع عناصر DOM لديها دالة matches
            if (typeof Element !== 'undefined' && Element.prototype) {
                if (!Element.prototype.matches) {
                    Element.prototype.matches = 
                        Element.prototype.matchesSelector || 
                        Element.prototype.mozMatchesSelector ||
                        Element.prototype.msMatchesSelector || 
                        Element.prototype.oMatchesSelector || 
                        Element.prototype.webkitMatchesSelector ||
                        function(s) {
                            var matches = (this.document || this.ownerDocument).querySelectorAll(s),
                                i = matches.length;
                            while (--i >= 0 && matches.item(i) !== this) {}
                            return i > -1;            
                        };
                }
            }
            
            // حماية إضافية: التأكد من أن Node.prototype لديه matches
            if (typeof Node !== 'undefined' && Node.prototype && !Node.prototype.matches) {
                Node.prototype.matches = function(selector) {
                    if (!this.nodeType || this.nodeType !== 1) return false;
                    if (!Element.prototype.matches) return false;
                    try {
                        return Element.prototype.matches.call(this, selector);
                    } catch (e) {
                        return false;
                    }
                };
            }
            
            // حماية MutationObserver من الأخطاء
            if (typeof MutationObserver !== 'undefined') {
                const OriginalMutationObserver = window.MutationObserver;
                window.MutationObserver = function(callback) {
                    return new OriginalMutationObserver(function(mutations, observer) {
                        try {
                            callback(mutations, observer);
                        } catch (e) {
                            console.warn("MutationObserver callback error (ignored):", e.message);
                        }
                    });
                };
                window.MutationObserver.prototype = OriginalMutationObserver.prototype;
            }
            
            console.log("✅ DOM matches polyfill and MutationObserver protection applied");
        },

        /**
         * Start rrweb recording
         */
        startRecording: function () {
            let recorder = window.rrweb;

            if (!recorder && typeof rrweb !== 'undefined') {
                recorder = rrweb;
            }

            console.log("Tracker: Checking for rrweb...", recorder ? "Found" : "Missing", typeof recorder);

            if (!recorder) {
                console.warn("Tracker Warning: rrweb not found on window. Waiting for load...");
                if (window.rrweb && window.rrweb.rrweb) recorder = window.rrweb.rrweb;
            }

            if (!recorder) {
                console.error("Tracker Critical Error: rrweb object is completely missing. Script likely failed to load.");
                return;
            }

            if (!recorder.record) {
                console.error("Tracker Critical Error: rrweb found but .record() is missing. Keys:", Object.keys(recorder));
                return;
            }

            console.log("Tracker: rrweb found, starting recording with 60s buffer...");

            // Rolling buffer: keep last 60 seconds
            const BUFFER_WINDOW_MS = 60000;
            let lastFullSnapshotTime = Date.now();

            try {
                // Wrap rrweb.record with error handling
                const recordConfig = {
                    emit: (event) => {
                        // تصفية الأحداث الفاسدة
                        try {
                            this.eventsBuffer.push(event);

                            // تتبع آخر Full Snapshot
                            if (event.type === 2) {
                                lastFullSnapshotTime = Date.now();
                                console.log("📸 Full Snapshot captured at", new Date(event.timestamp).toLocaleTimeString());
                            }

                            // Time-based trim مع حماية Meta و Full Snapshot
                            if (this.eventsBuffer.length > 200) {
                                const now = Date.now();
                                const cutoffTime = now - BUFFER_WINDOW_MS;

                                // البحث عن آخر Full Snapshot
                                let lastSnapshotIdx = -1;
                                for (let i = this.eventsBuffer.length - 1; i >= 0; i--) {
                                    if (this.eventsBuffer[i].type === 2) {
                                        lastSnapshotIdx = i;
                                        break;
                                    }
                                }

                                // البحث عن Meta event
                                let metaEventIdx = -1;
                                for (let i = 0; i < this.eventsBuffer.length; i++) {
                                    if (this.eventsBuffer[i].type === 4) {
                                        metaEventIdx = i;
                                        break;
                                    }
                                }

                                // حذف الأحداث القديمة مع حماية Meta و Snapshot
                                let trimTo = 0;
                                for (let i = 0; i < this.eventsBuffer.length; i++) {
                                    // حماية Meta event وآخر Full Snapshot
                                    if (i === metaEventIdx || i === lastSnapshotIdx) {
                                        break;
                                    }
                                    if (this.eventsBuffer[i].timestamp < cutoffTime && i < lastSnapshotIdx) {
                                        trimTo = i + 1;
                                    } else {
                                        break;
                                    }
                                }
                                if (trimTo > 0) {
                                    console.log(`🗑️ Trimming ${trimTo} old events, keeping ${this.eventsBuffer.length - trimTo}`);
                                    this.eventsBuffer.splice(0, trimTo);
                                }
                            }
                        } catch (e) {
                            console.warn("Tracker: Error processing event, skipping:", e.message);
                        }
                    },
                    maskAllInputs: false,
                    maskTextSelector: '.sensitive, .password, [type="password"]',
                    blockSelector: '.no-record, .sensitive-data',
                    checkoutEveryNms: 10000,
                    recordCanvas: true,
                    collectFonts: true,
                    inlineStylesheet: true,
                    inlineImages: false,
                    sampling: {
                        scroll: 150,
                        input: 'last',
                        mousemove: true,
                        mouseInteraction: true
                    }
                };

                // Wrap the record call to catch internal rrweb errors
                let stopFn;
                try {
                    stopFn = recorder.record(recordConfig);
                } catch (recordError) {
                    console.error("❌ rrweb.record() failed:", recordError);
                    // Try again with minimal config
                    console.log("🔄 Retrying with minimal config...");
                    stopFn = recorder.record({
                        emit: recordConfig.emit,
                        maskAllInputs: false,
                        checkoutEveryNms: 10000
                    });
                }
                
                console.log("✅ Tracker: rrweb.record started successfully");
                console.log("📊 Recording config: 60s buffer, 200 events max, Full Snapshot every 10s");
                
                // أخذ Full Snapshot فوري عند البداية
                setTimeout(() => {
                    if (recorder.record && recorder.record.takeFullSnapshot) {
                        recorder.record.takeFullSnapshot(true);
                        console.log("📸 Initial Full Snapshot taken");
                    }
                }, 1000);
                
            } catch (e) {
                console.error("Tracker: Error starting rrweb", e);
            }
        },

        /**
         * Start intercepting Network Requests (Fetch & XHR)
         */
        startNetworkLogging: function () {
            const self = this;

            // --- Intercept Fetch ---
            const originalFetch = window.fetch;
            window.fetch = async function (...args) {
                const startTime = Date.now();
                let url = args[0];
                if (url) {
                    if (typeof url !== 'string') {
                        if (url.url) url = url.url; // Request object
                        else if (url.href) url = url.href; // URL object
                        else if (url.toString) url = url.toString();
                    }
                }

                // Ensure plain string for comparison
                const urlString = String(url);

                const isTrackerRequest = urlString && (
                    urlString.includes(self.config.trackerUrl) ||
                    urlString.includes('/api/capture/') ||
                    urlString.includes('/api/session/')
                );

                if (isTrackerRequest) {
                    // console.debug("Tracker: Ignoring internal request", urlString);
                    return originalFetch.apply(this, args);
                }

                // Debugging recursion if it happens
                if (urlString && urlString.includes('capture')) {
                    console.warn("Tracker: WARNING - Capture request NOT ignored!", urlString, self.config.trackerUrl);
                }

                try {
                    const response = await originalFetch.apply(this, args);
                    const duration = Date.now() - startTime;

                    self.networkBuffer.push({
                        type: 'fetch',
                        method: args[1]?.method || 'GET',
                        url: url,
                        status: response.status,
                        duration: duration,
                        timestamp: startTime
                    });
                    console.log("Tracker: Captured Fetch", url, response.status);

                    // Auto-capture Network Errors (400+)
                    if (response.status >= 400) {
                        const netErr = new Error(`HTTP ${response.status} ${response.statusText || 'Error'} at ${url}`);
                        netErr.name = 'NetworkError';
                        self.captureException(netErr);
                    }

                    return response;
                } catch (error) {
                    const duration = Date.now() - startTime;
                    self.networkBuffer.push({
                        type: 'fetch',
                        method: args[1]?.method || 'GET',
                        url: url,
                        status: 0, // Network error
                        duration: duration,
                        timestamp: startTime,
                        error: error.message
                    });

                    // Capture underlying network failure (e.g. offline)
                    const netErr = new Error(`Network Request Failed: ${error.message} at ${url}`);
                    netErr.name = 'NetworkError';
                    self.captureException(netErr);

                    throw error;
                }
            };

            // --- Intercept XHR ---
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function (method, url) {
                this._tracker_metadata = { method, url, startTime: Date.now() };
                return originalOpen.apply(this, arguments);
            };

            XMLHttpRequest.prototype.send = function () {
                const meta = this._tracker_metadata;
                const urlString = meta && meta.url ? String(meta.url) : '';

                if (!meta || (urlString && (
                    urlString.includes(self.config.trackerUrl) ||
                    urlString.includes('/api/capture/') ||
                    urlString.includes('/api/session/')
                ))) {
                    return originalSend.apply(this, arguments);
                }

                this.addEventListener('loadend', () => {
                    const duration = Date.now() - meta.startTime;
                    self.networkBuffer.push({
                        type: 'xhr',
                        method: meta.method,
                        url: meta.url,
                        status: this.status,
                        duration: duration,
                        timestamp: meta.startTime
                    });

                    // Auto-capture XHR Errors
                    if (this.status >= 400) {
                        const netErr = new Error(`HTTP ${this.status} Error at ${meta.url}`);
                        netErr.name = 'NetworkError';
                        self.captureException(netErr);
                    }
                });

                return originalSend.apply(this, arguments);
            };
        },

        /**
         * Compress data using Gzip (if supported)
         * @param {string} dataVal 
         * @returns {Promise<{data: BodyInit, encoding: string}>}
         */
        compressData: async function (dataVal) {
            // Check if CompressionStream is available
            if (typeof CompressionStream !== 'undefined' && typeof Response !== 'undefined') {
                try {
                    const stream = new ManualCompressionStream('gzip'); // Use a polyfill or check if native
                    // Actually native is new CompressionStream('gzip')
                    // But to be safe and simple, let's use the native one if it exists

                    const cs = new CompressionStream('gzip');
                    const writer = cs.writable.getWriter();
                    writer.write(new TextEncoder().encode(dataVal));
                    writer.close();
                    return {
                        data: await new Response(cs.readable).blob(),
                        encoding: 'gzip'
                    };
                } catch (e) {
                    console.warn("Tracker: Compression failed, falling back to JSON", e);
                }
            }
            return { data: dataVal, encoding: '' };
        },

        /**
         * Send buffered rrweb events to the server
         */
        flushEvents: async function () {
            if (this.eventsBuffer.length === 0) {
                // console.debug("Tracker: Buffer empty, nothing to flush"); 
                return;
            }
            console.log(`Tracker: Flushing ${this.eventsBuffer.length} events to server...`);

            const eventsToSend = [...this.eventsBuffer];
            this.eventsBuffer = []; // Clear buffer

            const sessionEndpoint = `${this.config.trackerUrl}/api/session/`;

            const payload = JSON.stringify({
                session_id: this.sessionId,
                events: eventsToSend,
                network_logs: this.networkBuffer.splice(0, this.networkBuffer.length),
                console_logs: this.consoleBuffer.splice(0, this.consoleBuffer.length)
            });

            try {
                const { data, encoding } = await this.compressData(payload);
                const headers = { 'Content-Type': 'application/json' };
                if (encoding) headers['Content-Encoding'] = encoding;

                await fetch(sessionEndpoint, {
                    method: 'POST',
                    headers: headers,
                    body: data
                });
            } catch (e) {
                console.error('Tracker: Session Upload Failed', e);
            }
        },

        /**
         * Manually capture an exception
         * @param {Error} err 
         */
        captureException: function (err) {
            const errorMsg = err.message || '';
            if (errorMsg.includes('[HMR]') || errorMsg.includes('Hot Module Replacement') || errorMsg.includes('webpackHotUpdate')) {
                console.debug("Tracker: Ignoring HMR error");
                return;
            }

            // Prevent duplicate capture
            if (err.__tracker_captured) {
                console.debug("Tracker: Ignoring already captured error");
                return;
            }
            
            try {
                Object.defineProperty(err, '__tracker_captured', {
                    value: true,
                    enumerable: false,
                    writable: true
                });
            } catch (e) {
                err.__tracker_captured = true;
            }

            console.log("🚨 Tracker: Capturing Exception...", err.name, err.message);

            // التحقق من وجود Full Snapshot في الأحداث
            const hasSnapshot = this.eventsBuffer.some(e => e.type === 2);
            const hasMeta = this.eventsBuffer.some(e => e.type === 4);
            
            console.log("📊 Buffer status: Events:", this.eventsBuffer.length, "| Has Meta:", hasMeta, "| Has Snapshot:", hasSnapshot);

            // إذا لم يكن هناك Full Snapshot، أخذ واحد الآن
            if (!hasSnapshot && typeof rrweb !== 'undefined' && rrweb.record && rrweb.record.takeFullSnapshot) {
                console.log("📸 Taking emergency Full Snapshot before error capture...");
                rrweb.record.takeFullSnapshot(true);
                // انتظار قليل للسماح بإضافة الـ snapshot للـ buffer
                setTimeout(() => this._sendErrorCapture(err), 500);
                return;
            }

            this._sendErrorCapture(err);
        },

        /**
         * Internal method to send error capture
         * @param {Error} err 
         */
        _sendErrorCapture: function(err) {
            // نسخ الأحداث الحالية
            const eventsToSend = [...this.eventsBuffer];
            
            // التحقق النهائي
            const hasSnapshot = eventsToSend.some(e => e.type === 2);
            const hasMeta = eventsToSend.some(e => e.type === 4);
            
            console.log("📤 Sending error with", eventsToSend.length, "events | Meta:", hasMeta, "| Snapshot:", hasSnapshot);

            // لا نقوم بمسح الـ buffer بعد الإرسال للحفاظ على البيانات للأخطاء المستقبلية
            // this.eventsBuffer = [];

            const captureEndpoint = `${this.config.trackerUrl}/api/capture/`;

            const body = JSON.stringify({
                project: this.config.project,
                type: err.name || 'UnknownError',
                message: err.message || 'No error message provided',
                stack: err.stack || 'No stack trace',
                url: window.location.href,
                user: this.config.userId,
                breadcrumbs: this.breadcrumbs,
                session_id: this.sessionId,
                events: eventsToSend,
                network_logs: [...this.networkBuffer], // نسخ بدون حذف
                console_logs: [...this.consoleBuffer]  // نسخ بدون حذف
            });

            const payloadSize = new Blob([body]).size;
            console.log(`📦 Payload size: ${(payloadSize / 1024).toFixed(2)} KB (${eventsToSend.length} events)`);

            this.compressData(body).then(async ({ data, encoding }) => {
                const headers = { 'Content-Type': 'application/json' };
                if (encoding) {
                    headers['Content-Encoding'] = encoding;
                    const compressedSize = data.size || data.length;
                    console.log(`🗜️ Compressed to: ${(compressedSize / 1024).toFixed(2)} KB`);
                }

                try {
                    const res = await fetch(captureEndpoint, {
                        method: 'POST',
                        headers: headers,
                        body: data
                    });

                    if (res.ok) {
                        console.log("✅ Error sent successfully");
                    } else {
                        console.error("❌ Error send failed:", res.status, res.statusText);
                    }
                } catch (e) {
                    console.error('❌ Failed to send error', e);
                    console.error('API Config:', this.config);
                }
            });
        },

        /**
         * Setup global error handlers (window.onerror, unhandledrejection)
         */
        setupGlobalHandlers: function () {
            const originalOnError = window.onerror;
            window.onerror = (msg, url, lineNo, columnNo, error) => {
                if (error) {
                    this.captureException(error);
                } else {
                    // Fallback if error object is missing
                    this.captureException(new Error(msg));
                }
                if (originalOnError) originalOnError(msg, url, lineNo, columnNo, error);
            };

            window.addEventListener('unhandledrejection', (event) => {
                this.captureException(event.reason || new Error('Unhandled Rejection'));
            });

            this.setupConsoleHandlers(); // Keep usage for now, but implementation will be replaced or this line removed if merged.
            // Actually, let's remove this call since we call startConsoleLogging in init explicitly now?
            // Wait, setupGlobalHandlers is called in init. Let's remove setupConsoleHandlers call here
            // and rely on startConsoleLogging called in init.
        },

        /**
         * Intercept console.error calls
         */
        /**
         * Intercept Console logs (Log, Info, Warn, Error)
         */
        startConsoleLogging: function () {
            const levels = ['log', 'info', 'warn', 'error', 'debug'];
            levels.forEach(level => {
                const original = console[level];
                console[level] = (...args) => {
                    // Call original
                    original.apply(console, args);

                    // Avoid recursion
                    if (args.length > 0 && typeof args[0] === 'string' && args[0].startsWith('Tracker:')) return;

                    // Buffer
                    this.consoleBuffer.push({
                        level: level,
                        args: args.map(a => {
                            try {
                                return typeof a === 'object' ? JSON.stringify(a) : String(a);
                            } catch (e) { return '[Circular]'; }
                        }),
                        timestamp: Date.now()
                    });

                    // For error, keep the captureException logic
                    if (level === 'error') {
                        if (args.length > 0 && args[0] instanceof Error) {
                            this.captureException(args[0]);
                            return;
                        }

                        // Construct error from args if not an Error object
                        const message = args.map(arg => {
                            if (arg instanceof Error) return arg.message;
                            if (typeof arg === 'object') return JSON.stringify(arg);
                            return String(arg);
                        }).join(' ');

                        const error = new Error(message);
                        error.name = 'ConsoleError';
                        error.stack = new Error().stack;
                        this.captureException(error);
                    }
                };
            });
        },

        // Legacy/Duplicate - empty it or remove. We replaced it with startConsoleLogging
        setupConsoleHandlers: function () { },

        /**
         * Track clicks as breadcrumbs
         */
        setupBreadcrumbs: function () {
            document.addEventListener('click', (e) => {
                this.breadcrumbs.push({
                    type: 'click',
                    target: e.target.tagName.toLowerCase() + (e.target.id ? '#' + e.target.id : ''),
                    time: new Date().toISOString()
                });
                if (this.breadcrumbs.length > 20) this.breadcrumbs.shift();
            });
        }
    };

    // Expose to window
    window.Tracker = Tracker;

})(window);
