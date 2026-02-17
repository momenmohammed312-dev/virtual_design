// lib/data/repositories/processing_repository_impl.dart

import '../../domain/repositories/processing_repository.dart';
import '../../domain/entities/processing_settings.dart';
import '../../core/python_bridge/process_result.dart';
import '../../core/python_bridge/python_processor.dart';
import '../datasources/local/hive_service.dart';
import '../models/processing_settings_model.dart';

class ProcessingRepositoryImpl implements ProcessingRepository {
  final PythonProcessor _processor;
  final HiveService _hiveService;

  ProcessingRepositoryImpl({
    PythonProcessor? processor,
    HiveService? hiveService,
  }) : _processor = processor ?? PythonProcessor(),
       _hiveService = hiveService ?? HiveService.instance;

  @override
  Future<ProcessResult> processImage({
    required String imagePath,
    required ProcessingSettings settings,
    void Function(double, String)? onProgress,
  }) async {
    return await _processor.processImage(
      imagePath: imagePath,
      settings: settings,
      onProgress: onProgress,
    );
  }

  @override
  Future<List<String>> getSavedProjects() async {
    return [];
  }

  @override
  Future<void> deleteProject(String projectId) async {
    await _hiveService.deleteProject(projectId);
  }

  @override
  Future<void> saveSettings(ProcessingSettings settings) async {
    final model = ProcessingSettingsModel.fromEntity(settings);
    await _hiveService.saveLastSettings(model);
  }

  @override
  Future<ProcessingSettings?> loadLastSettings() async {
    final model = _hiveService.loadLastSettings();
    return model?.toEntity();
  }
}
