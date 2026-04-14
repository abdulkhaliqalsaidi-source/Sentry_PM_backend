# تحسينات مشغل الفيديو - Session Replay Improvements

## المشكلة الأصلية
كان تسجيل الفيديو يظهر فقط جزء صغير من الصفحة (شريط رمادي) بدلاً من الموقع الكامل.

## الأسباب
1. **Buffer صغير جداً**: كان يحتفظ بـ 50 حدث فقط و 20 ثانية
2. **فقدان Full Snapshot**: كان يتم حذف اللقطة الكاملة للصفحة
3. **فقدان Meta Event**: لم يكن محمياً من الحذف
4. **عدم وجود Snapshot عند الخطأ**: لم يكن يأخذ لقطة كاملة عند حدوث خطأ

## التحسينات المطبقة

### 1. تحسينات SDK (client_sdk.js)

#### زيادة سعة Buffer
```javascript
// قبل: 20 ثانية، 50 حدث
const BUFFER_WINDOW_MS = 20000;
if (this.eventsBuffer.length > 50)

// بعد: 60 ثانية، 200 حدث
const BUFFER_WINDOW_MS = 60000;
if (this.eventsBuffer.length > 200)
```

#### حماية الأحداث الحرجة
- حماية Meta Event (type 4) من الحذف
- حماية آخر Full Snapshot (type 2) من الحذف
- تتبع وقت آخر Full Snapshot

#### تحسين إعدادات التسجيل
```javascript
recorder.record({
    maskAllInputs: false,
    maskTextSelector: '.sensitive',
    blockSelector: '.no-record',
    checkoutEveryNms: 10000, // Full snapshot كل 10 ثواني
    recordCanvas: true,
    collectFonts: true,
    inlineStylesheet: true,
    inlineImages: false, // لتقليل الحجم
    sampling: {
        scroll: 150,
        input: 'last',
        mousemove: true,
        mouseInteraction: true
    }
});
```

#### أخذ Full Snapshot عند الخطأ
```javascript
// إذا لم يكن هناك Full Snapshot، أخذ واحد قبل إرسال الخطأ
if (!hasSnapshot && rrweb.record.takeFullSnapshot) {
    rrweb.record.takeFullSnapshot(true);
    setTimeout(() => this._sendErrorCapture(err), 500);
}
```

#### عدم مسح Buffer بعد الإرسال
```javascript
// قبل: كان يمسح الـ buffer بعد كل خطأ
this.eventsBuffer = [];

// بعد: يحتفظ بالـ buffer للأخطاء المستقبلية
const eventsToSend = [...this.eventsBuffer];
```

### 2. تحسينات مشغل الفيديو (Dashboard.vue)

#### إضافة Full Snapshot تلقائي
```javascript
// إذا كان Full Snapshot مفقوداً، يتم إنشاء واحد placeholder
if (!hasSnapshot) {
    processedEvents.splice(1, 0, {
        type: 2,
        data: {
            node: {
                // بنية HTML كاملة
            }
        }
    });
}
```

#### تحسين حساب الأبعاد
```javascript
const modalWidth = container.parentElement?.clientWidth || window.innerWidth * 0.9;
const maxWidth = Math.min(modalWidth - 40, 1600);
const scaleRatio = maxWidth / originalWidth;
const scaledHeight = Math.max(originalHeight * scaleRatio, 700);
```

#### إضافة Logging مفصل
```javascript
console.log('📹 Replay: Received', data.events.length, 'events');
console.log('📊 Event types:', eventTypes);
console.log('✅ Has Meta:', hasMeta, '| Has Snapshot:', hasSnapshot);
```

#### تحسين إعدادات المشغل
```javascript
new rrwebPlayer({
    target: container,
    props: {
        events: processedEvents,
        width: maxWidth,
        height: scaledHeight,
        autoPlay: true,
        showController: true,
        skipInactive: false,
        speed: 1,
        replayerConfig: {
            UNSAFE_replayCanvas: true,
            mouseTail: {
                duration: 500,
                lineCap: 'round',
                lineWidth: 2,
                strokeStyle: 'red'
            }
        }
    }
});
```

### 3. تحسينات CSS

#### تصميم جديد للمشغل
- خلفية gradient جذابة
- ظلال وتأثيرات حديثة
- تحسين مظهر التحكمات
- رسائل خطأ أفضل
- تحذيرات متحركة

```css
.player-container {
    min-height: 700px;
    max-height: 85vh;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

.replay-warning-overlay {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.95) 0%, rgba(251, 146, 60, 0.95) 100%);
    animation: slideDown 0.4s ease-out;
}
```

## النتائج المتوقعة

✅ تسجيل الموقع بالكامل مع جميع العناصر
✅ احتفاظ بالبيانات لمدة 60 ثانية
✅ حماية الأحداث الحرجة من الحذف
✅ أخذ Full Snapshot تلقائي عند الأخطاء
✅ مشغل فيديو بتصميم احترافي
✅ رسائل خطأ واضحة ومفيدة
✅ Logging مفصل للتشخيص

## الاختبار

1. افتح الموقع في المتصفح
2. قم بإثارة خطأ (مثلاً: اضغط على زر Test Simulator)
3. افتح Issues → اضغط على Replay
4. يجب أن ترى الموقع الكامل مع جميع العناصر

## ملاحظات

- حجم Buffer الآن أكبر (60 ثانية بدلاً من 20)
- يتم أخذ Full Snapshot كل 10 ثواني
- الأحداث الحرجة محمية من الحذف
- يتم أخذ Snapshot تلقائي عند الأخطاء
- التصميم الجديد أكثر احترافية

## الملفات المعدلة

1. `client_sdk.js` - تحسينات SDK
2. `frontend/src/components/Dashboard.vue` - تحسينات المشغل
3. `frontend/src/locales/ar.json` - ترجمات عربية
4. `frontend/src/locales/en.json` - ترجمات إنجليزية
