// batch_controller.dart — GetX Controller for Batch Processing
// Virtual Design Silk Screen Studio

import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:get/get.dart';
import '../../domain/usecases/batch_process_usecase.dart';
import '../../domain/entities/processing_settings.dart';

class BatchController extends GetxController {
  final BatchProcessUseCase batchUseCase;

  BatchController({required this.batchUseCase});

  // ── State ──────────────────────────────────────────────────────────────────
  final RxList<String> imagePaths   = <String>[].obs;
  final RxBool isProcessing         = false.obs;
  final RxBool isFinished           = false.obs;
  final Rx<BatchProgress?> batchProgress = Rx<BatchProgress?>(null);

  // ── Settings ───────────────────────────────────────────────────────────────
  final RxInt colorCount            = 2.obs;
  final Rx<PrintFinish> printFinish = PrintFinish.solid.obs;
  final RxInt dpi                   = 300.obs;

  // ── Image Picker ──────────────────────────────────────────────────────────

  Future<void> pickImages() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      allowMultiple: true,
    );
    if (result == null || result.files.isEmpty) return;

    final paths = result.files
        .where((f) => f.path != null)
        .map((f) => f.path!)
        .toList();

    imagePaths.addAll(paths);
    // إزالة التكرار
    imagePaths.value = imagePaths.toSet().toList();
  }

  void removeImage(int index) {
    if (index < imagePaths.length) imagePaths.removeAt(index);
  }

  // ── Processing ────────────────────────────────────────────────────────────

  Future<void> startProcessing() async {
    if (imagePaths.isEmpty) return;
    if (isProcessing.value) return;

    isProcessing.value = true;
    isFinished.value   = false;
    batchProgress.value = null;

    final settings = ProcessingSettings(
      colorCount:  colorCount.value,
      printFinish: printFinish.value,
      dpi:         dpi.value.toDouble(),
    );

    try {
      await for (final progress in batchUseCase.execute(imagePaths, settings)) {
        batchProgress.value = progress;

        // انتهت كل الصور
        if (progress.currentIndex >= imagePaths.length) {
          isProcessing.value = false;
          isFinished.value   = true;
          break;
        }
      }
    } catch (e) {
      isProcessing.value = false;
      Get.snackbar('خطأ', 'فشل Batch Processing: $e',
          duration: const Duration(seconds: 4));
    }
  }

  void cancel() {
    batchUseCase.cancel();
    isProcessing.value = false;
    isFinished.value   = true;
  }

  void reset() {
    imagePaths.clear();
    batchProgress.value = null;
    isProcessing.value  = false;
    isFinished.value    = false;
  }

  // ── Output ────────────────────────────────────────────────────────────────

  void openOutputFolder() {
    final completed = batchProgress.value?.completed ?? [];
    final firstSuccess = completed.where((r) => r.success).firstOrNull;
    if (firstSuccess?.outputDirectory == null) return;

    final folder = File(firstSuccess!.outputDirectory!).parent.path;
    if (Platform.isWindows) {
      Process.run('explorer', [folder]);
    } else if (Platform.isMacOS) {
      Process.run('open', [folder]);
    } else {
      Process.run('xdg-open', [folder]);
    }
  }
}
