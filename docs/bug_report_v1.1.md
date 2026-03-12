Virtual Design
Silk Screen Studio

Bug Report & Technical Fix Documentation
Version 1.1  —  March 2026

Bugs Fixed	3
Python Fixes	3
Flutter Fixes	2
New Features

Project	Virtual Design — Silk Screen Studio
Repository	github.com/momenmohammed312-dev/virtual_design
Stack	Flutter / Dart (frontend)  +  Python (image pipeline)
Architecture	Clean Architecture + GetX state management
Report Date	March 2026
Status	ALL BUGS RESOLVED — Patch ready

1. Executive Summary
هذا التقرير يوثّق ست مشاكل تم اكتشافها وإصلاحها في تطبيق Virtual Design - Silk Screen Studio. المشاكل تمتد عبر طبقتين: Python image processing pipeline و Flutter presentation layer. المشاكل أدّت إلى خروج output فاضٍ من الصور، وعدم عمل أدوات التكبير، وعدم عرض الألوان الفعلية في الـ preview، وعدم عمل زر Export كـ PDF، وعدم وجود زرّ رجوع في شاشة Print Type، وعدم تعامل صحيح مع Printer.
تم تحليل الكود المصدري بالكامل — Python pipeline (9 خطوات) وكل شاشات Flutter — لتحديد الأسباب الجذرية لكل مشكلة وتطبيق إصلاح دقيق لكل منها دون المساس بالمنطق الأصلي للكود.

1.1 ملخص المشاكل والإصلاحات
CRITICAL	Bug #1 — Output فاضي: الـ masks كانت مقلوبة (design أبيض على خلفية سودا)
CRITICAL	Bug #2 — PDF vector بيطلع فاضي: exporter كان بيقرأ الـ mask بشكل خاطئ بعد الـ inversion
HIGH	Bug #3 — Zoom/Fit لا تعمل: الأزرار كانت stubbed (onPressed: () {})
HIGH	Bug #4 — Color Layers لا تعرض الألوان الحقيقية: color_info.json لم يُقرأ
MEDIUM	Bug #5 — Export Films لا تفتح الـ PDF: الدالة كانت مجرد snackbar
MEDIUM	Bug #6 — Send to Print وPrint Type: لا رجوع ولا رسالة "no printer"

2. بيئة التطوير والتقنيات
2.1 Technology Stack
Frontend	Flutter 3.x + Dart + GetX 4.6+ (Clean Architecture + MVC)

Backend	Python 3.x — pipeline يتضمن: OpenCV, NumPy, Pillow, scikit-image, reportlab, svgwrite

Architecture	Clean Architecture: Presentation → Domain ← Data + Python IPC bridge

Communication	Flutter تُطلق Python process وتقرأ stdout سطراً بسطر (PROGRESS / OUTPUT_DIR)

Export	reportlab (vector PDF) + OpenCV (PNG) + registration marks على كل فيلم
2.2 Python Pipeline — الخطوات التسع
1.	Step 1: Load Image — تحميل الصورة بـ robust loader
2.	Step 2: Color Separation — K-Means clustering في LAB color space
3.	Step 3: Mask Generation — binary masks لكل لون
4.	Step 4: Edge Cleaning — morphological operations
5.	Step 5: Halftone — (اختياري) توليد halftone dots
6.	Step 6: Binarize — threshold للحصول على صورة أبيض وأسود
7.	Step 7: Stroke Validation — التحقق من أحجام الخطوط
8.	Step 8: Registration Marks — إضافة علامات التسجيل
9.	Step 9: Export — حفظ كـ PDF vector أو PNG

3. تفاصيل المشاكل والإصلاحات
BUG #1  [CRITICAL]  Output فاضي — الـ Masks مقلوبة

الملف	python/main.py  (step 6 → step 8)

التأثير	كل الـ output files بتطلع بيضاء تماماً — بس registration marks بيبانوا

