// lib/data/repositories/processing_repository_impl.dart

import '../../domain/repositories/processing_repository.dart';
import '../../domain/entities/processing_settings.dart';
import '../../core/python_bridge/process_result.dart';
import '../../core/python_bridge/python_processor.dart';
import '../datasources/local/hive_service.dart';

class ProcessingRepositoryImpl implements ProcessingRepository {
  final PythonProcessor _processor;
  final HiveService _hiveService;

  ProcessingRepositoryImpl({
    required PythonProcessor processor,
    HiveService? hiveService,
  }) : _processor = processor,
       _hiveService = hiveService ?? HiveService.instance;

  @override
  Future<ProcessResult> processImage({
    required String imagePath,
    required ProcessingSettings settings,
    String? outputDir,
    void Function(double, String)? onProgress,
  }) async {
    return await _processor.processImage(
      imagePath: imagePath,
      settings: settings,
      outputDir: outputDir,
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
    // Save as JSON directly (no Hive model needed)
    final box = await _hiveService.getSettingsBox();
    final json = {
      'colorCount': settings.colorCount,
      'detailLevel': settings.detailLevel.name,
      'printFinish': settings.printFinish.name,
      'strokeWidthMm': settings.strokeWidthMm,
      'dpi': settings.dpi,
      'meshCount': settings.meshCount,
      'edgeEnhancement': settings.edgeEnhancement.name,
      'halftoneSettings': settings.halftoneSettings != null
          ? {
              'lpi': settings.halftoneSettings!.lpi,
              'dotShape': settings.halftoneSettings!.dotShape,
              'angle': settings.halftoneSettings!.angle,
            }
          : null,
      'smoothingFactor': settings.smoothingFactor,
      'cornerThreshold': settings.cornerThreshold,
    };
    await box.put('last_settings', json);
  }

  @override
  Future<ProcessingSettings?> loadLastSettings() async {
    try {
      final box = await _hiveService.getSettingsBox();
      final json = box.get('last_settings');
      final Map<dynamic, dynamic>? rawJson = json as Map<dynamic, dynamic>?;
      if (rawJson == null) return null;

      final halftoneData = rawJson['halftoneSettings'] as Map?;
      
      return ProcessingSettings(
        colorCount: (rawJson['colorCount'] as num?)?.toInt() ?? 0,
        detailLevel: DetailLevel.values.firstWhere(
          (e) => e.name == rawJson['detailLevel'] as String?,
          orElse: () => DetailLevel.medium,
        ),
        printFinish: PrintFinish.values.firstWhere(
          (e) => e.name == rawJson['printFinish'] as String?,
          orElse: () => PrintFinish.solid,
        ),
        strokeWidthMm: (rawJson['strokeWidthMm'] as num?)?.toDouble() ?? 0.5,
        dpi: (rawJson['dpi'] as num?)?.toDouble() ?? 300.0,
        meshCount: (rawJson['meshCount'] as num?)?.toInt() ?? 200,
        edgeEnhancement: EdgeEnhancement.values.firstWhere(
          (e) => e.name == rawJson['edgeEnhancement'] as String?,
          orElse: () => EdgeEnhancement.light,
        ),
        halftoneSettings: halftoneData != null
            ? HalftoneSettings(
                lpi: (halftoneData['lpi'] as num).toInt(),
                dotShape: halftoneData['dotShape'] as String,
                angle: (halftoneData['angle'] as num?)?.toDouble() ?? 45.0,
              )
            : null,
        smoothingFactor: (rawJson['smoothingFactor'] as num?)?.toDouble() ?? 0.15,
        cornerThreshold: (rawJson['cornerThreshold'] as num?)?.toDouble() ?? 130.0,
      );
    } catch (e) {
      // MEDIUM #2 FIX: Handle corrupted or schema-mismatched Hive data
      print('[ProcessingRepo] Warning: Failed to load settings (data may be corrupted): $e');
      return null;
    }
  }
}
