// lib/domain/repositories/processing_repository.dart

import 'package:virtual_design/core/python_bridge/process_result.dart';
import 'package:virtual_design/domain/entities/processing_settings.dart';

/// Repository interface for image processing operations
/// This follows Clean Architecture - Domain layer defines the contract
abstract class ProcessingRepository {
  /// Process an image with given settings
  /// Returns ProcessResult with generated films
  Future<ProcessResult> processImage({
    required String imagePath,
    required ProcessingSettings settings,
    String? outputDir,
    void Function(double progress, String message)? onProgress,
  });

  /// Process an image using a raw settings map (used by ServerConnector for local fallback)
  Future<ProcessResult> processImageFromMap({
    required String imagePath,
    required Map<String, dynamic> settingsMap,
    String? outputDir,
    void Function(double progress, String message)? onProgress,
  });

  /// Get list of saved projects
  Future<List<String>> getSavedProjects();

  /// Delete a project by ID
  Future<void> deleteProject(String projectId);

  /// Save processing settings for reuse
  Future<void> saveSettings(ProcessingSettings settings);

  /// Load last used settings
  Future<ProcessingSettings?> loadLastSettings();
}
