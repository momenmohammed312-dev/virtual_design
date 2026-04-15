// processing_settings.dart — Domain Entity (updated)
// Virtual Design Silk Screen Studio
//
// MED #6 FIX: إضافة Mesh Count calculations كانت غائبة رغم ذكرها في SOP
// MED #3 FIX: Switch activeThumbColor deprecated — لا علاقة بهذا الملف
//             (الإصلاح في setup_page.dart)

// ─── Enums ───────────────────────────────────────────────────────────────────

enum PrintFinish { solid, halftone }

enum DetailLevel { high, medium, low }

enum EdgeEnhancement { none, light, strong }

// ─── Professional Features ────────────────────────────────────────────────────

enum PantoneMatching { automatic, manual, disabled }

enum UnderbaseMode { automatic, manual, disabled }

enum TrappingMode { automatic, manual, disabled }

enum OverprintMode { automatic, manual, disabled }

enum GradientMeshMode { automatic, manual, disabled }

enum TypographyMode { automatic, manual, disabled }

enum MeshPreviewMode { automatic, manual, disabled }

enum ImageType { simple, mixed, complex, auto }

// ─── Halftone Settings ────────────────────────────────────────────────────────

class HalftoneSettings {
  final int lpi; // Lines Per Inch (65-150, higher = smaller dots)
  final String dotShape; // round, square, ellipse
  final double angle; // rotation angle

  const HalftoneSettings({
    this.lpi = 85, // Default for finer dots
    this.dotShape = 'round',
    this.angle = 45.0,
  });

  HalftoneSettings copyWith({int? lpi, String? dotShape, double? angle}) =>
      HalftoneSettings(
        lpi: lpi ?? this.lpi,
        dotShape: dotShape ?? this.dotShape,
        angle: angle ?? this.angle,
      );

  Map<String, dynamic> toJson() => {
        'lpi': lpi,
        'dotShape': dotShape,
        'angle': angle,
      };

  factory HalftoneSettings.fromJson(Map<String, dynamic> json) =>
      HalftoneSettings(
        lpi: (json['lpi'] as int?) ?? 85,
        dotShape: (json['dotShape'] as String?) ?? 'round',
        angle: (json['angle'] as num?)?.toDouble() ?? 45.0,
      );
}

// ─── Processing Settings ──────────────────────────────────────────────────────

class ProcessingSettings {
  final int colorCount;
  final PrintFinish printFinish;
  final DetailLevel detailLevel;
  final double dpi;
  final double strokeWidthMm;
  final int meshCount; // عدد خيوط الشبكة (thread/inch)
  final EdgeEnhancement edgeEnhancement;
  final HalftoneSettings? halftoneSettings;
  final double paperWidthCm;
  final double paperHeightCm;

  // Advanced Tuning (Phase 8 Senior Optimizations)
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

  // Professional Features (all enabled by default)
  final PantoneMatching pantoneMatching;
  final UnderbaseMode underbaseMode;
  final TrappingMode trappingMode;
  final OverprintMode overprintMode;
  final GradientMeshMode gradientMeshMode;
  final TypographyMode typographyMode;
  final MeshPreviewMode meshPreviewMode;

  const ProcessingSettings({
    this.colorCount = 2,
    this.printFinish = PrintFinish.solid,
    this.detailLevel = DetailLevel.medium,
    this.dpi = 300,
    this.strokeWidthMm = 0.3,
    this.meshCount = 160, // 160 mesh شائع للطباعة العادية
    this.edgeEnhancement = EdgeEnhancement.light,
    this.halftoneSettings,
    this.paperWidthCm = 21.0,
    this.paperHeightCm = 29.7,
    // Advanced Tuning Defaults
    this.globalThreshold = 0.0, // 0 = Auto (Senior Engine decides)
    this.smoothingFactor = 0.25,
    this.cornerThreshold = 45.0,
    this.noiseRemoval = 3,
    this.autoCrop = false,
    this.forceHalftone = false,
    this.adaptiveThreshold = false,
    this.filmLabel = '',
    this.imageType = ImageType.auto,
    // Professional Features — all enabled automatically
    this.pantoneMatching = PantoneMatching.automatic,
    this.underbaseMode = UnderbaseMode.automatic,
    this.trappingMode = TrappingMode.automatic,
    this.overprintMode = OverprintMode.automatic,
    this.gradientMeshMode = GradientMeshMode.automatic,
    this.typographyMode = TypographyMode.automatic,
    this.meshPreviewMode = MeshPreviewMode.automatic,
    this.smoothingSlider = 35,
    this.responsiveMode = false,
  });

