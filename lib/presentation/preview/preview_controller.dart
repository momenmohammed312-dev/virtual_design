// lib/presentation/preview/preview_controller.dart

import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:open_file/open_file.dart';
import 'package:file_picker/file_picker.dart';
import '../../core/enums/app_enums.dart';

class PreviewController extends GetxController {
  final RxString outputDirectory = ''.obs;
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
  final TransformationController transformationController = TransformationController();
  final RxDouble zoomLevel = 1.0.obs;

  @override
  void onInit() {
    super.onInit();
    final args = Get.arguments;
    if (args != null) {
      if (args is String) {
        outputDirectory.value = args;
      } else if (args is Map) {
        outputDirectory.value = args['outputDirectory'] as String? ?? '';
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
  }

  Future<void> _loadFilmsAndInfo() async {
    try {
      isLoading.value = true;
      Get.log('🗂️ Loading output directory: ${outputDirectory.value}');

      final dir = Directory(outputDirectory.value);
      if (await dir.exists()) {
        final allFiles = dir.listSync().whereType<File>().toList();
        
        // Load PNG previews (sorted)
        previewPaths.value = allFiles
            .where((f) => f.path.toLowerCase().endsWith('.png') && !f.path.contains('debug'))
            .map((f) => f.path)
            .toList()..sort();
            
        // Load Individual PDFs
        pdfPaths.value = allFiles
            .where((f) => f.path.toLowerCase().endsWith('.pdf') && !f.path.contains('combined'))
            .map((f) => f.path)
            .toList()..sort();
            
        // Look for combined PDF
        final combined = allFiles.where((f) => f.path.toLowerCase().endsWith('all_films_combined.pdf')).toList();
        if (combined.isNotEmpty) {
          combinedPdfPath.value = combined.first.path;
        }

        // Load color_info.json
        final colorInfoFile = allFiles.where((f) => f.path.endsWith('color_info.json')).toList();
        if (colorInfoFile.isNotEmpty) {
          final jsonStr = await colorInfoFile.first.readAsString();
          final data = jsonDecode(jsonStr);
          if (data['colors'] != null) {
            colorInfo.value = List<Map<String, dynamic>>.from(data['colors']);
          }
        }

        if (previewPaths.isNotEmpty) {
          selectedFilmIndex.value = 0;
        }
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
      Get.snackbar('Error', 'Could not open file: ${result.message}\nPlease ensure you have a PDF viewer installed.');
      
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
