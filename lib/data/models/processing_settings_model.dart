// lib/data/models/processing_settings_model.dart

import 'package:hive/hive.dart';
import '../../domain/entities/processing_settings.dart';
import '../../core/enums/app_enums.dart';

part 'processing_settings_model.g.dart';

@HiveType(typeId: 0)
class ProcessingSettingsModel extends HiveObject {
  @HiveField(0)
  final String printType;

  @HiveField(1)
  final int colorCount;

  @HiveField(2)
  final String detailLevel;

  @HiveField(3)
  final String printFinish;

  @HiveField(4)
  final double strokeWidthMm;

  @HiveField(5)
  final String paperSize;

  @HiveField(6)
  final int copies;

  @HiveField(7)
  final double dpi;

  @HiveField(8)
  final String? fabricType;

  @HiveField(9)
  final bool autoUpscale;

  @HiveField(10)
  final bool removeBackground;

  @HiveField(11)
  final bool edgeEnhancement;

  @HiveField(12)
  final bool colorCorrection;

  @HiveField(13)
  final int? halftoneLpi;

  @HiveField(14)
  final String? halftoneDotShape;

  ProcessingSettingsModel({
    required this.printType,
    required this.colorCount,
    required this.detailLevel,
    required this.printFinish,
    required this.strokeWidthMm,
    required this.paperSize,
    required this.copies,
    required this.dpi,
    this.fabricType,
    required this.autoUpscale,
    required this.removeBackground,
    required this.edgeEnhancement,
    required this.colorCorrection,
    this.halftoneLpi,
    this.halftoneDotShape,
  });

  factory ProcessingSettingsModel.fromEntity(ProcessingSettings entity) {
    return ProcessingSettingsModel(
      printType: entity.printType.name,
      colorCount: entity.colorCount,
      detailLevel: entity.detailLevel.name,
      printFinish: entity.printFinish.name,
      strokeWidthMm: entity.strokeWidthMm,
      paperSize: entity.paperSize,
      copies: entity.copies,
      dpi: entity.dpi,
      fabricType: entity.fabricType?.name,
      autoUpscale: entity.autoUpscale,
      removeBackground: entity.removeBackground,
      edgeEnhancement: entity.edgeEnhancement,
      colorCorrection: entity.colorCorrection,
      halftoneLpi: entity.halftoneSettings?.lpi,
      halftoneDotShape: entity.halftoneSettings?.dotShape.name,
    );
  }

  ProcessingSettings toEntity() {
    final printTypeEnum = PrintType.values.firstWhere(
      (e) => e.name == printType,
      orElse: () => PrintType.screenPrinting,
    );

    final detailLevelEnum = DetailLevel.values.firstWhere(
      (e) => e.name == detailLevel,
      orElse: () => DetailLevel.medium,
    );

    final printFinishEnum = PrintFinish.values.firstWhere(
      (e) => e.name == printFinish,
      orElse: () => PrintFinish.solid,
    );

    FabricType? fabricTypeEnum;
    if (fabricType != null) {
      fabricTypeEnum = FabricType.values.firstWhere(
        (e) => e.name == fabricType,
        orElse: () => FabricType.cotton,
      );
    }

    HalftoneSettings? halftone;
    if (halftoneLpi != null && halftoneDotShape != null) {
      final dotShapeEnum = DotShape.values.firstWhere(
        (e) => e.name == halftoneDotShape,
        orElse: () => DotShape.round,
      );
      halftone = HalftoneSettings.withAutoMesh(
        lpi: halftoneLpi!,
        dotShape: dotShapeEnum,
        detailLevel: detailLevelEnum,
      );
    }

    return ProcessingSettings(
      printType: printTypeEnum,
      colorCount: colorCount,
      detailLevel: detailLevelEnum,
      printFinish: printFinishEnum,
      halftoneSettings: halftone,
      strokeWidthMm: strokeWidthMm,
      paperSize: paperSize,
      copies: copies,
      dpi: dpi,
      fabricType: fabricTypeEnum,
      autoUpscale: autoUpscale,
      removeBackground: removeBackground,
      edgeEnhancement: edgeEnhancement,
      colorCorrection: colorCorrection,
    );
  }
}
