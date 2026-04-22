// lib/presentation/setup/setup_controller.dart
// Fixes 2, 4, 7: Real UI values, dot_shape, temp file cleanup
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:get/get.dart';
import 'package:virtual_design/domain/entities/processing_settings.dart' as ps;
import 'package:virtual_design/domain/repositories/processing_repository.dart';
import 'package:virtual_design/core/utils/sound_manager.dart';
import 'package:virtual_design/core/mobile_ai/mobile_ai_service.dart';

class SetupController extends GetxController {
  final ProcessingRepository _repository;

  SetupController({required ProcessingRepository repository})
      : _repository = repository;

  // ─── Image paths ─────────────────────────────────────────────────────────
  final RxString imagePath = ''.obs;
  String _originalTempPath = ''; // for cleanup after processing

  // ─── Settings State ──────────────────────────────────────────────────────
  final RxInt selectedColors = 0.obs;
  final RxDouble strokeWidth = 0.5.obs; // mm
  final Rx<ps.DetailLevel> selectedDetail = ps.DetailLevel.medium.obs;
  final Rx<ps.PrintFinish> selectedFinish = ps.PrintFinish.solid.obs;
  final RxBool removeBackground = false.obs;
  final RxBool autoUpscale = false.obs;

  final RxDouble globalThreshold = 127.0.obs; // 0-255 (Magic solution)
  final RxDouble smoothingFactor = 35.0.obs; // 0-100%
  final RxDouble cornerThreshold = 45.0.obs; // 15-150°
  final RxInt smoothingSlider = 35.obs; // Legacy

  // Track if user manually moved these sliders
  bool smoothingAdjustmentMade = false;
  bool cornerAdjustmentMade = false;
  bool thresholdAdjustmentMade = false;

  // AI Auto-Fix controls
  final RxBool isAiAutoFix = true.obs; // Auto-adjust sliders by AI
  final RxInt selectedDpi = 1200.obs; // Default high DPI for halftone
  final RxString colorComplexity = 'Auto'.obs; // Auto or 1-8 colors

  // Available DPI options
  final List<int> dpiOptions = [150, 300, 450, 600, 750, 900, 1050, 1200];

  // Paper size
  final RxDouble paperWidthCm = 21.0.obs;
  final RxDouble paperHeightCm = 29.7.obs;

  // Print quality (DPI)
  final RxDouble printQuality = 300.0.obs;

  // Halftone settings
  final RxBool isHalftone = false.obs;
  // DYNAMIC LPI: Computed from DPI and Mesh (not stored, calculated on-the-fly)
  // Formula: LPI = min(DPI/2, Mesh/4.5) with safety limits 35-150
  int get lpiValue {
    final dpi = printQuality.value;
    final mesh = meshCount;
    // Ideal LPI from DPI (2:1 ratio for quality halftone)
    final lpiFromDpi = dpi / 2.0;
    // Max safe LPI from mesh (conservative 4.5 factor)
    final maxLpiFromMesh = mesh / 4.5;
    // Optimal is the lower of the two
    final optimalLpi =
        lpiFromDpi < maxLpiFromMesh ? lpiFromDpi : maxLpiFromMesh;
    // Clamp to safe range
    if (optimalLpi < 35) return 35;
    if (optimalLpi > 150) return 150;
    return optimalLpi.round();
  }

  final RxString selectedDotShape = 'round'.obs;
  final RxDouble dotSizeMultiplier = 1.0.obs;
  // Per-layer dot sizes
  final RxList<double> dotSizeMultipliers = <double>[].obs;

  // Edge enhancement & color correction
  final RxBool edgeEnhancement = false.obs;
  final RxBool colorCorrection = false.obs;
  final RxBool adaptiveThreshold = false.obs;
  final RxBool responsiveMode = false.obs;
  final Rx<ps.ImageType> selectedImageType = ps.ImageType.auto.obs;

  // Scaling & Sizing
  final RxDouble targetWidthMm = 0.0.obs;
  final RxInt sourceDpi = 300.obs;
  final RxString scaleMode = 'fit_to_page'.obs;
  final RxDouble customScalePercent = 100.0.obs;

