// lib/presentation/preview/preview_controller.dart

import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:open_file/open_file.dart';
import 'package:file_picker/file_picker.dart';
import '../../core/enums/app_enums.dart';
import '../../core/utils/image_processor.dart';
import '../../core/utils/sound_manager.dart';
import '../../domain/entities/processing_settings.dart' as ps;
import '../../domain/repositories/processing_repository.dart';

class PreviewController extends GetxController {
  final ProcessingRepository _repository;

  PreviewController({required ProcessingRepository repository})
      : _repository = repository;

  final RxString outputDirectory = ''.obs;
  final RxString imagePath = ''.obs;
  final RxString originalPath = ''.obs;
  final Rx<ps.ProcessingSettings?> initialSettings =
      Rx<ps.ProcessingSettings?>(null);

  // Hold both PNGs for UI and PDFs for export
  final RxList<String> previewPaths = <String>[].obs; // PNGs
  final RxList<String> pdfPaths = <String>[].obs; // PDFs
  final RxString combinedPdfPath = ''.obs; // all_films_combined.pdf

  final RxBool isLoading = true.obs;
  final RxInt selectedFilmIndex = 0.obs;
  final Rx<PrintType> selectedPrintType = PrintType.screenPrinting.obs;

  // Color Info from JSON
  final RxList<Map<String, dynamic>> colorInfo = <Map<String, dynamic>>[].obs;

  // Zoom functionality for InteractiveViewer
  final TransformationController transformationController =
      TransformationController();
  final RxDouble zoomLevel = 1.0.obs;

  // --- Adjustment State (Senior Perspective) ---
  final RxDouble globalThreshold = 200.0.obs;
  final RxDouble smoothingFactor = 0.25.obs; // Match setup controller default
  final RxDouble cornerThreshold = 45.0.obs; // Match setup controller default
  final RxInt noiseRemoval = 3.obs;
  final RxBool forceHalftone = false.obs;
  final RxBool adaptiveThreshold = false.obs;
  final RxString filmLabel = "".obs;
  late final TextEditingController filmLabelController;
  final RxDouble currentDpi = 300.0.obs; // Professional Standard = 300

  // Cache busting
  final RxInt lastUpdateTimestamp = 0.obs;

  // Per-layer overrides
  final RxList<bool> isLayerInverted = <bool>[].obs;
  final RxList<bool> isLayerSolid = <bool>[].obs;

  // Simulation Settings
  final Rx<Color> tshirtColor = Colors.white.obs;
  final RxBool showTshirtSimulation = false.obs;

  // Processing state for regeneration
  final RxBool isRegenerating = false.obs;
  final RxDouble progress = 0.0.obs;
  final RxString progressMessage = ''.obs;

  bool _needsAnotherPass = false; // Queue for overlapping adjustment requests
  double? _queuedDpi;

  @override
  void onInit() {
    super.onInit();
    final args = Get.arguments;
    if (args != null) {
      if (args is String) {
        outputDirectory.value = args;
      } else if (args is Map) {
        outputDirectory.value = args['outputDirectory'] as String? ?? '';
        imagePath.value = args['imagePath'] as String? ?? '';
        originalPath.value = args['originalPath'] as String? ?? '';

        final settings = args['settings'];
        if (settings is ps.ProcessingSettings) {
          initialSettings.value = settings;
          // Sync current adjustment state to initial values
          globalThreshold.value = settings.globalThreshold;
          smoothingFactor.value = settings.smoothingFactor;
          cornerThreshold.value = settings.cornerThreshold;
          noiseRemoval.value = settings.noiseRemoval;
          filmLabel.value = settings.filmLabel;
          currentDpi.value = settings.dpi;
          adaptiveThreshold.value = settings.adaptiveThreshold;
        }

        final printType = args['printType'];
        if (printType is PrintType) {
          selectedPrintType.value = printType;
        }
      }
      _loadFilmsAndInfo();
    } else {
      isLoading.value = false;
    }

    // Listen to zoom changes
    transformationController.addListener(() {
      zoomLevel.value = transformationController.value.getMaxScaleOnAxis();
    });

    // Debounce Tuning Sliders to prevent Python flood (Phase 9 & 11)
    debounce(globalThreshold, (_) => regenerateFilms(),
        time: const Duration(milliseconds: 300));
    debounce(smoothingFactor, (_) => regenerateFilms(),
        time: const Duration(milliseconds: 300));
    debounce(cornerThreshold, (_) => regenerateFilms(),
        time: const Duration(milliseconds: 400));
    debounce(noiseRemoval, (_) => regenerateFilms(),
        time: const Duration(milliseconds: 400));
    debounce(forceHalftone, (_) => regenerateFilms(),
        time: const Duration(milliseconds: 400));
    debounce(adaptiveThreshold, (_) => regenerateFilms(),
        time: const Duration(milliseconds: 400));

    filmLabelController = TextEditingController(text: filmLabel.value);
    filmLabelController.addListener(() {
      filmLabel.value = filmLabelController.text;
    });

    debounce(filmLabel, (_) => regenerateFilms(),
        time: const Duration(milliseconds: 600));
  }

