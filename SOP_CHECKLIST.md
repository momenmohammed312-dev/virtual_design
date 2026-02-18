# Virtual Design SOP — Checklist تنفيذي

**التاريخ**: فبراير 18، 2026  
**الحالة**: جاري التنفيذ  
**الفرع**: `fix/python-bridge-sop`

---

## ✅ المراحل المنجزة

### المرحلة صفر ✓
- [x] إنشاء فرع جديد: `fix/python-bridge-sop`
- [x] التحضيرات الأساسية

### المرحلة 1 ✓
- [x] `requirements.txt` — جميع dependencies مُحددة
- [x] `install_deps.bat` — Windows installer
- [x] `install_deps.sh` — Linux/macOS installer
- [x] Python core pipeline كامل في `python/core/`
- [x] Commit: "Phase 1: Python core pipeline with requirements"

### المرحلة 2 ✓
- [x] تحسين `color_separator.py` لاستخدام LAB color space
- [x] تحسين ترتيب الألوان (من الأغمق للأفتح)
- [x] معالجة الخلفية البيضاء بشكل محسّن

---

## 🔄 المراحل الجارية / المتبقية

### المرحلة 3 — تحسين Mask Generation ⏳
- [ ] تحسين `mask_generator.py` مع معاملات قابلة للضبط
- [ ] دعم `--min-area` لإزالة الضجيج الصغير
- [ ] استخدام connected components مع filtering
- [ ] اختبار على مجموعة صور تمثيلية

**معايير القبول:**
- لا تختفي الأشكال الأساسية على صور gradient
- الضجيج الصغير يُزال دون فقد التفاصيل

### المرحلة 4 — Batch Processing & Parallelism ⏳
- [ ] إضافة دعم `--workers N` في CLI
- [ ] استخدام `multiprocessing.Pool` أو `concurrent.futures`
- [ ] معالجة ملفات متعددة بالتوازي
- [ ] تجنب منافسة I/O

**معايير القبول:**
- معالجة 20 صورة تظهر تحسين الأداء
- لا crashes بسبب منافسة I/O

### المرحلة 5 — Dependency Management ⏳
- [ ] التحقق من `requirements.txt` كامل ✓
- [ ] اختبار `install_deps.at` على Windows
- [ ] اختبار `install_deps.sh` على Linux/macOS
- [ ] (اختياري) Dockerfile بسيط

### المرحلة 6 — Dart ↔ Python Bridge ⏳
- [ ] استخدام `Process.start()` بدل `Process.run()`
- [ ] تحديث `python_processor.dart` لقراءة stdout سطراً سطراً
- [ ] تحديث بيئة Python: `PYTHONUNBUFFERED=1`
- [ ] معالجة أسطر `Step x/y` وآخر `OUTPUT_DIR:`
- [ ] معالجة الأخطاء مع error codes
- [ ] اختبار end-to-end

**معايير القبول:**
- Flutter يعرض progress حقيقي أثناء المعالجة
- عند الانتهاء يُستلَم path صالح في `outputDir`

### المرحلة 7 — License Service ⏳
- [ ] ✓ إضافة `crypto` dependency
- [ ] ✓ إضافة `library` directive في `license_service.dart`
- [ ] تطبيق ترخيص offline JSON-based
- [ ] SHA-256 validation
- [ ] شاشة License Required عند الحاجة

### المرحلة 8 — Android Permissions ⏳
- [ ] تحديث `AndroidManifest.xml` مع الـ permissions الصحيحة
- [ ] استخدام `permission_handler` لطلب الإذن وقت التشغيل
- [ ] على Android 13+: `READ_MEDIA_IMAGES`
- [ ] رسالة توضيحية عند الرفض

### المرحلة 9 — Error Handling ⏳
- [ ] تعريف error codes مركزية
- [ ] `ProcessingErrorScreen` widget
- [ ] عرض رسائل واضحة مع retry options
- [ ] تسجيل logs للتشخيص

### المرحلة 10 — Tests & CI ⏳
- [ ] Python unit tests مع pytest
- [ ] Dart widget tests
- [ ] إعداد CI (GitHub Actions)

### المرحلة 11 — QA & Acceptance ⏳
- [ ] اختبار end-to-end كامل
- [ ] اختبار performance على صور 4K
- [ ] التأكد من عدم وجود crashes

### المرحلة 12 — تحسينات متقدمة (اختياري) 🚀
- [ ] KMeans pre-clustering
- [ ] Palette merging
- [ ] CMYK separations (إن احتُجت)
- [ ] UI presets وstatus history

---

## ملفات مطلوبة للتسليم

### Python
- [x] `python/core/color_separator.py` ✓
- [x] `python/core/mask_generator.py` ✓
- [x] `python/core/edge_cleaner.py` ✓
- [ ] `python/core/halftone_generator.py`
- [ ] `python/core/binarizer.py`
- [ ] `python/main.py` (محسّن)
- [x] `requirements.txt` ✓
- [x] `install_deps.bat` ✓
- [x] `install_deps.sh` ✓

### Dart
- [ ] `lib/core/python_bridge/python_processor.dart` (محسّن)
- [ ] `lib/core/python_bridge/python_config.dart`
- [x] `lib/core/licensing/license_service.dart` ✓
- [ ] Error handling widgets
- [ ] Permission handler implementation

### Tests
- [ ] `test/python/test_color_separator.py`
- [ ] `test/python/test_mask_generator.py`
- [ ] `test/dart/` (tests)
- [ ] `.github/workflows/ci.yml` (CI)

### Config
- [ ] `AndroidManifest.xml` (محدّث)
- [ ] `Dockerfile` (اختياري)
- [ ] `docker-compose.yml` (اختياري)

---

## خطوات المتابعة الفورية

### الآن:
1. ✓ اختبار `main.py` محلياً:
   ```bash
   python python/main.py --input samples/test.jpg --output out --colors 4
   ```
   
   إذا كانت النتيجة:
   - خروج code 0 ✓
   - آخر سطر يبدأ بـ `OUTPUT_DIR:` ✓
   - → انتقل للخطوة التالية

2. [ ] تحسين `python_processor.dart` لاستخدام `Process.start()` وليس `Process.run()`

3. [ ] إضافة معالجة الأخطاء والـ error codes

4. [ ] اختبار دورة كاملة: Flutter → Python → جاهز الملفات

---

## معايير النجاح الكلية

- [ ] كل مرحلة تنتهي ب-commit واضح
- [ ] لا warnings كبيرة في الكود
- [ ] tests تمر بنجاح
- [ ] end-to-end test: صور 5 × 2K في < 30 ثانية
- [ ] استهلاك الذاكرة < 500MB
- [ ] بدون crashes غير مُدارة

---

## ملاحظات إضافية

- استخدم `print(..., flush=True)` في Python
- شغّل Python مع `PYTHONUNBUFFERED=1`
- كل تغيير بـ-commit صغير واضح
- نسخة احتياطية من المستودع قبل دمج الـ PR
