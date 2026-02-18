// lib/data/models/processing_settings_model.dart

import 'package:hive/hive.dart';
import 'package:virtual_design/domain/entities/processing_settings.dart'
    as ps;

@HiveType(typeId: 0)
class ProcessingSettingsModel {
  @HiveField(0)
  final int colorCount;

  @HiveField(1)
  final String printFinish; // 'solid' or 'halftone'

  @HiveField(2)
  final String detailLevel; // 'high', 'medium', 'low'

  @HiveField(3)
  final double dpi;

  @HiveField(4)
  final double strokeWidthMm;

  @HiveField(5)
  final int meshCount;

  @HiveField(6)
  final String edgeEnhancement; // 'none', 'light', 'strong'

  @HiveField(7)
  final int? halftoneLpi;

  @HiveField(8)
  final String? halftoneDotShape; // 'round', 'square', 'ellipse'

  @HiveField(9)
  final double? halftoneAngle;

  ProcessingSettingsModel({
    this.colorCount = 2,
    this.printFinish = 'solid',
    this.detailLevel = 'medium',
    this.dpi = 300,
    this.strokeWidthMm = 0.3,
    this.meshCount = 160,
    this.edgeEnhancement = 'light',
    this.halftoneLpi,
    this.halftoneDotShape,
    this.halftoneAngle,
  });

  factory ProcessingSettingsModel.fromEntity(ps.ProcessingSettings entity) {
    return ProcessingSettingsModel(
      colorCount: entity.colorCount,
      detailLevel: entity.detailLevel.name,
      printFinish: entity.printFinish.name,
      strokeWidthMm: entity.strokeWidthMm,
      dpi: entity.dpi,
      meshCount: entity.meshCount,
      edgeEnhancement: entity.edgeEnhancement.name,
      halftoneLpi: entity.halftoneSettings?.lpi,
      halftoneDotShape: entity.halftoneSettings?.dotShape,
      halftoneAngle: entity.halftoneSettings?.angle,
    );
  }

  ps.ProcessingSettings toEntity() {
    final detailLevelEnum = ps.DetailLevel.values.firstWhere(
      (e) => e.name == detailLevel,
      orElse: () => ps.DetailLevel.medium,
    );

    final printFinishEnum = ps.PrintFinish.values.firstWhere(
      (e) => e.name == printFinish,
      orElse: () => ps.PrintFinish.solid,
    );

    final edgeEnhancementEnum = ps.EdgeEnhancement.values.firstWhere(
      (e) => e.name == edgeEnhancement,
      orElse: () => ps.EdgeEnhancement.light,
    );

    ps.HalftoneSettings? halftone;
    if (halftoneLpi != null && halftoneDotShape != null) {
      halftone = ps.HalftoneSettings(
        lpi: halftoneLpi!,
        dotShape: halftoneDotShape!,
        angle: halftoneAngle ?? 45.0,
      );
    }

    return ps.ProcessingSettings(
      colorCount: colorCount,
      detailLevel: detailLevelEnum,
      printFinish: printFinishEnum,
      strokeWidthMm: strokeWidthMm,
      dpi: dpi,
      meshCount: meshCount,
      edgeEnhancement: edgeEnhancementEnum,
      halftoneSettings: halftone,
    );
  }
}
