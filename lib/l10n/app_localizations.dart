import 'package:flutter/material.dart';
import 'app_localizations_en.dart';
import 'app_localizations_ar.dart';

/// Localized strings for the Virtual Design app.
/// Supports English (default) and Arabic.
abstract class AppLocalizations {
  /// The delegate that will be used to load the localized strings.
  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// The list of supported locales.
  static const List<Locale> supportedLocales = [
    Locale('en'), // English
    Locale('ar'), // Arabic
  ];

  /// Get an instance of the localizations for the current context.
  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  // ─── Common UI Strings ───────────────────────────────────────────────────────

  /// App name
  String get appName;

  /// Dashboard
  String get dashboard;
  String get dashboardOverview;
  
  /// Quick Actions
  String get newPrintJob;
  String get uploadFile;
  
  /// Recent Projects
  String get recentProjects;
  String get noRecentProjects;
  String get startNewProject;
  
  /// My Folders
  String get myFolders;
  String get folders;
  String get projects;
  String get exports;
  String get templates;
  
  /// Settings
  String get settings;
  String get general;
  String get darkMode;
  String get notifications;
  String get autoSave;
  String get highQualityPreview;
  String get processingDefaults;
  String get outputFormat;
  String get dpi;
  String get language;
  String get storage;
  String get outputDirectory;
  String get clearCache;
  String get resetAllSettings;
  String get about;
  String get appVersion;
  String get developer;
  String get license;
  
  /// Upload
  String get selectImage;
  String get pickFromGallery;
  String get pickFromFiles;
  
  /// Setup
  String get printAndSystemSetup;
  String get configureParameters;
  String get colorComplexity;
  String get auto;
  String colors(int count);
  String get printType;
  String get detailLevel;
  String get printFinish;
  String get solid;
  String get halftone;
  String get strokeWidth;
  String get specifications;
  String get paperSize;
  String get copies;
  String get advancedSettings;
  String get autoUpscale;
  String get removeBackground;
  String get edgeEnhancement;
  String get colorCorrection;
  String get outputDir;
  String get processImage;
  String get back;
  String get next;
  
  /// Preview
  String get printPreview;
  String get reviewSeparations;
  String get colorLayers;
  String get exportAll;
  String get sendToPrint;
  String get backToSetup;
  
  /// Print Type Selection
  String get selectPrintType;
  String get choosePrintingMethod;
  String get screenPrinting;
  String get dtf;
  String get sublimation;
  String get flexVinyl;
  String get dtg;
  String get embroidery;
  
  /// Status
  String get complete;
  String get processing;
  String get error;
  String get failed;
  
  /// Messages
  String get permissionRequired;
  String get storagePermissionNeeded;
  String get unsupportedFormat;
  String get imageProcessingError;
  String get noImageSelected;
  String get pleaseUploadImage;
  String get cacheCleared;
  String get settingsReset;
  
  /// Units
  String get mm;
  String get cm;
  String get inches;
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) async {
    // Load any necessary resources for the locale
    await Future<void>.delayed(Duration.zero);
    
    if (locale.languageCode == 'ar') {
      return AppLocalizationsAr();
    }
    return AppLocalizationsEn(); // Default to English
  }

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;

  @override
  bool isSupported(Locale locale) =>
      AppLocalizations.supportedLocales.map((l) => l.languageCode).contains(locale.languageCode);
}
