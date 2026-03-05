import 'package:get/get.dart';
import '../../core/repositories/folder_repository.dart';

class FilesController extends GetxController {
  final FolderRepository _folderRepository = FolderRepository();
  
  final RxList<Map<String, dynamic>> userFolders = <Map<String, dynamic>>[].obs;
  final RxBool isLoading = false.obs;
  final RxString errorMessage = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadUserFolders();
  }

  /// Load folders for the current user only
  Future<void> loadUserFolders() async {
    try {
      isLoading.value = true;
      errorMessage.value = '';
      
      final userId = await _folderRepository.getCurrentUserId();
      final folders = await _folderRepository.getFoldersByUser(userId);
      
      userFolders.value = folders;
    } catch (e) {
      errorMessage.value = 'Failed to load folders: $e';
      userFolders.value = [];
    } finally {
      isLoading.value = false;
    }
  }

  /// Refresh folders (pull-to-refresh)
  Future<void> refreshFolders() async {
    await loadUserFolders();
  }
}
