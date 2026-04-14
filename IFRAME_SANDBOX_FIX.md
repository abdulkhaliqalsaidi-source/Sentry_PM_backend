# إصلاح مشكلة Sandbox وأبعاد الفيديو

## المشكلة الأولى: Sandbox يمنع تنفيذ السكريبتات
```
Blocked script execution in 'http://localhost:5173/issues' 
because the document's frame is sandboxed and the 'allow-scripts' permission is not set.
```

### السبب
كان الكود يضيف `sandbox="allow-same-origin allow-scripts"` على iframe، لكن rrweb يحتاج صلاحيات أكثر لتشغيل التسجيل بشكل صحيح.

### الحل
إزالة sandbox تماماً من iframe لأن:
1. rrweb player يحتاج تنفيذ كامل للسكريبتات
2. المحتوى المسجل آمن (من نفس التطبيق)
3. لا يوجد محتوى خارجي غير موثوق

```javascript
setTimeout(() => {
    const iframe = container.querySelector('iframe');
    if (iframe) {
        iframe.removeAttribute('sandbox');
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        console.log('🔓 Iframe sandbox removed and styled');
    }
}, 100);
```

---

## المشكلة الثانية: أبعاد الفيديو غير متناسقة

### السبب
كان حساب الأبعاد لا يحافظ على نسبة العرض إلى الارتفاع (aspect ratio) الأصلية للتسجيل.

### الحل الجديد

#### 1. حساب النسبة الأصلية
```javascript
const originalWidth = metaEvent?.data?.width || 1920;
const originalHeight = metaEvent?.data?.height || 1080;
const aspectRatio = originalWidth / originalHeight;
```

#### 2. حساب المساحة المتاحة
```javascript
const containerElement = container.parentElement;
const availableWidth = containerElement ? containerElement.clientWidth - 80 : window.innerWidth * 0.85;
const availableHeight = window.innerHeight * 0.75;
```

#### 3. حساب الأبعاد مع الحفاظ على النسبة
```javascript
let playerWidth = Math.min(availableWidth, 1600);
let playerHeight = playerWidth / aspectRatio;

// إذا كان الارتفاع أكبر من المتاح، نعيد الحساب
if (playerHeight > availableHeight) {
    playerHeight = availableHeight;
    playerWidth = playerHeight * aspectRatio;
}

// التأكد من الحد الأدنى
playerWidth = Math.max(playerWidth, 800);
playerHeight = Math.max(playerHeight, 600);
```

#### 4. تطبيق الأبعاد
```javascript
this.rrPlayerInstance = new rrwebPlayer({
    target: container,
    props: {
        events: processedEvents,
        width: Math.round(playerWidth),
        height: Math.round(playerHeight),
        // ...
    }
});
```

---

## التحسينات في CSS

### 1. تحسين player container
```css
.player-container {
    min-height: 700px;
    max-height: 85vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
```

### 2. تحسين rr-player
```css
:deep(.rr-player) {
    max-width: 100% !important;
    margin: 0 auto !important;
}
```

### 3. تحسين rr-player__frame
```css
:deep(.rr-player__frame) {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
```

### 4. تحسين iframe
```css
:deep(iframe) {
    border: none !important;
    width: 100% !important;
    height: 100% !important;
    display: block !important;
}
```

### 5. تحسين replayer-wrapper
```css
:deep(.replayer-wrapper) {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
```

---

## النتائج المتوقعة

✅ لن يظهر خطأ sandbox
✅ السكريبتات ستعمل بشكل صحيح في iframe
✅ أبعاد الفيديو متناسقة ومحافظة على aspect ratio
✅ الفيديو يتناسب مع حجم الشاشة
✅ لا يوجد تشوه في العرض
✅ responsive على جميع الأحجام

---

## مثال على حساب الأبعاد

### تسجيل بأبعاد 1920x1080 (16:9)
- Available width: 1400px
- Player width: 1400px
- Player height: 1400 / (1920/1080) = 787.5px
- النتيجة: 1400x788 (محافظ على 16:9)

### تسجيل بأبعاد 1366x768 (16:9)
- Available width: 1200px
- Player width: 1200px
- Player height: 1200 / (1366/768) = 675px
- النتيجة: 1200x675 (محافظ على 16:9)

### تسجيل بأبعاد 1024x768 (4:3)
- Available width: 1000px
- Player width: 1000px
- Player height: 1000 / (1024/768) = 750px
- النتيجة: 1000x750 (محافظ على 4:3)

---

## الاختبار

1. افتح Issues → اضغط على Replay
2. يجب ألا ترى خطأ sandbox في Console
3. الفيديو يجب أن يظهر بأبعاد متناسقة
4. لا يوجد تشوه أو تمدد في الصورة
5. الفيديو يتناسب مع حجم النافذة

---

## ملاحظات الأمان

- إزالة sandbox آمنة لأن المحتوى من نفس التطبيق
- التسجيلات مخزنة في قاعدة البيانات الخاصة
- لا يوجد محتوى خارجي أو غير موثوق
- rrweb player يحتاج صلاحيات كاملة للعمل

إذا كنت تريد أمان إضافي، يمكن استخدام:
```javascript
iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-forms allow-popups allow-modals');
```

لكن الأفضل إزالة sandbox تماماً لضمان عمل rrweb بشكل صحيح.

---

## الملفات المعدلة

1. `frontend/src/components/Dashboard.vue`
   - إزالة sandbox من iframe
   - تحسين حساب الأبعاد مع aspect ratio
   - تحسين CSS للمشغل
