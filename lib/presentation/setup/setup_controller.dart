// lib/presentation/setup/setup_controller.dart

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:get/get.dart';
import '../../domain/entities/processing_settings.dart' as ps;
import '../../domain/repositories/processing_repository.dart';

class SetupController extends GetxController {
  final ProcessingRepository _repository;

  SetupController({required ProcessingRepository repository})
    : _repository = repository;

  // Image path passed from Upload screen
  final RxString imagePath = ''.obs;

  // Settings State
  final RxInt selectedColors = 0.obs;
  final RxDouble strokeWidth = 0.5.obs; // mm
  final Rx<ps.DetailLevel> selectedDetail = ps.DetailLevel.medium.obs;
  final Rx<ps.PrintFinish> selectedFinish = ps.PrintFinish.solid.obs;
  final RxBool removeBackground = false.obs;
  final RxBool autoUpscale = false.obs;
  // Paper size (cm) inputs
  final RxDouble paperWidthCm = 21.0.obs;
  final RxDouble paperHeightCm = 29.7.obs;
  
  // Output directory selection
  final RxString outputDir = ''.obs;

  final RxBool isProcessing = false.obs;
  final RxDouble progress = 0.0.obs;
  final RxString progressMessage = ''.obs;

  @override
  void onInit() {
    super.onInit();
    if (Get.arguments != null && Get.arguments is String) {
      imagePath.value = Get.arguments as String;
    }
    // No crash — just uses empty path if not provided
    _loadLastSettings();
  }

  Future<void> _loadLastSettings() async {
    final settings = await _repository.loadLastSettings();
    if (settings != null) {
      selectedColors.value = settings.colorCount;
      selectedDetail.value = settings.detailLevel;
      selectedFinish.value = settings.printFinish;
      strokeWidth.value = settings.strokeWidthMm;
      // ... load other settings
    }
  }

  Future<void> startProcessing() async {
    if (isProcessing.value) return;

    Get.log('=== startProcessing() called ===');
    Get.log('imagePath: ${imagePath.value}');
    Get.log('selectedColors: ${selectedColors.value}');
    Get.log('selectedDetail: ${selectedDetail.value}');
    Get.log('selectedFinish: ${selectedFinish.value}');

    // Guard: if no image selected, show snackbar and redirect to upload
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
      // Build settings object
      final halftone = selectedFinish.value == ps.PrintFinish.halftone
          ? ps.HalftoneSettings(lpi: 65)
          : null;

      final settings = ps.ProcessingSettings(
        colorCount: selectedColors.value,
        detailLevel: selectedDetail.value,
        printFinish: selectedFinish.value,
        strokeWidthMm: strokeWidth.value,
        dpi: 300,
        meshCount: 160,
        edgeEnhancement: ps.EdgeEnhancement.light,
        halftoneSettings: halftone,
        paperWidthCm: paperWidthCm.value,
        paperHeightCm: paperHeightCm.value,
      );

      Get.log('✅ Settings built, saving...');
      // Save settings for next time
      await _repository.saveSettings(settings);

      Get.log('🔄 Starting image processing...');
      // Process with output directory if selected
      final outputDir = this.outputDir.value.isNotEmpty ? this.outputDir.value : null;
      
      final result = await _repository.processImage(
        imagePath: imagePath.value,
        settings: settings,
        outputDir: outputDir,
        onProgress: (p, msg) {
          progress.value = p;
          progressMessage.value = msg;
          Get.log('Progress: $p - $msg');
        },
      );

      Get.log('Processing result: ${result.success}');
      if (result.success) {
        Get.log('✅ Success! Navigating to preview with: ${result.outputDirectory}');
        Get.offNamed('/preview', arguments: result.outputDirectory);
      } else {
        Get.log('❌ Processing failed: ${result.errorMessage}');
        // Show error screen with retry option
        Get.toNamed(
          '/error',
          arguments: {
            'processResult': result,
            'onRetry': () {
              // Retry processing
              Get.back(); // Close error page
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
      isProcessing.value = false;
      Get.log('=== startProcessing() finished ===');
    }
  }

  Future<void> selectOutputDirectory() async {
    final String? selectedDirectory = await FilePicker.platform.getDirectoryPath(
      dialogTitle: 'اختر مجلد حفظ الأفلام',
    );
    
    if (selectedDirectory != null) {
      outputDir.value = selectedDirectory;
    }
  }

  String getOutputDirectory() {
    if (outputDir.value.isNotEmpty) {
      return outputDir.value;
    }
    // Default: empty string means Python will use its own default
    return '';
  }
}