  @override
  void onClose() {
    // Final Cleanup - Only if we are NOT in a situation where we might need them again soon
    // FATAL #7 FIX: Be conservative with cleanup to avoid "File not found" during rapid tuning
    if (imagePath.value.contains('vd_normalized_') && !isRegenerating.value) {
      Get.log(
          '🧹 PreviewController.onClose: Cleaning up normalized image ${imagePath.value}');
      ImageProcessor.cleanupTempFile(imagePath.value);
    }
    if (originalPath.value.contains('vd_normalized_') &&
        !isRegenerating.value) {
      Get.log(
          '🧹 PreviewController.onClose: Cleaning up original raw image ${originalPath.value}');
      ImageProcessor.cleanupTempFile(originalPath.value);
    }
    filmLabelController.dispose();
    transformationController.dispose();
    super.onClose();
  }

  Future<bool> regenerateFilms({double? forcedDpi}) async {
    if (isRegenerating.value) {
      Get.log('⏳ Already in progress, queuing another pass (Phase 9)...');
      _needsAnotherPass = true;
      _queuedDpi = forcedDpi;
      return false;
    }

    if (imagePath.isEmpty || initialSettings.value == null) {
      Get.snackbar('Error', 'Cannot regenerate: Context missing.');
      return false;
    }

    try {
      isRegenerating.value = true;
      progress.value = 0.0;
      progressMessage.value = 'Preparing regeneration...';

      // Phase 11 & 12 Refinement: Use 300 DPI as the new baseline for quality
      final targetDpi = forcedDpi ?? 300.0;

      // Build updated settings
      final updatedSettings = initialSettings.value!.copyWith(
        globalThreshold: globalThreshold.value,
        smoothingFactor: smoothingFactor.value,
        cornerThreshold: cornerThreshold.value,
        noiseRemoval: noiseRemoval.value,
        forceHalftone: forceHalftone.value,
        adaptiveThreshold: adaptiveThreshold.value,
        filmLabel: filmLabel.value,
        dpi: targetDpi,
      );

      Get.log(
          '🔄 Regenerating with tuning: Threshold=${globalThreshold.value}, Smooth=${smoothingFactor.value}, DPI=$targetDpi');

      final result = await _repository.processImage(
        imagePath: imagePath.value,
        settings: updatedSettings,
        outputDir: outputDirectory.value, // Re-use SAME directory or parent
        onProgress: (p, msg) {
          progress.value = p;
          progressMessage.value = msg;
        },
      );

      if (result.success) {
        outputDirectory.value = result.outputDirectory!;
        currentDpi.value = targetDpi; // Update current DPI tracking
        await _loadFilmsAndInfo();
        SoundManager().playDone();
        Get.snackbar('Success', 'Films updated with new adjustments.');
        return true;
      } else {
        Get.snackbar('Error', 'Regeneration failed: ${result.errorMessage}');
        return false;
      }
    } catch (e) {
      Get.log('❌ Exception in regenerateFilms: $e');
      Get.snackbar('Error', 'An unexpected error occurred: $e');
      return false;
    } finally {
      isRegenerating.value = false;

      // If a request was queued while we were busy, run it now (Phase 9)
      if (_needsAnotherPass) {
        Get.log('🔄 Running queued regeneration pass...');
        final nextDpi = _queuedDpi;
        _needsAnotherPass = false;
        _queuedDpi = null;
        // Schedule next pass after short delay to allow UI to breathe
        Future.delayed(const Duration(milliseconds: 100),
            () => regenerateFilms(forcedDpi: nextDpi));
      }
    }
  }

