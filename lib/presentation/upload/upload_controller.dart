// lib/presentation/upload/upload_controller.dart

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
      type: FileType.image,
    );

    if (result != null && result.files.single.path != null) {
      _proceedToSetup(result.files.single.path!);
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