  // Output directory selection
  final RxString outputDir = ''.obs;

  // Processing state
  final RxBool isProcessing = false.obs;
  final RxDouble progress = 0.0.obs;
  final RxString progressMessage = ''.obs;

  // ─── Computed ────────────────────────────────────────────────────────────

  /// Auto-calculate mesh count based on DPI only (not LPI - prevents circular dependency)
  /// Higher DPI needs higher mesh count for quality halftone
  /// EXTENDED: Support up to 4800 DPI for photo/engraving applications
  int get meshCount {
    final dpi = printQuality.value;
    // Select appropriate mesh based on DPI
    // For screen printing: realistic max is 355 (for 900-1200 DPI)
    // For photo/engraving: we return 355 but LPI formula handles the rest
    if (dpi <= 400) return 110; // Low res, basic mesh
    if (dpi <= 500) return 160; // Standard
    if (dpi <= 600) return 196; // Good quality
    if (dpi <= 800) return 230; // High quality
    if (dpi <= 1000) return 280; // Very high quality
    // Beyond 1200 DPI is for photo/engraving - mesh stays at max
    // LPI will be limited by mesh/4.5 formula
    return 355; // Maximum mesh count
  }

  // ─── Lifecycle ───────────────────────────────────────────────────────────

  @override
  void onInit() {
    super.onInit();
    final args = Get.arguments;
    if (args is String) {
      imagePath.value = args;
    } else if (args is Map) {
      imagePath.value = (args['imagePath'] as String?) ?? '';
      _originalTempPath = (args['originalPath'] as String?) ?? '';
    }
    _loadLastSettings();

    // Auto-update smoothingFactor and cornerThreshold based on selectedImageType
    ever(selectedImageType, (ps.ImageType type) {
      switch (type) {
        case ps.ImageType.simple:
          smoothingFactor.value = 25.0;
          cornerThreshold.value = 45.0;
          break;
        case ps.ImageType.mixed:
          smoothingFactor.value = 25.0;
          cornerThreshold.value = 45.0;
          break;
        case ps.ImageType.complex:
          smoothingFactor.value = 30.0;
          cornerThreshold.value = 50.0;
          break;
        case ps.ImageType.auto:
          smoothingFactor.value = 35.0;
          cornerThreshold.value = 45.0;
          break;
      }
      // Reset adjustment flags when image type changes to allow engine defaults
      smoothingAdjustmentMade = false;
      cornerAdjustmentMade = false;
    });
  }

  Future<void> _loadLastSettings() async {
    final settings = await _repository.loadLastSettings();
    if (settings != null) {
      selectedColors.value = settings.colorCount;
      selectedDetail.value = settings.detailLevel;
      selectedFinish.value = settings.printFinish;
      isHalftone.value = (settings.printFinish == ps.PrintFinish.halftone);
      strokeWidth.value = settings.strokeWidthMm;
      printQuality.value = settings.dpi;
      adaptiveThreshold.value = settings.adaptiveThreshold;
      responsiveMode.value = settings.responsiveMode;
      selectedImageType.value = settings.imageType;
      smoothingSlider.value = settings.smoothingSlider;
      if (settings.halftoneSettings != null) {
        // LPI is now computed dynamically from DPI and Mesh
        // selectedDotShape is still loaded from settings
        selectedDotShape.value = settings.halftoneSettings!.dotShape;
        dotSizeMultiplier.value = settings.halftoneSettings!.dotSizeMultiplier;
      }
    }
  }

  // ─── Reset ───────────────────────────────────────────────────────────────

