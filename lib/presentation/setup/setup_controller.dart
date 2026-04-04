// lib/presentation/setup/setup_controller.dart
// Fixes 2, 4, 7: Real UI values, dot_shape, temp file cleanup

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:get/get.dart';
import '../../domain/entities/processing_settings.dart' as ps;
import '../../domain/repositories/processing_repository.dart';
import '../../core/utils/sound_manager.dart';

class SetupController extends GetxController {
  final ProcessingRepository _repository;

  SetupController({required ProcessingRepository repository})
      : _repository = repository;

  // ─── Image paths ─────────────────────────────────────────────────────────
  final RxString imagePath = ''.obs;
  String _originalTempPath = ''; // for cleanup after processing

  // ─── Settings State ──────────────────────────────────────────────────────
  final RxInt selectedColors = 1.obs;
  final RxDouble strokeWidth = 0.5.obs; // mm
  final Rx<ps.DetailLevel> selectedDetail = ps.DetailLevel.medium.obs;
  final Rx<ps.PrintFinish> selectedFinish = ps.PrintFinish.solid.obs;
  final RxBool removeBackground = false.obs;
  final RxBool autoUpscale = false.obs;

  final RxDouble smoothingFactor = 0.25.obs;
  final RxDouble cornerThreshold = 45.0.obs;
  final RxInt smoothingSlider = 35.obs;

  // Paper size
  final RxDouble paperWidthCm = 21.0.obs;
  final RxDouble paperHeightCm = 29.7.obs;

  // Print quality (DPI)
  final RxDouble printQuality = 300.0.obs;

  // Halftone settings
  final RxBool isHalftone = false.obs;
  final RxInt lpiValue = 55.obs;
  final RxString selectedDotShape = 'round'.obs;

  // Edge enhancement & color correction
  final RxBool edgeEnhancement = false.obs;
  final RxBool colorCorrection = false.obs;
  final RxBool adaptiveThreshold = false.obs;
  final Rx<ps.ImageType> selectedImageType = ps.ImageType.auto.obs;

  // Output directory selection
  final RxString outputDir = ''.obs;

  // Processing state
  final RxBool isProcessing = false.obs;
  final RxDouble progress = 0.0.obs;
  final RxString progressMessage = ''.obs;

  // ─── Computed ────────────────────────────────────────────────────────────

  /// Auto-calculate mesh count based on LPI
  int get meshCount {
    final lpi = lpiValue.value;
    if (lpi < 30) return 110;
    if (lpi < 50) return 160;
    if (lpi < 65) return 200;
    if (lpi < 80) return 230;
    if (lpi < 90) return 280;
    return 355;
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
          smoothingFactor.value = 0.25;
          cornerThreshold.value = 45.0;
          break;
        case ps.ImageType.mixed:
          smoothingFactor.value = 0.25;
          cornerThreshold.value = 45.0;
          break;
        case ps.ImageType.complex:
          smoothingFactor.value = 0.30;
          cornerThreshold.value = 50.0;
          break;
        case ps.ImageType.auto:
        default:
          // In Auto mode, keep user-set values (do nothing)
          break;
      }
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
      selectedImageType.value = settings.imageType;
      smoothingSlider.value = settings.smoothingSlider;
      if (settings.halftoneSettings != null) {
        lpiValue.value = settings.halftoneSettings!.lpi;
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
    lpiValue.value = 55;
    selectedDotShape.value = 'round';
    edgeEnhancement.value = false;
    colorCorrection.value = false;
    adaptiveThreshold.value = false;
    selectedImageType.value = ps.ImageType.auto;
    smoothingFactor.value = 0.25;
    cornerThreshold.value = 45.0;
    smoothingSlider.value = 35;
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
      'Halftone: ${isHalftone.value}, LPI: ${lpiValue.value}, DotShape: ${selectedDotShape.value}',
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
    progressMessage.value = 'Starting...';

    try {
      // Build halftone settings ONLY if finish is halftone
      final bool effectivelyHalftone =
          selectedFinish.value == ps.PrintFinish.halftone;
      final halftone = effectivelyHalftone
          ? ps.HalftoneSettings(
              lpi: lpiValue.value,
              dotShape: selectedDotShape.value,
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
        imageType: selectedImageType.value,
        smoothingFactor: smoothingFactor.value,
        cornerThreshold: cornerThreshold.value,
        smoothingSlider: smoothingSlider.value,
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
          '✅ Success! Navigating to preview with: ${result.outputDirectory}',
        );
        // Play completion sound
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
