// lib/presentation/setup/setup_controller.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../domain/entities/processing_settings.dart';
import '../../domain/repositories/processing_repository.dart';
import '../../core/enums/app_enums.dart';

class SetupController extends GetxController {
  final ProcessingRepository _repository;

  SetupController({required ProcessingRepository repository})
    : _repository = repository;

  // Image path passed from Upload screen
  final RxString imagePath = ''.obs;

  // Settings State
  final Rx<PrintType> selectedPrintType = PrintType.screenPrinting.obs;
  final RxInt selectedColors = 4.obs;
  final RxDouble strokeWidth = 0.5.obs; // mm
  final Rx<DetailLevel> selectedDetail = DetailLevel.medium.obs;
  final Rx<PrintFinish> selectedFinish = PrintFinish.solid.obs;
  final RxBool removeBackground = true.obs;
  final RxBool autoUpscale = true.obs;

  final RxBool isProcessing = false.obs;
  final RxDouble progress = 0.0.obs;
  final RxString progressMessage = ''.obs;

  @override
  void onInit() {
    super.onInit();
    if (Get.arguments != null && Get.arguments is String) {
      imagePath.value = Get.arguments as String;
    } else {
      // Fallback or error - should not happen in normal flow
      Get.back();
    }
    _loadLastSettings();
  }

  Future<void> _loadLastSettings() async {
    final settings = await _repository.loadLastSettings();
    if (settings != null) {
      selectedPrintType.value = settings.printType;
      selectedColors.value = settings.colorCount;
      selectedDetail.value = settings.detailLevel;
      selectedFinish.value = settings.printFinish;
      removeBackground.value = settings.removeBackground;
      // ... load other settings
    }
  }

  Future<void> startProcessing() async {
    if (isProcessing.value) return;

    isProcessing.value = true;
    progress.value = 0.0;
    progressMessage.value = 'Starting...';

    // Build settings object
    final settings = ProcessingSettings(
      printType: selectedPrintType.value,
      colorCount: selectedColors.value,
      detailLevel: selectedDetail.value,
      printFinish: selectedFinish.value,
      strokeWidthMm: strokeWidth.value,
      paperSize: 'A4', // Default or make selectable
      copies: 1,
      dpi: 300,
      removeBackground: removeBackground.value,
      autoUpscale: autoUpscale.value,
      edgeEnhancement: true,
      colorCorrection: true,
    );

    try {
      // Save settings for next time
      await _repository.saveSettings(settings);

      // Process
      final result = await _repository.processImage(
        imagePath: imagePath.value,
        settings: settings,
        onProgress: (p, msg) {
          progress.value = p;
          progressMessage.value = msg;
        },
      );

      if (result.success) {
        Get.offNamed('/preview', arguments: result.outputDirectory);
      } else {
        Get.defaultDialog(
          title: 'Error',
          middleText: result.errorMessage ?? 'Unknown error occurred',
          textConfirm: 'OK',
          onConfirm: () => Get.back(),
        );
      }
    } catch (e) {
      Get.defaultDialog(
        title: 'Error',
        middleText: e.toString(),
        textConfirm: 'OK',
        onConfirm: () => Get.back(),
      );
    } finally {
      isProcessing.value = false;
    }
  }
}
