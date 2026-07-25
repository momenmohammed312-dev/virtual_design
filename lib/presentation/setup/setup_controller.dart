// lib/presentation/setup/setup_controller.dart
// Fixes 2, 4, 7: Real UI values, dot_shape, temp file cleanup
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:get/get.dart';
import 'package:virtual_design/domain/entities/processing_settings.dart' as ps;
import 'package:virtual_design/domain/repositories/processing_repository.dart';
import 'package:virtual_design/core/utils/sound_manager.dart';
import 'package:virtual_design/core/mobile_ai/mobile_ai_service.dart';
import 'package:virtual_design/core/server/server_connector.dart';
import 'package:virtual_design/core/python_bridge/process_result.dart';

class SetupController extends GetxController {
  final ProcessingRepository _repository;

  // Manual LPI override (0 = auto)
  final RxInt manualLpi = 0.obs;
  final RxInt userLpi = 79.obs;
  final RxInt userMeshCount = 355.obs;

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

  // Track if user manually moved threshold slider
  bool thresholdAdjustmentMade = false;

  // AI Auto-Fix controls
  final RxBool isAiAutoFix = true.obs; // Auto-adjust sliders by AI
  final RxInt selectedDpi = 300.obs; // Default DPI baseline
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
    return userLpi.value;
  }

  final RxString selectedDotShape = 'round'.obs;
  final RxDouble dotSizeMultiplier = 0.7.obs;
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
    return userMeshCount.value;
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
      thresholdAdjustmentMade = false;
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
      // Normalize legacy/invalid values so "auto" mode is stable across restarts.
      // (Avoid persisting 1200 as a sticky default when the app is moving to 300 baseline.)
      printQuality.value = (settings.dpi <= 0) ? 300.0 : settings.dpi;
      if (printQuality.value > 300.0 && !isHalftone.value) {
        printQuality.value = 300.0;
      }
      adaptiveThreshold.value = settings.adaptiveThreshold;
      responsiveMode.value = settings.responsiveMode;
      selectedImageType.value = settings.imageType;
      smoothingSlider.value = settings.smoothingSlider;
      if (settings.halftoneSettings != null) {
        // LPI is now computed dynamically from DPI and Mesh
        // selectedDotShape is still loaded from settings
        selectedDotShape.value = settings.halftoneSettings!.dotShape;
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
    dotSizeMultiplier.value = 0.7; // Sensible default for artwork
    dotSizeMultipliers.clear();
    edgeEnhancement.value = false;
    colorCorrection.value = false;
    adaptiveThreshold.value = false;
    responsiveMode.value = false;
    selectedImageType.value = ps.ImageType.auto;
    globalThreshold.value = 127.0;
    smoothingFactor.value = 35.0;
    cornerThreshold.value = 45.0;
    smoothingSlider.value = 35;
    thresholdAdjustmentMade = false;
    // New AI controls
    isAiAutoFix.value = true;
    selectedDpi.value = 300;
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
    progressMessage.value = 'Analyzing image on-device…';

    try {
      // ── 1. On-device AI (MobileNetV3 + DeepLabV3) ───────────────────────
      final aiService = MobileAIService();
      final aiAnalysis = await aiService.analyze(imagePath.value);
      Get.log(
        '🤖 Mobile AI: class=${aiAnalysis.imageClass} '
        'conf=${aiAnalysis.confidence.toStringAsFixed(2)} '
        'source=${aiAnalysis.source}',
      );

      progressMessage.value = 'AI analysis complete.';
      progress.value = 0.12;

      // ── 2. Apply AI suggestions in Auto-color mode ───────────────────────
      if (selectedColors.value == 0 &&
          aiAnalysis.suggestions?.suggestedColors != null) {
        Get.log(
          '🎨 Auto-colors: AI suggests ${aiAnalysis.suggestions!.suggestedColors} colors',
        );
        selectedColors.value = aiAnalysis.suggestions!.suggestedColors!;
      }

      // ── 3. Resolve class hint (user choice is final) ─────────────────────
      String resolvedClass = aiAnalysis.imageClass;
      if (resolvedClass == 'logo') resolvedClass = 'text_logo';
      if (selectedFinish.value == ps.PrintFinish.solid) {
        resolvedClass = 'text_logo';
      }

      final bool effectivelyHalftone =
          selectedFinish.value == ps.PrintFinish.halftone;

      double resolvedConfidence = (selectedFinish.value == ps.PrintFinish.solid)
          ? aiAnalysis.confidence
          : aiAnalysis.confidence;

      // Halftone: keep mobile AI class hint, cap confidence below .90 so Python AI runs.
      if (effectivelyHalftone) {
        resolvedConfidence = min(aiAnalysis.confidence, 0.89);
      }

      // Manual LPI override
      final effectiveLpi = userLpi.value;

      // ── 4. Build ProcessingSettings ──────────────────────────────────────
      final halftone = effectivelyHalftone
          ? ps.HalftoneSettings(
              lpi: effectiveLpi,
              dotShape: selectedDotShape.value,
              dotSizeMultiplier: dotSizeMultiplier.value,
            )
          : null;

      final edge = edgeEnhancement.value
          ? ps.EdgeEnhancement.light
          : ps.EdgeEnhancement.none;

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
        smoothingFactor: -1.0,
        cornerThreshold: -1.0,
        smoothingSlider: -1,
        targetWidthMm: targetWidthMm.value,
        sourceDpi: sourceDpi.value,
        scaleMode: scaleMode.value,
        customScalePercent: customScalePercent.value,
        dotSizeMultipliers:
            dotSizeMultipliers.isEmpty ? null : dotSizeMultipliers.toList(),
        imageClassHint: resolvedClass,
        aiConfidence: resolvedConfidence,
        preMaskPath: aiAnalysis.maskPath,
      );

      Get.log(
        '✅ Settings built: DPI=${settings.dpi}, mesh=${settings.meshCount}, '
        'edge=${settings.edgeEnhancement.name}',
      );

      // ── 4. Validate ──────────────────────────────────────────────────────
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

      // ── 5. Build settings map for ServerConnector API fields ─────────────
      final settingsMap = <String, dynamic>{
        'colors': settings.colorCount,
        'dpi': settings.dpi.round(),
        'halftone': effectivelyHalftone,
        'lpi': effectiveLpi,
        'dot_shape': selectedDotShape.value,
        'dot_size': dotSizeMultiplier.value.clamp(0.3, 1.5),
        'mesh_count': meshCount,
        'paper_width': paperWidthCm.value,
        'paper_height': paperHeightCm.value,
        'detail_level': selectedDetail.value.name,
        'target_width_mm': targetWidthMm.value,
        'source_dpi': sourceDpi.value,
        'scale_mode': scaleMode.value,
        'custom_scale_percent': customScalePercent.value,
        // Smoothing & corner (sentinel -1.0 = adaptive from AI/decision engine)
        'smoothing_factor': -1.0,
        'corner_threshold': -1.0,
      };

      // ── 6. Route: server (Qwen) or local pipeline ────────────────────────
      progressMessage.value = 'Processing…';
      progress.value = 0.15;

      final connector = ServerConnector();
      Get.log(
        '🔌 Connection mode: ${connector.mode.value.name} '
        '(${connector.serverUrl.value})',
      );

      final result = await connector.processImage(
        imagePath: imagePath.value,
        settings: settingsMap,
        maskPath: aiAnalysis.maskPath,
        imageClassHint: resolvedClass,
        aiConfidence: resolvedConfidence,
        onProgress: (p, msg) {
          // Blend connector progress [0..1] into overall [0.15..1.0]
          progress.value = 0.15 + p * 0.85;
          progressMessage.value = msg;
          Get.log(
              'Progress: ${(progress.value * 100).toStringAsFixed(0)}% — $msg');
        },
      );

      Get.log('Processing result: ${result.success}');

      if (result.success) {
        Get.log('✅ Success → preview: ${result.outputDirectory}');
        SoundManager().playDone();
        await Future.delayed(const Duration(milliseconds: 500));
        Get.offNamed(
          '/preview',
          arguments: {
            'outputDirectory': result.outputDirectory,
            'imagePath': imagePath.value,
            'originalPath': _originalTempPath,
            'settings': settings,
          },
        );
      } else {
        Get.log('❌ Processing failed: ${result.error}');
        isProcessing.value = false;

        // Surface a friendly error with connection context
        final isServerMode = connector.isServerMode;
        final errorTitle = isServerMode ? 'Server Error' : 'Processing Error';
        final errorBody = result.error ?? 'An unknown error occurred.';

        Get.toNamed(
          '/error',
          arguments: {
            'processResult': _makeErrorResult(errorBody),
            'onRetry': () {
              Get.back();
              startProcessing();
            },
            'onGoBack': () {
              Get.offAllNamed('/dashboard');
            },
          },
        );
        Get.snackbar(
          errorTitle,
          errorBody,
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.red.withAlpha((0.12 * 255).round()),
          colorText: Colors.red,
          duration: const Duration(seconds: 6),
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
      if (isProcessing.value) isProcessing.value = false;
      Get.log('=== startProcessing() finished ===');
    }
  }

  /// Returns a ProcessResult so the error page can classify it properly.
  ProcessResult _makeErrorResult(String message) {
    return ProcessResult.failure(errorMessage: message);
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