الخطورة	CRITICAL — التطبيق غير قابل للاستخدام
الشرح التقني للمشكلة
عملية K-Means clustering في الـ ColorSeparator تُرجع labels للـ pixels. عند بناء الـ mask في MaskGenerator، يتم تعيين mask[label_map == i] = 255 للـ pixels التابعة لكل لون — أي الـ design يظهر بالأبيض (255) على خلفية سودا (0).
هذا منطقي من الناحية الرياضية لـ K-Means، لكنه عكس المعيار الصناعي لـ silk screen films:
•	Film صح = design أسود (0) على خلفية بيضاء (255)
•	Film خاطئ = design أبيض (255) على خلفية سودا (0)  ← ما كان موجود
عندما يُضاف الـ white border في الخطوة التالية (registration marks)، والـ design نفسه أبيض — النتيجة صورة بيضاء كاملة. الـ registration marks الموجودة في الـ border بتبان لأنها رُسمت بالأسود في منطقة البوردر البيضاء — لكن الصورة نفسها فاضية.
الإصلاح المُطبَّق
تمت إضافة خطوة inversion صريحة في main.py بعد Step 7 (Stroke Validation) وقبل Step 8 (Registration Marks):
# Invert masks: silk screen films need design=BLACK on WHITE background.
# K-means produces design=255 (white) on background=0 (black).
logger.info("Inverting masks for standard film output")
inverted = []
for m in masks:
    if len(m.shape) == 3:
        gray = cv2.cvtColor(m, cv2.COLOR_BGR2GRAY)
    else:
        gray = m
    inverted.append(cv2.bitwise_not(gray))
masks = inverted
بعد الـ inversion: design = أسود (0)، خلفية = أبيضاء (255) — النتيجة films صحيحة قابلة للطباعة مباشرة.

BUG #2  [CRITICAL]  PDF Vector بيطلع فاضي — Exporter يقرأ الـ Mask بشكل خاطئ

الملف	python/core/vector_exporter.py — دالة export_vector_pdf

التأثير	الـ PDF يُنشأ لكنه بيحتوي على صفحات بيضاء بدون design

الخطورة	CRITICAL — PDF export معطل كلياً
الشرح التقني للمشكلة
بعد إصلاح Bug #1 (inversion)، الـ masks تصل لـ exporter بشكل صحيح (design=أسود). لكن الـ vector_exporter كان يستخدم:
# الكود القديم — خاطئ
_, bw = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(bw, ...)
المشكلتان هنا:
•	THRESH_BINARY: يُعطي 255 للـ pixels فوق 127 — أي الخلفية البيضاء. الـ findContours يجد حدود الخلفية وليس الـ design.
•	الـ mask بعد Registration Marks يكون BGR (3-channel) بسبب add_marks() في OpenCV — لكن الـ exporter يعامله كـ grayscale مباشرة.
الإصلاح المُطبَّق
في الـ exporter، قبل الـ threshold، تمت إضافة تحويل BGR→Grayscale وقلب الـ threshold:
# الكود الجديد — صحيح
# Convert to single-channel (handles BGR from registration marks step)
if len(mask.shape) == 3:
    gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
else:
    gray = mask.copy()

# THRESH_BINARY_INV: design=255 (for contour detection), bg=0
_, bw = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

BUG #3  [HIGH]  Zoom / Fit to Screen لا تعمل

الملف	lib/presentation/preview/preview_page.dart + preview_controller.dart

التأثير	أزرار Zoom In / Zoom Out / Fit to Screen لا تفعل شيئاً

الخطورة	HIGH — UX معطوبة — المستخدم لا يمكنه فحص الـ film بدقة
الشرح التقني للمشكلة
الأزرار الثلاثة في الـ Preview header كانت كلها:
// الكود القديم — stubbed بدون وظيفة
IconButton(onPressed: () {},  // ← لا شيء!
  icon: const Icon(Icons.zoom_in))
بالإضافة لذلك، لم يكن هناك أي InteractiveViewer للـ image — الصورة كانت Image.file() مباشرة بدون إمكانية zoom أو pan.
الإصلاح المُطبَّق
في الـ PreviewController، تمت إضافة:
•	TransformationController لربط حالة الـ zoom
•	RxDouble zoomLevel لعرض النسبة المئوية
•	دوال zoomIn() وzoomOut() وfitToScreen()
// controller — zoom methods
final TransformationController transformationController
    = TransformationController();