  // ─── Mesh Count Calculations (MED #6 FIX) ──────────────────────────────

  /// قائمة المشات الشائعة في الطباعة على الحرير
  static const List<int> standardMeshCounts = [
    110, // مناسب للألوان العريضة والمساحات الكبيرة
    160, // الأكثر شيوعاً للطباعة العامة
    200, // للتفاصيل المتوسطة
    230, // للتفاصيل الدقيقة
    280, // للتفاصيل الدقيقة جداً
    355, // للطباعة عالية الدقة
  ];

  /// حساب LPI بناءً على Mesh Count (الأمان التقليدي)
  /// القاعدة: LPI = MeshCount / 4.5 للأمان
  /// مع DPI عالي (1200+) ممكن LPI أعلى
  static int calculateOptimalLPI(int meshCount) {
    return (meshCount / 4.5).round().clamp(65, 150);
  }

  /// حساب الـ LPI الأمثل للـ settings الحالية
  int get optimalLPI => calculateOptimalLPI(meshCount);

  /// حساب أدنى عرض خط مقبول بالـ mm بناءً على Mesh Count
  /// القاعدة: خيطان على الأقل لكل stroke
  static double calculateMinStrokeWidth(int meshCount) {
    final threadWidthMm = 25.4 / meshCount; // عرض خيط واحد بالـ mm
    return (threadWidthMm * 2).clamp(0.1, 2.0); // خيطان على الأقل
  }

  /// الـ stroke width الأدنى بناءً على الـ mesh الحالي
  double get meshBasedMinStroke => calculateMinStrokeWidth(meshCount);

  /// وصف الـ mesh Count للعرض في الـ UI
  String get meshDescription {
    if (meshCount <= 110) return 'مناسب للمساحات العريضة والألوان الكبيرة';
    if (meshCount <= 160) return 'متوازن — مناسب للطباعة العامة';
    if (meshCount <= 230) return 'مناسب للتفاصيل المتوسطة';
    if (meshCount <= 280) return 'للتفاصيل الدقيقة';
    return 'للدقة العالية جداً — يتطلب حبر خاص';
  }

  /// تحذيرات بناءً على الإعدادات الحالية
  List<String> get warnings {
    final warns = <String>[];

    // تحذير Halftone + Mesh
    if (printFinish == PrintFinish.halftone && halftoneSettings != null) {
      final lpi = halftoneSettings!.lpi;
      if (lpi > optimalLPI) {
        warns.add(
          'LPI ($lpi) أعلى من الأمثل لـ $meshCount mesh ($optimalLPI). '
          'قد تظهر مشاكل في الطباعة.',
        );
      }
    }

    // تحذير Stroke Width
    if (strokeWidthMm < meshBasedMinStroke) {
      warns.add(
        'عرض الخط ($strokeWidthMm mm) أقل من الحد الأدنى '
        'لـ $meshCount mesh (${meshBasedMinStroke.toStringAsFixed(2)} mm).',
      );
    }

    // تحذير عدد الألوان العالي
    if (colorCount > 4) {
      warns.add('عدد ألوان كبير ($colorCount) — تأكد من جودة التسجيل.');
    }

    return warns;
  }

  // ─── Validation ──────────────────────────────────────────────────────────

