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
  })  : _processor = processor,
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
    try {
      final projects = _hiveService.getAllProjects();
      return projects.map((p) => p.name).toList();
    } catch (e) {
      print('[ProcessingRepo] Failed to load projects: $e');
      return [];
    }
  }

  @override
  Future<void> deleteProject(String projectId) async {
    await _hiveService.deleteProject(projectId);
  }

  @override
  Future<void> saveSettings(ProcessingSettings settings) async {
    try {
      final box = await _hiveService.getSettingsBox();
      // Persist ALL fields so loadLastSettings() restores a complete state.
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
        // Advanced tuning (were missing before — caused silent reset on next launch)
        'globalThreshold': settings.globalThreshold,
        'smoothingFactor': settings.smoothingFactor,
        'cornerThreshold': settings.cornerThreshold,
        'noiseRemoval': settings.noiseRemoval,
        'autoCrop': settings.autoCrop,
        'forceHalftone': settings.forceHalftone,
        'adaptiveThreshold': settings.adaptiveThreshold,
        'filmLabel': settings.filmLabel,
        'imageType': settings.imageType.name,
        // Professional features
        'pantoneMatching': settings.pantoneMatching.name,
        'underbaseMode': settings.underbaseMode.name,
        'trappingMode': settings.trappingMode.name,
        'overprintMode': settings.overprintMode.name,
        'gradientMeshMode': settings.gradientMeshMode.name,
        'typographyMode': settings.typographyMode.name,
        'meshPreviewMode': settings.meshPreviewMode.name,
      };
      await box.put('last_settings', json);
    } catch (e) {
      print('[ProcessingRepo] Warning: Failed to save settings: $e');
    }
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
        meshCount: (rawJson['meshCount'] as num?)?.toInt() ?? 160,
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
        // Advanced tuning
        globalThreshold:
            (rawJson['globalThreshold'] as num?)?.toDouble() ?? 200.0,
        smoothingFactor:
            (rawJson['smoothingFactor'] as num?)?.toDouble() ?? 0.25,
        cornerThreshold:
            (rawJson['cornerThreshold'] as num?)?.toDouble() ?? 45.0,
        noiseRemoval: (rawJson['noiseRemoval'] as num?)?.toInt() ?? 10,
        autoCrop: (rawJson['autoCrop'] as bool?) ?? false,
        forceHalftone: (rawJson['forceHalftone'] as bool?) ?? false,
        adaptiveThreshold: (rawJson['adaptiveThreshold'] as bool?) ?? false,
        filmLabel: (rawJson['filmLabel'] as String?) ?? '',
        imageType: ImageType.values.firstWhere(
          (e) => e.name == rawJson['imageType'] as String?,
          orElse: () => ImageType.auto,
        ),
        // Professional features
        pantoneMatching: PantoneMatching.values.firstWhere(
          (e) => e.name == rawJson['pantoneMatching'] as String?,
          orElse: () => PantoneMatching.automatic,
        ),
        underbaseMode: UnderbaseMode.values.firstWhere(
          (e) => e.name == rawJson['underbaseMode'] as String?,
          orElse: () => UnderbaseMode.automatic,
        ),
        trappingMode: TrappingMode.values.firstWhere(
          (e) => e.name == rawJson['trappingMode'] as String?,
          orElse: () => TrappingMode.automatic,
        ),
        overprintMode: OverprintMode.values.firstWhere(
          (e) => e.name == rawJson['overprintMode'] as String?,
          orElse: () => OverprintMode.automatic,
        ),
        gradientMeshMode: GradientMeshMode.values.firstWhere(
          (e) => e.name == rawJson['gradientMeshMode'] as String?,
          orElse: () => GradientMeshMode.automatic,
        ),
        typographyMode: TypographyMode.values.firstWhere(
          (e) => e.name == rawJson['typographyMode'] as String?,
          orElse: () => TypographyMode.automatic,
        ),
        meshPreviewMode: MeshPreviewMode.values.firstWhere(
          (e) => e.name == rawJson['meshPreviewMode'] as String?,
          orElse: () => MeshPreviewMode.automatic,
        ),
      );
    } catch (e) {
      print(
          '[ProcessingRepo] Warning: Failed to load settings (data may be corrupted): $e');
      return null;
    }
  }
}
