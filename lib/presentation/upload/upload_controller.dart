// lib/presentation/upload/upload_controller.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import '../../core/permissions/permission_service.dart';


class UploadController extends GetxController {
  final PermissionService permissionService = Get.find<PermissionService>();
  final RxBool isDragging = false.obs;

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
      type: FileType.custom,
      allowedExtensions: ['png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'webp'],
      allowMultiple: false,
    );

    if (result != null && result.files.single.path != null) {
      final file = result.files.single;
      final ext = file.extension?.toLowerCase() ?? '';
      
      final supported = ['png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'webp'];
      if (!supported.contains(ext)) {
        Get.snackbar(
          'صيغة غير مدعومة',
          'يُرجى اختيار ملف PNG أو JPG أو TIFF أو BMP أو WEBP',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: Colors.red,
          colorText: Colors.white,
        );
        return;
      }
      
      _proceedToSetup(file.path!);
    }
  }

  void onFileDropped(dynamic file) {
    // Handling depends on drop package, usually returns path or bytes
    // Assuming we get a path string or file object with path
    // _proceedToSetup(file.path);
  }

  void _proceedToSetup(String imagePath) {
    Get.toNamed('/setup', arguments: imagePath);
  }
}
