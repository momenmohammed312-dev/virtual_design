// lib/presentation/preview/preview_controller.dart

import 'dart:io';
import 'package:get/get.dart';
import 'package:open_file/open_file.dart';

class PreviewController extends GetxController {
  final RxString outputDirectory = ''.obs;
  final RxList<String> filmPaths = <String>[].obs;
  final RxBool isLoading = true.obs;

  @override
  void onInit() {
    super.onInit();
    final args = Get.arguments;
    if (args != null && args is String) {
      outputDirectory.value = args;
      _loadFilms();
    } else {
      Get.back();
      Get.snackbar('Error', 'No output directory provided');
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
            .where((f) => f.path.toLowerCase().endsWith('.png'))
            .map((f) => f.path)
            .toList();

        // Sort to ensure consistent order (e.g., specific colors first)
        files.sort();

        filmPaths.value = files;
      }
    } catch (e) {
      Get.log('Error loading films: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> openFile(String path) async {
    final result = await OpenFile.open(path);
    if (result.type != ResultType.done) {
      Get.snackbar('Error', 'Could not open file: ${result.message}');
    }
  }

  void goBack() => Get.offAllNamed('/dashboard');
}
