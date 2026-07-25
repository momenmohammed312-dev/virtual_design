// lib/data/repositories/processing_repository_impl.dart
import 'package:get/get.dart';
import 'package:virtual_design/domain/repositories/processing_repository.dart';
import 'package:virtual_design/domain/entities/processing_settings.dart';
import 'package:virtual_design/core/python_bridge/process_result.dart';
import 'package:virtual_design/core/python_bridge/python_processor.dart';
import 'package:virtual_design/data/datasources/local/hive_service.dart';

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
    // Convert ProcessingSettings to Map<String, dynamic>
    // Only include settings that Python main.py accepts
    final settingsMap = <String, dynamic>{
      // Core settings (mapped to Python argument names)
      'colors': settings.colorCount, // Python: --colors
      'detail-level': settings.detailLevel.name, // Python: --detail-level
      'dpi': settings.dpi,
      'mesh-count': settings.meshCount, // Python: --mesh-count
      'image-type': settings.imageType.name, // Python: --image-type
      'global-threshold':
          settings.globalThreshold, // Python: --global-threshold
      'smoothing-factor':
          settings.smoothingFactor, // Python: --smoothing-factor
      'corner-threshold':
          settings.cornerThreshold, // Python: --corner-threshold
      'noise-removal': settings.noiseRemoval, // Python: --noise-removal
      'adaptive-threshold':
          settings.adaptiveThreshold, // Python: --adaptive-threshold

      // Mode settings
      'pantone-matching':
          settings.pantoneMatching.name, // Python: --pantone-matching
      'underbase-mode': settings.underbaseMode.name, // Python: --underbase-mode
      'trapping-mode': settings.trappingMode.name, // Python: --trapping-mode
      'overprint-mode': settings.overprintMode.name, // Python: --overprint-mode
      'gradient-mesh-mode':
          settings.gradientMeshMode.name, // Python: --gradient-mesh-mode
      'typography-mode':
          settings.typographyMode.name, // Python: --typography-mode
      'mesh-preview-mode':
          settings.meshPreviewMode.name, // Python: --mesh-preview-mode

      // Scaling settings
      'target-width-mm': settings.targetWidthMm, // Python: --target-width-mm
      'source-dpi': settings.sourceDpi, // Python: --source-dpi
      'scale-mode': settings.scaleMode, // Python: --scale-mode
      'custom-scale-percent':
          settings.customScalePercent, // Python: --custom-scale-percent

      // Paper size settings (convert cm to mm for Python)
      'page-width': settings.paperWidthCm * 10, // Python: --page-width (mm)
      'page-height': settings.paperHeightCm * 10, // Python: --page-height (mm)
      'page-size': 'CUSTOM', // Python: --page-size (always custom for now)
      
      // Mobile AI Hints
      'image-class-hint': settings.imageClassHint,
      'ai-confidence': settings.aiConfidence,
      'pre-mask': settings.preMaskPath,
    };

    // ⚠️ HALFTONE MODE ENFORCEMENT: User's UI choice must be explicit
    // Python needs to know if user explicitly chose halftone OR solid
    if (settings.printFinish == PrintFinish.halftone ||
        settings.forceHalftone) {
      // User explicitly wants halftone
      settingsMap['halftone'] = true;
    }

    // Add halftone settings if present
    if (settings.halftoneSettings != null) {
      settingsMap['lpi'] = settings.halftoneSettings!.lpi; // Python: --lpi
      settingsMap['dot-shape'] =
          settings.halftoneSettings!.dotShape; // Python: --dot-shape
      // Python doesn't use angle directly, it's handled in halftone generation

      // Per-layer dot sizes
      if (settings.dotSizeMultipliers != null && settings.dotSizeMultipliers!.isNotEmpty) {
        settingsMap['dot-sizes'] = settings.dotSizeMultipliers!
            .map((v) => v.toStringAsFixed(2))
            .join(',');
      } else {
        settingsMap['dot-size'] = settings.halftoneSettings?.dotSizeMultiplier ?? 1.0;
      }
    }

    // Filter out null values and false booleans (for flags)
    settingsMap.removeWhere((key, value) {
      if (value == null) return true;
      if (key == 'halftone') return false;
      if (value is bool && !value) return true; // Remove false flags
      if (value is String && value.isEmpty) return true;
      return false;
    });

    return await _processor.processImage(
      imagePath: imagePath,
      settings: settingsMap,
      outputDir: outputDir,
      onProgress: onProgress,
    );
  }

  @override
  Future<ProcessResult> processImageFromMap({
    required String imagePath,
    required Map<String, dynamic> settingsMap,
    String? outputDir,
    void Function(double progress, String message)? onProgress,
  }) async {
    return await _processor.processImage(
      imagePath: imagePath,
      settings: settingsMap,
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
      Get.log('[ProcessingRepo] Failed to load projects: $e');
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
                'dotSizeMultiplier': settings.halftoneSettings!.dotSizeMultiplier,
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
        'smoothingSlider': settings.smoothingSlider,
      };
      await box.put('last_settings', json);
    } catch (e) {
      Get.log('[ProcessingRepo] Warning: Failed to save settings: $e');
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
                dotSizeMultiplier: (halftoneData['dotSizeMultiplier'] as num?)?.toDouble() ?? 1.0,
              )
            : null,
        // Advanced tuning
        globalThreshold:
            (rawJson['globalThreshold'] as num?)?.toDouble() ?? 180.0,
        smoothingFactor:
            (rawJson['smoothingFactor'] as num?)?.toDouble() ?? -1.0,
        cornerThreshold:
            (rawJson['cornerThreshold'] as num?)?.toDouble() ?? -1.0,
        noiseRemoval: (rawJson['noiseRemoval'] as num?)?.toInt() ?? 3,
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
        smoothingSlider: (rawJson['smoothingSlider'] as num?)?.toInt() ?? 35,
      );
    } catch (e) {
      Get.log(
          '[ProcessingRepo] Warning: Failed to load settings (data may be corrupted): $e');
      return null;
    }
  }
}