  void resetToDefaults() {
    selectedColors.value = 0;
    strokeWidth.value = 0.5;
    selectedDetail.value = ps.DetailLevel.medium;
    selectedFinish.value = ps.PrintFinish.solid;
    removeBackground.value = false;
    autoUpscale.value = false;
    paperWidthCm.value = 21.0;
    paperHeightCm.value = 29.7;
    printQuality.value = 300.0;
    isHalftone.value = false;
    // lpiValue is now computed dynamically (no longer stored)
    selectedDotShape.value = 'round';
    edgeEnhancement.value = false;
    colorCorrection.value = false;
    adaptiveThreshold.value = false;
    responsiveMode.value = false;
    selectedImageType.value = ps.ImageType.auto;
    globalThreshold.value = 127.0;
    smoothingFactor.value = 35.0;
    cornerThreshold.value = 45.0;
    smoothingSlider.value = 35;
    smoothingAdjustmentMade = false;
    cornerAdjustmentMade = false;
    thresholdAdjustmentMade = false;
    // New AI controls
    isAiAutoFix.value = true;
    selectedDpi.value = 1200;
    colorComplexity.value = 'Auto';
    targetWidthMm.value = 0.0;
    sourceDpi.value = 300;
    scaleMode.value = 'fit_to_page';
    customScalePercent.value = 100.0;
    update();
  }

  // ─── Processing ──────────────────────────────────────────────────────────

