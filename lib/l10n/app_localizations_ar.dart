// Arabic localizations for Virtual Design app

import 'app_localizations.dart';

class AppLocalizationsAr extends AppLocalizations {
  AppLocalizationsAr();

  @override
  String get appName => 'المصمم الافتراضي';

  // Dashboard
  @override
  String get dashboard => 'لوحة التحكم';
  @override
  String get dashboardOverview => 'نظرة عامة على لوحة التحكم';

  // Quick Actions
  @override
  String get newPrintJob => 'مهمة طباعة جديدة';
  @override
  String get uploadFile => 'رفع ملف';

  // Recent Projects
  @override
  String get recentProjects => 'المشاريع الحديثة';
  @override
  String get noRecentProjects => 'لا توجد مشاريع حديثة';
  @override
  String get startNewProject => 'بدء مشروع جديد';

  // My Folders
  @override
  String get myFolders => 'مجلدي / الملفات';
  @override
  String get folders => 'المجلدات';
  @override
  String get projects => 'المشاريع';
  @override
  String get exports => 'الصادرات';
  @override
  String get templates => 'القوالب';

  // Settings
  @override
  String get settings => 'الإعدادات';
  @override
  String get general => 'عام';
  @override
  String get darkMode => 'الوضع الداكن';
  @override
  String get notifications => 'الإشعارات';
  @override
  String get autoSave => 'حفظ تلقائي';
  @override
  String get highQualityPreview => 'معاينة عالية الجودة';
  @override
  String get processingDefaults => 'الإعدادات الافتراضية للمعالجة';
  @override
  String get outputFormat => 'صيغة الإخراج';
  @override
  String get dpi => 'دقة البكسل';
  @override
  String get language => 'اللغة';
  @override
  String get storage => 'التخزين';
  @override
  String get outputDirectory => 'دليل الإخراج';
  @override
  String get clearCache => 'مسح ذاكرة التخزين المؤقت';
  @override
  String get resetAllSettings => 'إعادة تعيين جميع الإعدادات';
  @override
  String get about => 'حول';
  @override
  String get appVersion => 'إصدار التطبيق';
  @override
  String get developer => 'المطور';
  @override
  String get license => 'الترخيص';

  // Upload
  @override
  String get selectImage => 'اختر صورة للمعالجة';
  @override
  String get pickFromGallery => 'اختر من المعرض';
  @override
  String get pickFromFiles => 'اختر من الملفات';

  // Setup
  @override
  String get printAndSystemSetup => 'إعداد الطباعة والنظام';
  @override
  String get configureParameters => 'قم بتكوين معلمات الطباعة ونوع التشطيب وإعدادات الجودة أدناه.';
  @override
  String get colorComplexity => '1. تعقيد الألوان';
  @override
  String get auto => 'تلقائي';
  @override
  String colors(int count) => count == 1 ? 'لون واحد' : '$count ألوان';

  @override
  String get printType => '2. نوع الطباعة';
  @override
  String get detailLevel => 'مستوى التفاصيل';
  @override
  String get printFinish => 'تشطيب الطباعة';
  @override
  String get solid => 'صلب';
  @override
  String get halftone => 'نقطي';
  @override
  String get strokeWidth => 'عرض الخط (مم)';
  @override
  String get specifications => 'المواصفات';
  @override
  String get paperSize => 'حجم الورق';
  @override
  String get copies => 'نسخ';
  @override
  String get advancedSettings => 'إعدادات متقدمة';
  @override
  String get autoUpscale => 'تكبير تلقائي';
  @override
  String get removeBackground => 'إزالة الخلفية';
  @override
  String get edgeEnhancement => 'تحسين الحواف';
  @override
  String get colorCorrection => 'تصحيح الألوان';
  @override
  String get outputDir => 'دليل الإخراج';
  @override
  String get processImage => 'معالجة الصورة';
  @override
  String get back => 'رجوع';
  @override
  String get next => 'التالي';

  // Preview
  @override
  String get printPreview => 'معاينة الطباعة';
  @override
  String get reviewSeparations => 'راجع فصل الألوان والأفلام قبل التصدير.';
  @override
  String get colorLayers => 'طبقات الألوان';
  @override
  String get exportAll => 'تصدير الكل';
  @override
  String get sendToPrint => 'إرسال للطباعة';
  @override
  String get backToSetup => 'العودة للإعدادات';

  // Print Type Selection
  @override
  String get selectPrintType => 'اختر نوع الطباعة';
  @override
  String get choosePrintingMethod => 'اختر طريقة الطباعة التي تناسب مشروعك بشكل أفضل.';
  @override
  String get screenPrinting => 'طباعة الشاشة';
  @override
  String get dtf => 'DTF';
  @override
  String get sublimation => 'سublimation';
  @override
  String get flexVinyl => 'فليكس / فينيل';
  @override
  String get dtg => 'DTG';
  @override
  String get embroidery => 'تطريز';

  // Status
  @override
  String get complete => 'مكتمل';
  @override
  String get processing => 'قيد المعالجة';
  @override
  String get error => 'خطأ';
  @override
  String get failed => 'فشل';

  // Messages
  @override
  String get permissionRequired => 'مطلوب إذن';
  @override
  String get storagePermissionNeeded => 'مطلوب إذن التخزين لاختيار الصور';
  @override
  String get unsupportedFormat => 'صيغة غير مدعومة';
  @override
  String get imageProcessingError => 'خطأ في معالجة الصورة';
  @override
  String get noImageSelected => 'لم يتم اختيار صورة';
  @override
  String get pleaseUploadImage => 'يرجى رفع صورة أولاً.';
  @override
  String get cacheCleared => 'تم مسح ذاكرة التخزين المؤقت';
  @override
  String get settingsReset => 'تم إعادة تعيين الإعدادات';

  // Units
  @override
  String get mm => 'مم';
  @override
  String get cm => 'سم';
  @override
  String get inches => 'بوصة';
}
