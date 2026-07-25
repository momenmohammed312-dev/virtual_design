// processing_settings.dart - Domain Entity (updated)
// Virtual Designer - Screen Printing Studio
//
// MED #6 FIX: Added Mesh Count calculations that were missing despite being mentioned in SOP
// MED #3 FIX: Switch activeThumbColor deprecated - not related to this file
//             (Fix is in setup_page.dart)

import 'package:virtual_design/core/enums/app_enums.dart';

// --- Enums -------------------------------------------------------------------

enum PrintFinish { solid, halftone }

enum DetailLevel { high, medium, low }

enum EdgeEnhancement { none, light, strong }

// --- Professional Features ---------------------------------------------------

enum PantoneMatching { automatic, manual, disabled }

enum UnderbaseMode { automatic, manual, disabled }

enum TrappingMode { automatic, manual, disabled }

enum OverprintMode { automatic, manual, disabled }

enum GradientMeshMode { automatic, manual, disabled }

enum TypographyMode { automatic, manual, disabled }

enum MeshPreviewMode { automatic, manual, disabled }

enum ImageType { simple, mixed, complex, auto }

// --- Halftone Settings -------------------------------------------------------

class HalftoneSettings {
  final int lpi;
  final String dotShape;
  final double angle;
  final double dotSizeMultiplier;

  const HalftoneSettings({
    this.lpi = 85,
    this.dotShape = 'round',
    this.angle = 45.0,
    this.dotSizeMultiplier = 1.0,
  });

  HalftoneSettings copyWith({
    int? lpi,
    String? dotShape,
    double? angle,
    double? dotSizeMultiplier,
  }) =>
      HalftoneSettings(
        lpi: lpi ?? this.lpi,
        dotShape: dotShape ?? this.dotShape,
        angle: angle ?? this.angle,
        dotSizeMultiplier: dotSizeMultiplier ?? this.dotSizeMultiplier,
      );

  Map<String, dynamic> toJson() => {
        'lpi': lpi,
        'dotShape': dotShape,
        'angle': angle,
        'dotSizeMultiplier': dotSizeMultiplier,
      };

  factory HalftoneSettings.fromJson(Map<String, dynamic> json) =>
      HalftoneSettings(
        lpi: (json['lpi'] as int?) ?? 85,
        dotShape: (json['dotShape'] as String?) ?? 'round',
        angle: (json['angle'] as num?)?.toDouble() ?? 45.0,
        dotSizeMultiplier: (json['dotSizeMultiplier'] as num?)?.toDouble() ?? 1.0,
      );
}

// --- Processing Settings -----------------------------------------------------

class ProcessingSettings {
  final int colorCount;
  final PrintFinish printFinish;
  final DetailLevel detailLevel;
  final double dpi;
  final double strokeWidthMm;
  final int meshCount;
  final EdgeEnhancement edgeEnhancement;
  final HalftoneSettings? halftoneSettings;
  final double paperWidthCm;
  final double paperHeightCm;
  final double globalThreshold;
  final double smoothingFactor;
  final double cornerThreshold;
  final int noiseRemoval;
  final bool autoCrop;
  final bool forceHalftone;
  final bool adaptiveThreshold;
  final String filmLabel;
  final ImageType imageType;
  final int smoothingSlider;
  final bool responsiveMode;
  final PantoneMatching pantoneMatching;
  final UnderbaseMode underbaseMode;
  final TrappingMode trappingMode;
  final OverprintMode overprintMode;
  final GradientMeshMode gradientMeshMode;
  final TypographyMode typographyMode;
  final MeshPreviewMode meshPreviewMode;
  final double targetWidthMm;
  final int sourceDpi;
  final String scaleMode;
  final double customScalePercent;
  final List<double>? dotSizeMultipliers;
  final DotShape? overrideDotShape;
  
  // Mobile AI Hints
  final String? imageClassHint;
  final double? aiConfidence;
  final String? preMaskPath;
  final int? reprocessLayer;

  const ProcessingSettings({
    this.colorCount = 2,
    this.printFinish = PrintFinish.solid,
    this.detailLevel = DetailLevel.medium,
    this.dpi = 300,
    this.strokeWidthMm = 0.3,
    this.meshCount = 160,
    this.edgeEnhancement = EdgeEnhancement.light,
    this.halftoneSettings,
    this.paperWidthCm = 21.0,
    this.paperHeightCm = 29.7,
    this.globalThreshold = 0.0,
    this.smoothingFactor = -1.0,
    this.cornerThreshold = -1.0,
    this.noiseRemoval = 3,
    this.autoCrop = false,
    this.forceHalftone = false,
    this.adaptiveThreshold = false,
    this.filmLabel = '',
    this.imageType = ImageType.auto,
    this.pantoneMatching = PantoneMatching.automatic,
    this.underbaseMode = UnderbaseMode.automatic,
    this.trappingMode = TrappingMode.automatic,
    this.overprintMode = OverprintMode.automatic,
    this.gradientMeshMode = GradientMeshMode.automatic,
    this.typographyMode = TypographyMode.automatic,
    this.meshPreviewMode = MeshPreviewMode.automatic,
    this.smoothingSlider = 35,
    this.responsiveMode = false,
    this.targetWidthMm = 0.0,
    this.sourceDpi = 300,
    this.scaleMode = 'fit_to_page',
    this.customScalePercent = 100.0,
    this.dotSizeMultipliers,
    this.overrideDotShape,
    this.imageClassHint,
    this.aiConfidence,
    this.preMaskPath,
    this.reprocessLayer,
  });