  Future<void> _loadFilmsAndInfo() async {
    try {
      isLoading.value = true;
      Get.log('🗂️ Loading output directory: ${outputDirectory.value}');

      final dir = Directory(outputDirectory.value);
      if (await dir.exists()) {
        final allFiles = dir.listSync().whereType<File>().toList();
        Get.log('🔎 Found ${allFiles.length} files in output directory.');
        for (var f in allFiles) {
          Get.log('   📄 ${f.path.split(Platform.pathSeparator).last}');
        }

        // Load PNG previews (sorted)
        previewPaths.value = allFiles
            .where((f) =>
                f.path.toLowerCase().endsWith('.png') &&
                !f.path.contains('debug'))
            .map((f) => f.path)
            .toList()
          ..sort();

        // Load Individual PDFs
        pdfPaths.value = allFiles
            .where((f) =>
                f.path.toLowerCase().endsWith('.pdf') &&
                !f.path.contains('combined'))
            .map((f) => f.path)
            .toList()
          ..sort();

        // Look for combined PDF
        final combined = allFiles
            .where(
                (f) => f.path.toLowerCase().endsWith('all_films_combined.pdf'))
            .toList();
        if (combined.isNotEmpty) {
          combinedPdfPath.value = combined.first.path;
        }

        // Load color_info.json
        final colorInfoFile =
            allFiles.where((f) => f.path.endsWith('color_info.json')).toList();
        if (colorInfoFile.isNotEmpty) {
          final jsonStr = await colorInfoFile.first.readAsString();
          final data = jsonDecode(jsonStr);
          if (data['colors'] != null) {
            colorInfo.value = List<Map<String, dynamic>>.from(data['colors']);
          }
        }

        if (previewPaths.isNotEmpty) {
          selectedFilmIndex.value = 0;

          // Always reinitialize layer toggles to default (false) for new processing
          isLayerInverted.value = List.filled(previewPaths.length, false);
          isLayerSolid.value = List.filled(previewPaths.length, false);
        }

        // Trigger cache bust (Phase 10) - Always update to force UI refresh
        lastUpdateTimestamp.value = DateTime.now().millisecondsSinceEpoch;
        Get.log('🔄 Cache bust triggered: ${lastUpdateTimestamp.value}');
      }
    } catch (e) {
      Get.log('❌ Error loading preview data: $e');
    } finally {
      isLoading.value = false;
    }
  }

  void selectFilm(int index) {
    if (index >= 0 && index < previewPaths.length) {
      selectedFilmIndex.value = index;
      fitToScreen(); // reset zoom when changing films
    }
  }

  void setPrintType(PrintType type) {
    selectedPrintType.value = type;
  }

  // ─── Zoom Methods ────────────────────────────────────────────────────────

  void zoomIn() {
    final scale = (zoomLevel.value * 1.5).clamp(0.5, 5.0);
    _applyZoom(scale);
  }

  void zoomOut() {
    final scale = (zoomLevel.value / 1.5).clamp(0.5, 5.0);
    _applyZoom(scale);
  }

  void fitToScreen() {
    transformationController.value = Matrix4.identity();
    zoomLevel.value = 1.0;
  }

  void _applyZoom(double scale) {
    // Zoom toward center
    final matrix = Matrix4.identity();
    matrix.scale(scale, scale, 1.0);
    transformationController.value = matrix;
    zoomLevel.value = scale;
  }

  // ─── Export & Print ──────────────────────────────────────────────────────

  Future<void> exportAll() async {
    if (combinedPdfPath.isEmpty) {
      Get.snackbar('Error', 'Combined PDF not found for export.');
      return;
    }

    // Hybrid DPI Logic: If current preview is low quality, generate high quality for export
    if (currentDpi.value < 300) {
      Get.log('🚀 Triggering high-DPI (300) pass for final export...');
      final success = await regenerateFilms(forcedDpi: 300.0);
      if (!success) return;
    }

    // Save As dialog
    final savePath = await FilePicker.platform.saveFile(
      dialogTitle: 'Save Output Films PDF',
      fileName: 'SilkScreen_Films.pdf',
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );

    if (savePath != null) {
      try {
        await File(combinedPdfPath.value).copy(savePath);
        Get.snackbar(
          'Export Complete',
          'Saved to $savePath',
          backgroundColor: Colors.green.withAlpha((0.1 * 255).round()),
          colorText: Colors.green,
        );
      } catch (e) {
        Get.snackbar('Error', 'Failed to save file: $e');
      }
    }
  }

  Future<void> sendToPrint() async {
    // Hybrid DPI Logic: If current preview is low quality, generate high quality for printing
    if (currentDpi.value < 300) {
      Get.log('🚀 Triggering high-DPI (300) pass for printing...');
      final success = await regenerateFilms(forcedDpi: 300.0);
      if (!success) return;
    }

    // Windows/Desktop check if a printer exists can be complex.
    // Standard approach: if user clicks print, open the PDF with default system handler.
    // Or save it directly if preferred.
    if (combinedPdfPath.isNotEmpty) {
      Get.snackbar('Printing', 'Opening PDF in default viewer for printing...');
      await openFile(combinedPdfPath.value);
    } else if (pdfPaths.isNotEmpty) {
      await openFile(pdfPaths[selectedFilmIndex.value]);
    } else {
      Get.snackbar('Error', 'No PDF available to print.');
    }
  }

  Future<void> openFile(String path) async {
    final result = await OpenFile.open(path);
    if (result.type != ResultType.done) {
      Get.snackbar('Error',
          'Could not open file: ${result.message}\nPlease ensure you have a PDF viewer installed.');

      // Fallback: copy to location
      final savePath = await FilePicker.platform.saveFile(
        dialogTitle: 'Save PDF instead',
        fileName: 'Film_${selectedFilmIndex.value + 1}.pdf',
      );
      if (savePath != null) {
        await File(path).copy(savePath);
      }
    }
  }

  // Navigate back to setup instead of dashboard
  void goBackToSetup() => Get.back();
}
