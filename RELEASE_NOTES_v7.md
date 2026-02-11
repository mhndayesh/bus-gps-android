# 🌟 الإصدار السابع (v7) - آمن مدرستي
**تاريخ الإصدار:** 11 فبراير 2026

يسعدنا الإعلان عن إطلاق التحديث الجديد لنظام تتبع الحافلات المدرسية، والذي يركز بشكل أساسي على **تحسين تجربة النقل المدرسي** وجعلها أكثر سلاسة وموثوقية للإدارة والسائقين.

---

## � أبرز التحديثات (للإدارة)

### 1. 🗺️ المسار الذكي والمنظم
في السابق، كان ترتيب الطلاب في المسار قد يظهر بشكل عشوائي. الآن، قمنا ببرمجة النظام ليختار **أقصر وأقرب مسار** تلقائياً بناءً على موقع السائق الحالي.
**النتيجة:** توفير في الوقت والوقود، ومسارات منطقية وسهلة للسائقين.

### 2. 📍 تحديث فوري للمواقع
يمكن للمشرفين الآن تعديل موقع منزل الطالب من لوحة التحكم، وسيتم **تحديث مسار السائق فوراً** وهو في الطريق. لا داعي لإعادة تشغيل الرحلة أو الانتظار لليوم التالي.

### 3. 📱 أداة فحص ذاتي للسائقين
أضفنا شاشة صغيرة داخل تطبيق السائق توضح حالة النظام. في حال وجود مشكلة، يمكن للسائق معرفة السبب (مثل ضعف الإنترنت) فوراً دون الحاجة لانتظار الدعم الفني.

### 4. 🛠️ إصلاحات عامة
- حل مشكلة ظهور الطالب كأنه "داخل الحافلة" بعد نزوله.
- تحسين سرعة التطبيق واستجابته للأوامر بشكل ملحوظ.

---

# �🚀 Release Notes v7-landmark (Technical)
**Date:** February 11, 2026

This release uses the tag `v7-landmark` and focuses on stability, route optimization, and debugging tools.

## ✨ What's New
- **Nearest Neighbor Routing:** Smart algorithm to sort stops by proximity, eliminating "zigzag" routes.
- **Real-Time Location Sync:** Admin updates to student locations now instantly propagate to active trips.
- **On-Screen Debug Console:** Built-in log overlay in the Driver App for easier troubleshooting on mobile devices.

## ⚡ Technical Improvements
- **Manifest Denormalization:** Student data is now cached in the manifest for faster querying.
- **Robustness:** Decoupled route calculation from main DB to prevent locks and errors.
- **Docker Optimization:** Reduced build size by ~90% for faster deployments.

**Upgrade Instructions:**
```bash
git pull origin main
docker-compose up -d --build
```
