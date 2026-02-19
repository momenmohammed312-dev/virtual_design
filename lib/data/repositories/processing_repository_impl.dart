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
    };
    await box.put('last_settings', json);
  }

  @override
  Future<ProcessingSettings?> loadLastSettings() async {
    final box = await _hiveService.getSettingsBox();
    final json = box.get('last_settings');
    if (json == null || json is! Map) return null;

    final halftoneData = json['halftoneSettings'] as Map<String, dynamic>?;
    
    return ProcessingSettings(
      colorCount: json['colorCount'] as int,
      detailLevel: DetailLevel.values.firstWhere(
        (e) => e.name == json['detailLevel'] as String,
        orElse: () => DetailLevel.medium,
      ),
      printFinish: PrintFinish.values.firstWhere(
        (e) => e.name == json['printFinish'] as String,
        orElse: () => PrintFinish.solid,
      ),
      strokeWidthMm: (json['strokeWidthMm'] as num).toDouble(),
      dpi: (json['dpi'] as num).toDouble(),
      meshCount: (json['meshCount'] as num).toInt(),
      edgeEnhancement: EdgeEnhancement.values.firstWhere(
        (e) => e.name == json['edgeEnhancement'] as String,
        orElse: () => EdgeEnhancement.light,
      ),
      halftoneSettings: halftoneData != null
          ? HalftoneSettings(
              lpi: (halftoneData['lpi'] as num).toInt(),
              dotShape: halftoneData['dotShape'] as String,
              angle: (halftoneData['angle'] as num?)?.toDouble() ?? 45.0,
            )
          : null,
    );
  }
}
