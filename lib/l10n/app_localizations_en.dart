// English localizations for Virtual Design app

import 'app_localizations.dart';

class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn();

  @override
  String get appName => 'Virtual Designer';

  // Dashboard
  @override
  String get dashboard => 'Dashboard';
  @override
  String get dashboardOverview => 'Dashboard Overview';

  // Quick Actions
  @override
  String get newPrintJob => 'New Print Job';
  @override
  String get uploadFile => 'Upload File';

  // Recent Projects
  @override
  String get recentProjects => 'Recent Projects';
  @override
  String get noRecentProjects => 'No recent projects';
  @override
  String get startNewProject => 'Start New Project';

  // My Folders
  @override
  String get myFolders => 'My Folders / Files';
  @override
  String get folders => 'Folders';
  @override
  String get projects => 'Projects';
  @override
  String get exports => 'Exports';
  @override
  String get templates => 'Templates';

  // Settings
  @override
  String get settings => 'Settings';
  @override
  String get general => 'General';
  @override
  String get darkMode => 'Dark Mode';
  @override
  String get notifications => 'Notifications';
  @override
  String get autoSave => 'Auto Save';
  @override
  String get highQualityPreview => 'High Quality Preview';
  @override
  String get processingDefaults => 'Processing Defaults';
  @override
  String get outputFormat => 'Output Format';
  @override
  String get dpi => 'DPI';
  @override
  String get language => 'Language';
  @override
  String get storage => 'Storage';
  @override
  String get outputDirectory => 'Output Directory';
  @override
  String get clearCache => 'Clear Cache';
  @override
  String get resetAllSettings => 'Reset All Settings';
  @override
  String get about => 'About';
  @override
  String get appVersion => 'App Version';
  @override
  String get developer => 'Developer';
  @override
  String get license => 'License';

  // Upload
  @override
  String get selectImage => 'Select Image to Process';
  @override
  String get pickFromGallery => 'Pick from Gallery';
  @override
  String get pickFromFiles => 'Pick from Files';

  // Setup
  @override
  String get printAndSystemSetup => 'Print & System Setup';
  @override
  String get configureParameters => 'Configure your print job parameters, finish type, and quality settings below.';
  @override
  String get colorComplexity => '1. Color Complexity';
  @override
  String get auto => 'Auto';
  @override
  String colors(int count) => count == 1 ? '1 Color' : '$count Colors';

  @override
  String get printType => '2. Print Type';
  @override
  String get detailLevel => 'Detail Level';
  @override
  String get printFinish => 'Print Finish';
  @override
  String get solid => 'Solid';
  @override
  String get halftone => 'Halftone';
  @override
  String get strokeWidth => 'Stroke Width (mm)';
  @override
  String get specifications => 'Specifications';
  @override
  String get paperSize => 'Paper Size';
  @override
  String get copies => 'Copies';
  @override
  String get advancedSettings => 'Advanced Settings';
  @override
  String get autoUpscale => 'Auto Upscale';
  @override
  String get removeBackground => 'Remove Background';
  @override
  String get edgeEnhancement => 'Edge Enhancement';
  @override
  String get colorCorrection => 'Color Correction';
  @override
  String get outputDir => 'Output Directory';
  @override
  String get processImage => 'Process Image';
  @override
  String get back => 'Back';
  @override
  String get next => 'Next';

  // Preview
  @override
  String get printPreview => 'Print Preview';
  @override
  String get reviewSeparations => 'Review your color separations and films before exporting.';
  @override
  String get colorLayers => 'Color Layers';
  @override
  String get exportAll => 'Export All';
  @override
  String get sendToPrint => 'Send to Print';
  @override
  String get backToSetup => 'Back to Setup';

  // Print Type Selection
  @override
  String get selectPrintType => 'Select Print Type';
  @override
  String get choosePrintingMethod => 'Choose the printing method that best suits your project.';
  @override
  String get screenPrinting => 'Screen Printing';
  @override
  String get dtf => 'DTF';
  @override
  String get sublimation => 'Sublimation';
  @override
  String get flexVinyl => 'Flex/Vinyl';
  @override
  String get dtg => 'DTG';
  @override
  String get embroidery => 'Embroidery';

  // Status
  @override
  String get complete => 'Complete';
  @override
  String get processing => 'Processing';
  @override
  String get error => 'Error';
  @override
  String get failed => 'Failed';

  // Messages
  @override
  String get permissionRequired => 'Permission Required';
  @override
  String get storagePermissionNeeded => 'Storage permission is needed to select images';
  @override
  String get unsupportedFormat => 'Unsupported format';
  @override
  String get imageProcessingError => 'Image Processing Error';
  @override
  String get noImageSelected => 'No Image Selected';
  @override
  String get pleaseUploadImage => 'Please upload an image first.';
  @override
  String get cacheCleared => 'Cache Cleared';
  @override
  String get settingsReset => 'Settings Reset';

  // Units
  @override
  String get mm => 'mm';
  @override
  String get cm => 'cm';
  @override
  String get inches => 'inches';
}
