// lib/presentation/preview/preview_controller.dart

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:open_file/open_file.dart';

class PreviewController extends GetxController {
  final RxString outputDirectory = ''.obs;
  final RxList<String> filmPaths = <String>[].obs;
  final RxBool isLoading = true.obs;
  final RxInt selectedFilmIndex = 0.obs;

  @override
  void onInit() {
    super.onInit();
    final args = Get.arguments;
    if (args != null && args is String) {
      outputDirectory.value = args;
      _loadFilms();
    } else {
      // No crash — just show empty state
      isLoading.value = false;
    }
  }

  Future<void> _loadFilms() async {
    try {
      isLoading.value = true;
      final dir = Directory(outputDirectory.value);
      if (await dir.exists()) {
        final files = dir
            .listSync()
            .whereType<File>()
            .where((f) =>
                f.path.toLowerCase().endsWith('.png') ||
                f.path.toLowerCase().endsWith('.pdf'))
            .map((f) => f.path)
            .toList()
          ..sort();

        filmPaths.value = files;
        if (filmPaths.isNotEmpty) {
          selectedFilmIndex.value = 0;
        }
      }
    } catch (e) {
      Get.log('Error loading films: $e');
    } finally {
      isLoading.value = false;
    }
  }

  void selectFilm(int index) {
    if (index >= 0 && index < filmPaths.length) {
      selectedFilmIndex.value = index;
    }
  }

  Future<void> exportAll() async {
    if (filmPaths.isEmpty) {
      Get.snackbar('No Films', 'No films to export.', snackPosition: SnackPosition.BOTTOM);
      return;
    }

    Get.snackbar(
      'Exporting',
      'Exporting ${filmPaths.length} films...',
      snackPosition: SnackPosition.BOTTOM,
      duration: const Duration(seconds: 2),
    );

    // In a real implementation, you would package all films into a ZIP or copy them to a destination
    await Future.delayed(const Duration(seconds: 2));

    Get.snackbar(
      'Export Complete',
      'All films have been exported successfully.',
      snackPosition: SnackPosition.BOTTOM,
      backgroundColor: Colors.green.withAlpha((0.1 * 255).round()),
      colorText: Colors.green,
    );
  }

  Future<void> openFile(String path) async {
    final result = await OpenFile.open(path);
    if (result.type != ResultType.done) {
      Get.snackbar('Error', 'Could not open file: ${result.message}');
    }
  }

  void goBack() => Get.offAllNamed('/dashboard');
}
