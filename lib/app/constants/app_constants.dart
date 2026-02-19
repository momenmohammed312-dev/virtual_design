// app_constants.dart — App-wide Constants
// Virtual Design Silk Screen Studio
//
// MED #4 FIX: حُذِفَ منه static const lightTheme / darkTheme
//             استخدم AppTheme.darkTheme من app_theme.dart دائماً
//
// القاعدة: app_theme.dart هو المصدر الوحيد لكل theme values.

class AppConstants {
  AppConstants._();

  // ─── App Info ─────────────────────────────────────────────────────────────
  static const String appName        = 'Virtual Design';
  static const String appSubtitle    = 'Silk Screen Studio';
  static const String appVersion     = '1.1.0';
  static const String appBuildNumber = '11';

  // ─── Processing Limits ───────────────────────────────────────────────────
  static const int    minColors       = 1;
  static const int    maxColors       = 10;
  static const double minDpi          = 72;
  static const double maxDpi          = 1200;
  static const double defaultDpi      = 300;
  static const double minStrokeMm     = 0.1;
  static const double maxStrokeMm     = 10.0;
  static const double defaultStrokeMm = 0.3;

  // ─── Mesh Counts ─────────────────────────────────────────────────────────
  static const List<int> standardMeshCounts = [110, 160, 200, 230, 280, 355];
  static const int defaultMeshCount = 160;

  // ─── Halftone ────────────────────────────────────────────────────────────
  static const int    minLpi     = 25;
  static const int    maxLpi     = 85;
  static const int    defaultLpi = 65;

  // ─── Storage Keys (Hive) ─────────────────────────────────────────────────
  // ملاحظة: مُنقَّل لـ storage_keys.dart — موجود هنا للـ backwards compat فقط
  static const String projectsBox  = 'projects_box';
  static const String settingsBox  = 'settings_box';
  static const String licenseBox   = 'license_box';

  // ─── File Extensions ─────────────────────────────────────────────────────
  static const List<String> supportedImageFormats = [
    'png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'webp',
  ];
  static const List<String> exportFormats = ['png', 'pdf', 'svg', 'zip'];

  // ─── Python Pipeline ─────────────────────────────────────────────────────
  static const int  totalPipelineSteps = 9;
  static const int  processingTimeoutSeconds = 300; // 5 دقائق
  static const String outputDirPrefix = 'silk_output_';

  // ─── Demo / Fallback ─────────────────────────────────────────────────────
  static const bool showDemoOnError = false; // ← كان true، غُيِّر لـ false
  // (بعد إصلاح البريدج، نُظهر شاشة خطأ حقيقية بدل Demo)

  // ─── UI ──────────────────────────────────────────────────────────────────
  static const double maxContentWidth = 1100;
  static const double sidebarWidth    = 280;

  // ─── REMOVED (MED #4 FIX) ────────────────────────────────────────────────
  // كانت هنا قيم theme مكررة — حُذفت:
  //
  //   static const lightTheme = ...  ← محذوف
  //   static const darkTheme  = ...  ← محذوف
  //
  // استخدم بدلاً منها:
  //   AppTheme.darkTheme
  //   AppTheme.lightTheme
  //   AppColors.primary
  //   AppColors.surface1
  //   إلخ...
}
