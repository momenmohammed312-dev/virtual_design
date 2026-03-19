// lib/presentation/upload/upload_controller.dart

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import '../../core/permissions/permission_service.dart';
import '../../core/utils/image_processor.dart';

class UploadController extends GetxController {
  final PermissionService permissionService = Get.find<PermissionService>();
  final RxBool isDragging = false.obs;
  final RxString urlInput = ''.obs;

  final RxBool isUrlDownloading = false.obs;
  final RxDouble urlDownloadProgress = 0.0.obs;
  final RxString urlDownloadStatus = ''.obs;

  Future<void> pickImage() async {
    // Check permissions first
    final hasPermission = await permissionService.ensureImageAccess();
    if (!hasPermission) {
      Get.snackbar(
        'Permission Required',
        'Storage permission is needed to select images',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Get.theme.colorScheme.error,
        colorText: Get.theme.colorScheme.onError,
      );
      return;
    }

    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);

    if (image != null) {
      _proceedToSetup(image.path);
    }
  }

  Future<void> pickFile() async {
    // Check permissions first
    final hasPermission = await permissionService.ensureImageAccess();
    if (!hasPermission) {
      Get.snackbar(
        'Permission Required',
        'Storage permission is needed to select images',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Get.theme.colorScheme.error,
        colorText: Get.theme.colorScheme.onError,
      );
      return;
    }

    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.any,
      allowMultiple: false,
    );

    if (result != null && result.files.single.path != null) {
      final file = result.files.single;
      _proceedToSetup(file.path!);
    }
  }

  void onFileDropped(dynamic file) {
    // Handling depends on drop package, usually returns path or bytes
    // Assuming we get a path string or file object with path
    // _proceedToSetup(file.path);
  }

  Future<void> importFromUrl(String url) async {
    final trimmed = url.trim();
    if (trimmed.isEmpty) {
      Get.snackbar(
        'Invalid URL',
        'Please paste a valid image URL.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return;
    }

    final uri = Uri.tryParse(trimmed);
    if (uri == null || !(uri.isScheme('http') || uri.isScheme('https'))) {
      Get.snackbar(
        'Invalid URL',
        'Only http/https URLs are supported.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return;
    }

    const maxBytes = 10 * 1024 * 1024;

    isUrlDownloading.value = true;
    urlDownloadProgress.value = 0.0;
    urlDownloadStatus.value = 'Starting download...';

    try {
      final req = http.Request('GET', uri);
      final res = await req.send().timeout(const Duration(seconds: 25));

      if (res.statusCode < 200 || res.statusCode >= 300) {
        throw Exception('Request failed (HTTP ${res.statusCode})');
      }

      final contentLength = res.contentLength;
      if (contentLength != null && contentLength > maxBytes) {
        throw Exception('File is larger than 10MB');
      }

      final tempDir = await getTemporaryDirectory();

      String ext = '';
      final contentType =
          res.headers['content-type'] ?? res.headers['Content-Type'];
      if (contentType != null) {
        final lower = contentType.toLowerCase();
        if (lower.contains('image/png')) {
          ext = '.png';
        } else if (lower.contains('image/jpeg') ||
            lower.contains('image/jpg')) {
          ext = '.jpg';
        } else if (lower.contains('image/webp')) {
          ext = '.webp';
        } else if (lower.contains('image/bmp')) {
          ext = '.bmp';
        } else if (lower.contains('image/tiff')) {
          ext = '.tiff';
        }
      }

      if (ext.isEmpty) {
        final seg = uri.pathSegments.isNotEmpty ? uri.pathSegments.last : '';
        final inferred = p.extension(seg);
        if (inferred.isNotEmpty && inferred.length <= 6) {
          ext = inferred;
        } else {
          ext = '.img';
        }
      }

      final filename = 'vd_url_${DateTime.now().millisecondsSinceEpoch}$ext';
      final downloadedPath = p.join(tempDir.path, filename);
      urlDownloadStatus.value = 'Downloading...';
      await _downloadStreamToFile(
        stream: res.stream,
        filePath: downloadedPath,
        maxBytes: maxBytes,
        contentLength: contentLength,
      );

      urlDownloadProgress.value = 1.0;
      urlDownloadStatus.value = 'Download complete. Processing...';

      await _proceedToSetup(downloadedPath);
    } catch (e) {
      Get.snackbar(
        'Download Failed',
        'Could not download image: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red,
        colorText: Colors.white,
        duration: const Duration(seconds: 6),
      );
    } finally {
      isUrlDownloading.value = false;
    }
  }

  Future<void> _downloadStreamToFile({
    required Stream<List<int>> stream,
    required String filePath,
    required int maxBytes,
    required int? contentLength,
  }) async {
    final outFile = File(filePath);
    final sink = outFile.openWrite();
    var total = 0;
    try {
      await for (final chunk in stream) {
        total += chunk.length;
        if (total > maxBytes) {
          throw Exception('File is larger than 10MB');
        }
        sink.add(chunk);

        if (contentLength != null && contentLength > 0) {
          urlDownloadProgress.value = (total / contentLength).clamp(0.0, 1.0);
          final percent = (urlDownloadProgress.value * 100).toStringAsFixed(0);
          urlDownloadStatus.value = 'Downloading... $percent%';
        } else {
          urlDownloadProgress.value = 0.0;
          urlDownloadStatus.value = 'Downloading...';
        }
      }
    } finally {
      await sink.flush();
      await sink.close();
    }
  }

  Future<void> _proceedToSetup(String rawImagePath) async {
    try {
      // Show loading indicator
      Get.dialog(
        const Center(child: CircularProgressIndicator()),
        barrierDismissible: false,
      );

      // Normalize the image to JPG format
      final normalizedPath = await ImageProcessor.normalizeImage(rawImagePath);

      // Close loading indicator
      if (Get.isDialogOpen!) Get.back();

      // Navigate to setup with normalized image
      Get.toNamed(
        '/setup',
        arguments: {'imagePath': normalizedPath, 'originalPath': rawImagePath},
      );
    } catch (e) {
      // Close loading indicator if open
      if (Get.isDialogOpen!) Get.back();

      Get.snackbar(
        'Image Processing Error',
        'Failed to process image: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    }
  }
}