  static const List<int> standardMeshCounts = [
    110,
    160,
    200,
    230,
    280,
    355,
  ];

  static int calculateOptimalLPI(int meshCount) {
    return (meshCount / 4.5).round().clamp(65, 150);
  }

  int get optimalLPI => calculateOptimalLPI(meshCount);

  static double calculateMinStrokeWidth(int meshCount) {
    final threadWidthMm = 25.4 / meshCount;
    return (threadWidthMm * 2).clamp(0.1, 2.0);
  }

  double get meshBasedMinStroke => calculateMinStrokeWidth(meshCount);

  String get meshDescription {
    if (meshCount <= 110) return 'Suitable for wide areas and large colors';
    if (meshCount <= 160) return 'Balanced - suitable for general printing';
    if (meshCount <= 230) return 'Suitable for medium details';
    if (meshCount <= 280) return 'For fine details';
    return 'For very high precision - requires special ink';
  }

  ProcessingSettings copyWith({
    int? colorCount,
    PrintFinish? printFinish,
    DetailLevel? detailLevel,
    double? dpi,
    double? strokeWidthMm,
    int? meshCount,
    EdgeEnhancement? edgeEnhancement,
    HalftoneSettings? halftoneSettings,
    double? paperWidthCm,
    double? paperHeightCm,
    double? globalThreshold,
    double? smoothingFactor,
    double? cornerThreshold,
    int? noiseRemoval,
    bool? autoCrop,
    bool? forceHalftone,
    bool? adaptiveThreshold,
    String? filmLabel,
    ImageType? imageType,
    PantoneMatching? pantoneMatching,
    UnderbaseMode? underbaseMode,
    TrappingMode? trappingMode,
    OverprintMode? overprintMode,
    GradientMeshMode? gradientMeshMode,
    TypographyMode? typographyMode,
    MeshPreviewMode? meshPreviewMode,
    int? smoothingSlider,
    bool? responsiveMode,
    double? targetWidthMm,
    int? sourceDpi,
    String? scaleMode,
    double? customScalePercent,
    List<double>? dotSizeMultipliers,
    int? reprocessLayer,
  }) =>
      ProcessingSettings(
        colorCount: colorCount ?? this.colorCount,
        printFinish: printFinish ?? this.printFinish,
        detailLevel: detailLevel ?? this.detailLevel,
        dpi: dpi ?? this.dpi,
        strokeWidthMm: strokeWidthMm ?? this.strokeWidthMm,
        meshCount: meshCount ?? this.meshCount,
        edgeEnhancement: edgeEnhancement ?? this.edgeEnhancement,
        halftoneSettings: halftoneSettings ?? this.halftoneSettings,
        paperWidthCm: paperWidthCm ?? this.paperWidthCm,
        paperHeightCm: paperHeightCm ?? this.paperHeightCm,
        globalThreshold: globalThreshold ?? this.globalThreshold,
        smoothingFactor: smoothingFactor ?? this.smoothingFactor,
        cornerThreshold: cornerThreshold ?? this.cornerThreshold,
        noiseRemoval: noiseRemoval ?? this.noiseRemoval,
        autoCrop: autoCrop ?? this.autoCrop,
        forceHalftone: forceHalftone ?? this.forceHalftone,
        adaptiveThreshold: adaptiveThreshold ?? this.adaptiveThreshold,
        filmLabel: filmLabel ?? this.filmLabel,
        imageType: imageType ?? this.imageType,
        pantoneMatching: pantoneMatching ?? this.pantoneMatching,
        underbaseMode: underbaseMode ?? this.underbaseMode,
        trappingMode: trappingMode ?? this.trappingMode,
        overprintMode: overprintMode ?? this.overprintMode,
        gradientMeshMode: gradientMeshMode ?? this.gradientMeshMode,
        typographyMode: typographyMode ?? this.typographyMode,
        meshPreviewMode: meshPreviewMode ?? this.meshPreviewMode,
        smoothingSlider: smoothingSlider ?? this.smoothingSlider,
        responsiveMode: responsiveMode ?? this.responsiveMode,
        targetWidthMm: targetWidthMm ?? this.targetWidthMm,
        sourceDpi: sourceDpi ?? this.sourceDpi,
        scaleMode: scaleMode ?? this.scaleMode,
        customScalePercent: customScalePercent ?? this.customScalePercent,
        dotSizeMultipliers: dotSizeMultipliers ?? this.dotSizeMultipliers,
        reprocessLayer: reprocessLayer ?? this.reprocessLayer,
      );

  /// Validates settings and returns list of error messages if any
  List<String> validate() {
    final errors = <String>[];

    if (dpi < 72 || dpi > 9600) {
      errors.add('DPI must be between 72 and 9600');
    }

    if (colorCount < 1 || colorCount > 12) {
      errors.add('Color count must be between 1 and 12');
    }

    if (meshCount < 40 || meshCount > 500) {
      errors.add('Mesh count must be between 40 and 500');
    }

    if (strokeWidthMm < 0.05 || strokeWidthMm > 5.0) {
      errors.add('Stroke width must be between 0.05 and 5.0 mm');
    }

    if (paperWidthCm <= 0 || paperHeightCm <= 0) {
      errors.add('Paper dimensions must be positive');
    }

    if (halftoneSettings != null) {
      final halftone = halftoneSettings!;
      if (halftone.lpi < 20 || halftone.lpi > 200) {
        errors.add('Halftone LPI must be between 20 and 200');
      }
    }

    return errors;
  }
}
