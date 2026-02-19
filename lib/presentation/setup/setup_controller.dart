// lib/presentation/setup/setup_controller.dart

import 'package:get/get.dart';
import '../../domain/entities/processing_settings.dart' as ps;
import '../../domain/repositories/processing_repository.dart';
import '../../core/errors/error_handler.dart';

class SetupController extends GetxController {
  final ProcessingRepository _repository;

  SetupController({required ProcessingRepository repository})
    : _repository = repository;

  // Image path passed from Upload screen
  final RxString imagePath = ''.obs;

  // Settings State
  final RxInt selectedColors = 4.obs;
  final RxDouble strokeWidth = 0.5.obs; // mm
  final Rx<ps.DetailLevel> selectedDetail = ps.DetailLevel.medium.obs;
  final Rx<ps.PrintFinish> selectedFinish = ps.PrintFinish.solid.obs;
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
      selectedColors.value = settings.colorCount;
      selectedDetail.value = settings.detailLevel;
      selectedFinish.value = settings.printFinish;
      strokeWidth.value = settings.strokeWidthMm;
      // ... load other settings
    }
  }

  Future<void> startProcessing() async {
    if (isProcessing.value) return;

    isProcessing.value = true;
    progress.value = 0.0;
    progressMessage.value = 'Starting...';

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
    } catch (e) {
      ErrorHandler.handleError(
        e,
        context: 'SetupController.startProcessing',
        showDialog: true,
        onRetry: startProcessing,
      );
    } finally {
      isProcessing.value = false;
    }
  }
}
