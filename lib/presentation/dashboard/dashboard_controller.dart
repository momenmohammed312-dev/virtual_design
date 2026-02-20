// lib/presentation/dashboard/dashboard_controller.dart

import 'dart:io';
import 'package:get/get.dart';
import 'package:path_provider/path_provider.dart';
import '../../domain/repositories/project_repository.dart';
import '../../domain/entities/print_project.dart';

class DashboardController extends GetxController {
  final ProjectRepository _projectRepository;

  DashboardController({required ProjectRepository projectRepository})
    : _projectRepository = projectRepository;

  // ── State ──────────────────────────────────────────────
  final RxInt totalProjects = 0.obs;
  final RxInt totalFilms = 0.obs;
  final RxString storageUsed = '0 MB'.obs;
  final RxList<PrintProject> recentProjects = <PrintProject>[].obs;
  final RxBool isLoading = true.obs;
  final RxString searchQuery = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadStats();
  }

  // ═══════════════════════════════════════════════════════
  // Load Dashboard Stats
  // ═══════════════════════════════════════════════════════

  Future<void> loadStats() async {
    try {
      isLoading.value = true;

      // Load all projects
      final projects = await _projectRepository.getAllProjects();
      totalProjects.value = projects.length;

      // Count completed projects as "films"
      int films = projects.where((p) => p.status.toString() == 'ProjectStatus.completed').length;
      totalFilms.value = films;

      // Get recent projects (last 5)
      recentProjects.value = projects.take(5).toList();

      // Calculate storage (approximation)
      await _calculateStorage();
    } catch (e) {
      Get.snackbar(
        'Error',
        'Failed to load stats: $e',
        snackPosition: SnackPosition.BOTTOM,
      );
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> _calculateStorage() async {
    try {
      final appDir = await getApplicationDocumentsDirectory();
      final outputDir = Directory('${appDir.path}/silk_screen_output');

      if (!outputDir.existsSync()) {
        storageUsed.value = '0 MB';
        return;
      }

      int totalBytes = 0;
      await for (final entity in outputDir.list(recursive: true)) {
        if (entity is File) {
          totalBytes += await entity.length();
        }
      }

      storageUsed.value = _formatBytes(totalBytes);
    } catch (e) {
      storageUsed.value = 'N/A';
    }
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  // ═══════════════════════════════════════════════════════
  // Computed Properties
  // ═══════════════════════════════════════════════════════

  int get pendingCount {
    return recentProjects.where((p) => p.status.toString() != 'ProjectStatus.completed').length;
  }

  // ═══════════════════════════════════════════════════════
  // Navigation
  // ═══════════════════════════════════════════════════════

  void goToUpload() => Get.toNamed('/upload');
  void goToSetup() => Get.toNamed('/setup');

  void openProject(PrintProject project) {
    if (project.status.toString() == 'ProjectStatus.completed') {
      Get.toNamed('/preview', arguments: project);
    }
  }

  // ═══════════════════════════════════════════════════════
  // Project Management
  // ═══════════════════════════════════════════════════════

  Future<void> deleteProject(PrintProject project) async {
    try {
      await _projectRepository.deleteProject(project.id);
      await loadStats(); // Refresh
      Get.snackbar(
        'Success',
        'Project deleted',
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Error',
        'Failed to delete: $e',
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }

  @override
  void refresh() => loadStats();
}