  Future<void> startProcessing() async {
    if (isProcessing.value) return;

    Get.log('=== startProcessing() called ===');
    Get.log('imagePath: ${imagePath.value}');
    Get.log('selectedColors: ${selectedColors.value}');
    Get.log('selectedDetail: ${selectedDetail.value}');
    Get.log('selectedFinish: ${selectedFinish.value}');
    Get.log('DPI: ${printQuality.value}');
    Get.log(
      'Halftone: ${isHalftone.value}, LPI: $lpiValue (dynamic), DotShape: ${selectedDotShape.value}',
    );

    if (imagePath.value.isEmpty) {
      Get.log('❌ No image selected, redirecting to upload');
      Get.snackbar(
        'No Image Selected',
        'Please upload an image first.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red.withAlpha((0.1 * 255).round()),
        colorText: Colors.red,
      );
      Future.delayed(const Duration(seconds: 1), () {
        Get.offNamed('/upload');
      });
      return;
    }

    isProcessing.value = true;
    progress.value = 0.0;
    progressMessage.value = 'Starting AI Analysis...';

    try {
      // 1. Mobile-side AI classification
      final aiService = MobileAIService();
      final aiAnalysis = await aiService.analyze(imagePath.value);
      progressMessage.value = 'AI Analysis complete.';
      // Build halftone settings ONLY if finish is halftone
      final bool effectivelyHalftone =
          selectedFinish.value == ps.PrintFinish.halftone;
      final halftone = effectivelyHalftone
          ? ps.HalftoneSettings(
              lpi: lpiValue, // Dynamic LPI from DPI and Mesh
              dotShape: selectedDotShape.value,
              dotSizeMultiplier: dotSizeMultiplier.value,
            )
          : null;

      // Determine edge enhancement from toggle
      final edge = edgeEnhancement.value
          ? ps.EdgeEnhancement.light
          : ps.EdgeEnhancement.none;

      // Build settings from REAL controller values
      final settings = ps.ProcessingSettings(
        colorCount: selectedColors.value,
        detailLevel: selectedDetail.value,
        printFinish: selectedFinish.value,
        strokeWidthMm: strokeWidth.value,
        dpi: printQuality.value,
        meshCount: meshCount,
        edgeEnhancement: edge,
        halftoneSettings: halftone,
        paperWidthCm: paperWidthCm.value,
        paperHeightCm: paperHeightCm.value,
        adaptiveThreshold: adaptiveThreshold.value,
        responsiveMode: responsiveMode.value,
        imageType: selectedImageType.value,
        globalThreshold: thresholdAdjustmentMade ? globalThreshold.value : 0.0,
        smoothingFactor: smoothingAdjustmentMade ? smoothingFactor.value : -1.0,
        cornerThreshold: cornerAdjustmentMade ? cornerThreshold.value : -1.0,
        smoothingSlider: -1, // Use independent smoothingFactor instead
        targetWidthMm: targetWidthMm.value,
        sourceDpi: sourceDpi.value,
        scaleMode: scaleMode.value,
        customScalePercent: customScalePercent.value,
        dotSizeMultipliers: dotSizeMultipliers.isEmpty ? null : dotSizeMultipliers.toList(),
        imageClassHint: aiAnalysis.imageClass,
        aiConfidence: aiAnalysis.confidence,
        preMaskPath: aiAnalysis.maskPath,
      );

      Get.log(
        '✅ Settings built: DPI=${settings.dpi}, mesh=${settings.meshCount}, edge=${settings.edgeEnhancement.name}',
      );

      // Validate settings before sending to Python
      final validationErrors = settings.validate();
      if (validationErrors.isNotEmpty) {
        Get.log('❌ Settings validation failed: $validationErrors');
        isProcessing.value = false;
        Get.snackbar(
          'Invalid Settings',
          validationErrors.join('\n'),
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.orange.withAlpha((0.15 * 255).round()),
          colorText: Colors.orange,
          duration: const Duration(seconds: 5),
        );
        return;
      }

      await _repository.saveSettings(settings);

      Get.log('🔄 Starting image processing...');
      Get.log(
          '📊 HALFTONE SETTINGS: isHalftone=${isHalftone.value}, LPI=$lpiValue, Mesh=$meshCount, DotShape=${selectedDotShape.value}');
      Get.log(
          '📊 DPI: ${printQuality.value}, Detail: ${selectedDetail.value}, Colors: ${selectedColors.value}');
      final outputDirVal = outputDir.value.isNotEmpty ? outputDir.value : null;

      final result = await _repository.processImage(
        imagePath: imagePath.value,
        settings: settings,
        outputDir: outputDirVal,
        onProgress: (p, msg) {
          progress.value = p;
          progressMessage.value = msg;
          Get.log('Progress: $p - $msg');
        },
      );

      Get.log('Processing result: ${result.success}');
      if (result.success) {
        Get.log(
          '✅ Success! Navigating to preview with: ${result.outputPath}',
        );
        // Play completion sound
        SoundManager().playDone();
        await Future.delayed(const Duration(milliseconds: 500));
        Get.offNamed(
          '/preview',
          arguments: {
            'outputDirectory': result.outputPath,
            'imagePath': imagePath.value,
            'originalPath': _originalTempPath,
            'settings': settings,
          },
        );
      } else {
        Get.log('❌ Processing failed: ${result.errorMessage}');
        isProcessing.value = false;
        Get.toNamed(
          '/error',
          arguments: {
            'processResult': result,
            'onRetry': () {
              Get.back();
              startProcessing();
            },
            'onGoBack': () {
              Get.offAllNamed('/dashboard');
            },
          },
        );
      }
    } catch (e, stackTrace) {
      Get.log('🔥 EXCEPTION in startProcessing: $e');
      Get.log('Stack trace: $stackTrace');

      Get.snackbar(
        'Processing Error',
        'An unexpected error occurred: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red.withAlpha((0.1 * 255).round()),
        colorText: Colors.red,
        duration: const Duration(seconds: 5),
      );
    } finally {
      // NOTE: Cleanup deferred to PreviewController.onClose() to allow Regenerate feature.
      /*
      if (imagePath.value.contains('vd_normalized_')) {
        ImageProcessor.cleanupTempFile(imagePath.value);
      }
      if (_originalTempPath.isNotEmpty &&
          _originalTempPath.contains('vd_normalized_')) {
        ImageProcessor.cleanupTempFile(_originalTempPath);
      }
      */
      if (isProcessing.value) isProcessing.value = false;
      Get.log('=== startProcessing() finished ===');
    }
  }

  Future<void> selectOutputDirectory() async {
    final String? selectedDirectory = await FilePicker.platform
        .getDirectoryPath(dialogTitle: 'اختر مجلد حفظ الأفلام');

    if (selectedDirectory != null) {
      outputDir.value = selectedDirectory;
    }
  }

  String getOutputDirectory() {
    if (outputDir.value.isNotEmpty) {
      return outputDir.value;
    }
    return '';
  }
}