  List<String> validate() {
    final errors = <String>[];
    // Allow 0 to denote automatic color counting
    if (colorCount != 0 && (colorCount < 1 || colorCount > 10)) {
      errors.add('Color count must be between 1 and 10.');
    }
    if (dpi < 72 || dpi > 4800) {
      errors.add('DPI must be between 72 and 4800.');
    }
    if (strokeWidthMm < 0.1 || strokeWidthMm > 10) {
      errors.add('Stroke width must be between 0.1 and 10 mm.');
    }
    if (!standardMeshCounts.contains(meshCount) && meshCount > 0) {
      // mesh غير معياري — تحذير لا خطأ
    }
    return errors;
  }

  bool get isValid => validate().isEmpty;

  // ─── Copy & JSON ─────────────────────────────────────────────────────────

  ProcessingSettings copyWith({
    int? colorCount,
    DetailLevel? detailLevel,
    PrintFinish? printFinish,
    EdgeEnhancement? edgeEnhancement,
    double? dpi,
    int? meshCount,
    HalftoneSettings? halftoneSettings,
    double? strokeWidthMm,
    double? paperWidthCm,
    double? paperHeightCm,
    PantoneMatching? pantoneMatching,
    UnderbaseMode? underbaseMode,
    TrappingMode? trappingMode,
    OverprintMode? overprintMode,
    GradientMeshMode? gradientMeshMode,
    TypographyMode? typographyMode,
    MeshPreviewMode? meshPreviewMode,
    double? globalThreshold,
    double? smoothingFactor,
    double? cornerThreshold,
    int? noiseRemoval,
    bool? autoCrop,
    bool? forceHalftone,
    bool? adaptiveThreshold,
    String? filmLabel,
    ImageType? imageType,
    int? smoothingSlider,
    bool? responsiveMode,
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
        pantoneMatching: pantoneMatching ?? this.pantoneMatching,
        underbaseMode: underbaseMode ?? this.underbaseMode,
        trappingMode: trappingMode ?? this.trappingMode,
        overprintMode: overprintMode ?? this.overprintMode,
        gradientMeshMode: gradientMeshMode ?? this.gradientMeshMode,
        typographyMode: typographyMode ?? this.typographyMode,
        meshPreviewMode: meshPreviewMode ?? this.meshPreviewMode,
        globalThreshold: globalThreshold ?? this.globalThreshold,
        smoothingFactor: smoothingFactor ?? this.smoothingFactor,
        cornerThreshold: cornerThreshold ?? this.cornerThreshold,
        noiseRemoval: noiseRemoval ?? 3,
        autoCrop: autoCrop ?? this.autoCrop,
        forceHalftone: forceHalftone ?? this.forceHalftone,
        adaptiveThreshold: adaptiveThreshold ?? this.adaptiveThreshold,
        filmLabel: filmLabel ?? this.filmLabel,
        imageType: imageType ?? this.imageType,
        smoothingSlider: smoothingSlider ?? this.smoothingSlider,
        responsiveMode: responsiveMode ?? this.responsiveMode,
      );

  Map<String, dynamic> toJson() => {
        'colorCount': colorCount,
        'printFinish': printFinish.name,
        'detailLevel': detailLevel.name,
        'dpi': dpi,
        'strokeWidthMm': strokeWidthMm,
        'meshCount': meshCount,
        'edgeEnhancement': edgeEnhancement.name,
        'halftoneSettings': halftoneSettings?.toJson(),
        'paperWidthCm': paperWidthCm,
        'paperHeightCm': paperHeightCm,
        'pantoneMatching': pantoneMatching.name,
        'underbaseMode': underbaseMode.name,
        'trappingMode': trappingMode.name,
        'overprintMode': overprintMode.name,
        'gradientMeshMode': gradientMeshMode.name,
        'typographyMode': typographyMode.name,
        'meshPreviewMode': meshPreviewMode.name,
        'globalThreshold': globalThreshold,
        'smoothingFactor': smoothingFactor,
        'cornerThreshold': cornerThreshold,
        'noiseRemoval': noiseRemoval,
        'autoCrop': autoCrop,
        'forceHalftone': forceHalftone,
        'adaptiveThreshold': adaptiveThreshold,
        'filmLabel': filmLabel,
        'imageType': imageType.name,
        'smoothingSlider': smoothingSlider,
        'responsiveMode': responsiveMode,
      };

  factory ProcessingSettings.fromJson(Map<String, dynamic> json) =>
      ProcessingSettings(
        colorCount: (json['colorCount'] as int?) ?? 2,
        printFinish: PrintFinish.values.firstWhere(
          (e) => e.name == json['printFinish'],
          orElse: () => PrintFinish.solid,
        ),
        detailLevel: DetailLevel.values.firstWhere(
          (e) => e.name == json['detailLevel'],
          orElse: () => DetailLevel.medium,
        ),
        dpi: (json['dpi'] as num?)?.toDouble() ?? 300,
        strokeWidthMm: (json['strokeWidthMm'] as num?)?.toDouble() ?? 0.3,
        meshCount: (json['meshCount'] as int?) ?? 160,
        edgeEnhancement: EdgeEnhancement.values.firstWhere(
          (e) => e.name == json['edgeEnhancement'],
          orElse: () => EdgeEnhancement.light,
        ),
        halftoneSettings: json['halftoneSettings'] != null
            ? HalftoneSettings.fromJson(
                json['halftoneSettings'] as Map<String, dynamic>,
              )
            : null,
        paperWidthCm: (json['paperWidthCm'] as num?)?.toDouble() ?? 21.0,
        paperHeightCm: (json['paperHeightCm'] as num?)?.toDouble() ?? 29.7,
        pantoneMatching: PantoneMatching.values.firstWhere(
          (e) => e.name == json['pantoneMatching'],
          orElse: () => PantoneMatching.automatic,
        ),
        underbaseMode: UnderbaseMode.values.firstWhere(
          (e) => e.name == json['underbaseMode'],
          orElse: () => UnderbaseMode.automatic,
        ),
        trappingMode: TrappingMode.values.firstWhere(
          (e) => e.name == json['trappingMode'],
          orElse: () => TrappingMode.automatic,
        ),
        overprintMode: OverprintMode.values.firstWhere(
          (e) => e.name == json['overprintMode'],
          orElse: () => OverprintMode.automatic,
        ),
        gradientMeshMode: GradientMeshMode.values.firstWhere(
          (e) => e.name == json['gradientMeshMode'],
          orElse: () => GradientMeshMode.automatic,
        ),
        typographyMode: TypographyMode.values.firstWhere(
          (e) => e.name == json['typographyMode'],
          orElse: () => TypographyMode.automatic,
        ),
        meshPreviewMode: MeshPreviewMode.values.firstWhere(
          (e) => e.name == json['meshPreviewMode'],
          orElse: () => MeshPreviewMode.automatic,
        ),
        globalThreshold: (json['globalThreshold'] as num?)?.toDouble() ?? 0.0,
        smoothingFactor: (json['smoothingFactor'] as num?)?.toDouble() ?? 0.25,
        cornerThreshold: (json['cornerThreshold'] as num?)?.toDouble() ?? 45.0,
        noiseRemoval: (json['noiseRemoval'] as int?) ?? 3,
        autoCrop: (json['autoCrop'] as bool?) ?? false,
        forceHalftone: (json['forceHalftone'] as bool?) ?? false,
        adaptiveThreshold: (json['adaptiveThreshold'] as bool?) ?? false,
        filmLabel: (json['filmLabel'] as String?) ?? '',
        imageType: ImageType.values.firstWhere(
          (e) => e.name == json['imageType'],
          orElse: () => ImageType.auto,
        ),
        smoothingSlider: (json['smoothingSlider'] as int?) ?? 35,
        responsiveMode: (json['responsiveMode'] as bool?) ?? false,
      );
}