final RxDouble zoomLevel = 1.0.obs;

void zoomIn()  => _applyZoom((zoomLevel.value * 1.3).clamp(0.5, 5.0));
void zoomOut() => _applyZoom((zoomLevel.value / 1.3).clamp(0.5, 5.0));
void fitToScreen() {
  zoomLevel.value = 1.0;
  transformationController.value = Matrix4.identity();
}
وفي الـ page، الصورة أُحيطت بـ InteractiveViewer مع ربطه بالـ controller:
// preview_page.dart
ClipRect(
  child: InteractiveViewer(
    transformationController: controller.transformationController,
    minScale: 0.5,
    maxScale: 5.0,
    child: Image.file(File(path), fit: BoxFit.contain),
  ),
)

BUG #4  [HIGH]  Color Layers لا تعرض الألوان الحقيقية

الملف	lib/presentation/preview/preview_controller.dart + preview_page.dart

التأثير	الـ Layers panel يعرض "Film 1", "Film 2" بدون ألوان — المستخدم لا يعرف أي فيلم لأي لون

الخطورة	HIGH — معلومات الألوان الأساسية غائبة
الشرح التقني للمشكلة
Python pipeline يحفظ ملف color_info.json في مجلد الـ output في كل عملية. هذا الملف يحتوي على:
// color_info.json — مثال
{
  "num_colors": 3,
  "colors": [
    { "index": 0, "name": "color_01", "rgb": [10, 8, 12],
      "hex": "#0A080C", "percentage": 45.2 },
    { "index": 1, "name": "color_02", "rgb": [180, 60, 20],
      "hex": "#B43C14", "percentage": 32.8 },
    { "index": 2, "name": "color_03", "rgb": [240, 200, 50],
      "hex": "#F0C832", "percentage": 22.0 }
  ]
}
لكن الـ PreviewController القديم لم يكن يقرأ هذا الملف إطلاقاً. الـ Layers panel كان يعرض thumbnail صغيرة من الـ PNG فقط، بدون معلومات اللون الحقيقي أو نسبة التغطية.
الإصلاح المُطبَّق
تمت إضافة:
•	ColorLayerInfo data class لتمثيل بيانات كل لون
•	_loadColorInfo() يُستدعى بعد _loadFilms() لقراءة الـ JSON
•	colorInfoForFilm(index) لاسترجاع لون فيلم معين
// preview_controller.dart
Future<void> _loadColorInfo() async {
  final jsonFile = File("\${outputDirectory.value}/color_info.json");
  if (await jsonFile.exists()) {
    final data = json.decode(await jsonFile.readAsString());
    colorLayers.value = (data["colors"] as List)
        .map((c) => ColorLayerInfo.fromJson(c)).toList();
  }
}
الـ Layers panel الآن يعرض:
•	Color swatch ملوّن بالـ RGB الحقيقي من الصورة
•	HEX code اللون (مثال: #B43C14)
•	نسبة التغطية (مثال: 32.8% coverage)

BUG #5  [MEDIUM]  Export Films لا تفتح الـ PDF

الملف	lib/presentation/preview/preview_controller.dart — دالة exportAll()

التأثير	زر Export Films و Export All لا يفعلان شيئاً مفيداً

الخطورة	MEDIUM — الـ files موجودة لكن لا يوجد وصول لها
الشرح التقني للمشكلة
الدالة القديمة كانت:
// الكود القديم — لا يفعل شيئاً مفيداً
Future<void> exportAll() async {
  // In a real implementation, you would package all films...
  await Future.delayed(const Duration(seconds: 2));
  Get.snackbar("Export Complete", "All films have been exported.");
}
المشكلة أن الـ films موجودة فعلاً في مجلد الـ output — الـ Python pipeline حفظها هناك. الكود كان بحاجة فقط لفتح المجلد أو فتح الـ PDF مباشرة بالـ system viewer.
الإصلاح المُطبَّق
// الكود الجديد — يفتح المجلد أو الـ PDF مباشرة
Future<void> exportAll() async {
  if (filmPaths.isEmpty) { ... return; }

  // Try to open output directory (Finder/Explorer)
  final result = await OpenFile.open(outputDirectory.value);
  if (result.type == ResultType.done) return;

  // Fallback: open first PDF or first film
  final pdfPaths = filmPaths.where((p) => p.endsWith(".pdf")).toList();
  final target = pdfPaths.isNotEmpty ? pdfPaths.first : filmPaths.first;
  final r2 = await OpenFile.open(target);
  if (r2.type != ResultType.done) {
    Get.snackbar("Files Saved At", outputDirectory.value, ...);
  }
}

BUG #6  [MEDIUM]  Print Type: لا رجوع + Send to Print بلا رسالة

الملف	select_print_type_screen.dart + preview_controller.dart — sendToPrint()

التأثير	(أ) لا يوجد زرّ رجوع من شاشة Print Type — المستخدم محاصر. (ب) Send to Print لا يُخبر المستخدم بأنه لا توجد طابعة متصلة.

الخطورة	MEDIUM — تجربة مستخدم سيئة ومُربِكة
المشكلة أ — لا رجوع من شاشة Print Type
شاشة Select Print Type لم تكن تحتوي على أي زرّ للرجوع في الـ top bar. بمجرد الدخول إليها، المستخدم لا يستطيع العودة إلا إذا أختار print type ونُقل لشاشة أخرى.
الإصلاح أ
// select_print_type_screen.dart — top bar
Row(children: [
  IconButton(
    onPressed: () => Get.back(),  // ← الإصلاح
    icon: const Icon(Icons.arrow_back_ios_new, size: 18),
    color: Color(0xFF1564A5),
  ),
  Text("Select Print Type", style: ...),
  ...
])
المشكلة ب — Send to Print لا يُبلغ عن غياب الطابعة
الزرّ القديم:
// الكود القديم
onPressed: () {
  Get.snackbar("Send to Print",
    "Sending \${controller.filmPaths.length} films to printer...");
}
المشكلة: الرسالة تُوهم المستخدم بأن الطباعة تجري بينما لا شيء يُرسل فعلاً.
الإصلاح ب
تمت كتابة دالة sendToPrint() كاملة في الـ controller:
// preview_controller.dart — sendToPrint()
Future<void> sendToPrint() async {
  final pdfPaths = filmPaths
      .where((p) => p.toLowerCase().endsWith(".pdf")).toList();

  // لو مافيش PDF → dialog واضح
  if (pdfPaths.isEmpty) {
    Get.dialog(AlertDialog(
      title: Text("No PDF for Printing"),
      content: Text("A PDF file is needed to send to printer..."),
      ...
    ));
    return;
  }

  // حاول فتح system print dialog
  final result = await OpenFile.open(pdfPaths.first);
  if (result.type != ResultType.done) {
    // لو فشل → dialog "No Printer Detected"
    Get.dialog(AlertDialog(
      title: Text("No Printer Detected"),
      content: Text("Please open the file manually:\n\${pdfPaths.first}"),
      ...
    ));
  }
}

4. الملفات المُعدَّلة
الملف	النوع	التغيير
python/main.py	Python	إضافة خطوة Inversion للـ masks (Bug #1)
python/core/vector_exporter.py	Python	تحويل BGR→Gray + THRESH_BINARY_INV (Bug #2)
lib/presentation/preview/preview_controller.dart	Flutter	Zoom + color_info loading + export + print (Bugs #3,4,5,6)
lib/presentation/preview/preview_page.dart	Flutter	InteractiveViewer + zoom % + color swatches (Bugs #3,4)
lib/presentation/print_type/select_print_type_screen.dart	Flutter	إضافة Back button في top bar (Bug #6)

5. كيفية تطبيق الإصلاحات
5.1 الحزمة الجاهزة
تم تجميع المشروع الكامل مع جميع الإصلاحات في ملف واحد:
virtual_design_fixed.zip

# الملف يحتوي على كامل المشروع مع الإصلاحات الستة مطبَّقة
5.2 خطوات التشغيل
10.	فك ضغط الملف: unzip virtual_design_fixed.zip
11.	تثبيت Python dependencies (إن لم تكن مثبّتة):
cd python
pip install -r requirements.txt
# أو
pip install opencv-python numpy Pillow scikit-image scipy reportlab svgwrite
12.	تشغيل التطبيق من مجلد Flutter:
cd virtual_design_fixed
flutter pub get
flutter run
13.	للتحقق من عمل الـ Python pipeline مباشرة:
cd python
python main.py --input /path/to/image.png --output /tmp/test_output --colors 3
# يجب أن تجد في /tmp/test_output:
# - films_combined.pdf  (design أسود على خلفية بيضاء)
# - color_info.json     (معلومات الألوان)
5.3 التحقق من نجاح الإصلاحات
ما يجب التحقق منه	النتيجة المتوقعة
Output فيلم PNG	✓  Design أسود واضح على خلفية بيضاء
Output فيلم PDF	✓  Vector paths صحيحة تمثل الـ design
زر Zoom In	✓  الصورة تكبر وتُعرض النسبة: 130%
زر Fit to Screen	✓  الصورة ترجع لـ 100%
Color Layers panel	✓  Color swatches ملوّنة + HEX + نسبة التغطية
زر Export Films	✓  يفتح مجلد الـ output أو الـ PDF
زر Send to Print	✓  يفتح system print dialog أو dialog "No Printer"
Print Type — Back	✓  زرّ السهم يعود للـ Preview بدون مشكلة

6. ملاحظات معمارية وتوصيات
6.1 الدرس المستفاد من Bug #1 — Mask Convention
المشكلة الجذرية في Bug #1 ليست في K-Means أو المنطق الرياضي — بل في غياب تحديد واضح لـ "film convention" في الكود. ينصح بإضافة تعليق ثابت في أعلى كل دالة تتعامل مع الـ masks:
# CONVENTION: All masks follow silk-screen film standard:
#   - Design pixels:     0   (black)
#   - Background pixels: 255 (white)
# Any function that changes this MUST re-invert before returning.
6.2 الدرس المستفاد من Bug #4 — State Sync
في GetX، الحالة المحلية (local variables) لا تتزامن تلقائياً مع الـ observable state في الـ controller. هذه قاعدة صلبة:
•	أي بيانات تحتاجها الـ UI يجب أن تكون observable (.obs) في الـ controller
•	لا تقرأ ملفات (JSON/files) في الـ View — اقرأها دائماً في الـ controller ضمن onInit() أو بعد العملية مباشرة
•	حافظ على Single Source of Truth: filmPaths + colorLayers كلاهما في PreviewController
6.3 توصية — اختبار Integration
ينصح بإضافة integration test بسيط يغطي الـ happy path كاملاً:
// integration_test/pipeline_test.dart (مقترح)
// 1. Upload image
// 2. Select 3 colors, halftone=false
// 3. Process (run Python pipeline)
// 4. Verify output directory contains:
//    - films_combined.pdf (non-empty)
//    - color_info.json with 3 entries
//    - PNG files with black design on white bg
// 5. Open Preview page → verify color swatches visible
6.4 توصية — إضافة Color Convention Test
اختبار وحدة Python للتحقق من الـ mask convention بعد كل تعديل:
# tests/test_mask_convention.py (مقترح)
def test_masks_are_black_on_white():
    """Verify masks follow silk-screen convention."""
    image = cv2.imread("tests/test_samples/sample.png")
    result = ColorSeparator().separate(image, num_colors=2)
    masks = MaskGenerator().generate_masks(image, result)
    # After inversion in main.py:
    for mask in masks:
        # Background (most common) should be white
        assert mask.mean() > 127, "Background should be white (>127)"


Virtual Design — Silk Screen Studio  |  Bug Report v1.1
6 bugs fixed  |  5 files modified  |  March 2026
github.com/momenmohammed312-dev/virtual_design
