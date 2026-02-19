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

// ─── Halftone Settings ────────────────────────────────────────────────────────

class HalftoneSettings {
  final int lpi;           // Lines Per Inch (25-85)
  final String dotShape;  // round, square, ellipse
  final double angle;     // rotation angle

  const HalftoneSettings({
    this.lpi = 65,
    this.dotShape = 'round',
    this.angle = 45.0,
  });

  HalftoneSettings copyWith({int? lpi, String? dotShape, double? angle}) =>
      HalftoneSettings(
        lpi: lpi ?? this.lpi,
        dotShape: dotShape ?? this.dotShape,
        angle: angle ?? this.angle,
      );

  Map<String, dynamic> toJson() =>
      {'lpi': lpi, 'dotShape': dotShape, 'angle': angle};

  factory HalftoneSettings.fromJson(Map<String, dynamic> json) =>
      HalftoneSettings(
        lpi: (json['lpi'] as int?) ?? 65,
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
  final int meshCount;           // عدد خيوط الشبكة (thread/inch)
  final EdgeEnhancement edgeEnhancement;
  final HalftoneSettings? halftoneSettings;

  const ProcessingSettings({
    this.colorCount = 2,
    this.printFinish = PrintFinish.solid,
    this.detailLevel = DetailLevel.medium,
    this.dpi = 300,
    this.strokeWidthMm = 0.3,
    this.meshCount = 160,          // 160 mesh شائع للطباعة العادية
    this.edgeEnhancement = EdgeEnhancement.light,
    this.halftoneSettings,
  });

  // ─── Mesh Count Calculations (MED #6 FIX) ──────────────────────────────

  /// قائمة المشات الشائعة في الطباعة على الحرير
  static const List<int> standardMeshCounts = [
    110,  // مناسب للألوان العريضة والمساحات الكبيرة
    160,  // الأكثر شيوعاً للطباعة العامة
    200,  // للتفاصيل المتوسطة
    230,  // للتفاصيل الدقيقة
    280,  // للتفاصيل الدقيقة جداً
    355,  // للطباعة عالية الدقة
  ];

  /// حساب LPI الأمثل بناءً على Mesh Count
  /// القاعدة الذهبية: LPI = MeshCount / 4
  /// (أكثر من ذلك → dots تتداخل مع الخيوط → نتيجة سيئة)
  static int calculateOptimalLPI(int meshCount) {
    return (meshCount / 4).round().clamp(25, 85);
  }

  /// حساب الـ LPI الأمثل للـ settings الحالية
  int get optimalLPI => calculateOptimalLPI(meshCount);

  /// حساب أدنى عرض خط مقبول بالـ mm بناءً على Mesh Count
  /// القاعدة: خيطان على الأقل لكل stroke
  static double calculateMinStrokeWidth(int meshCount) {
    final threadWidthMm = 25.4 / meshCount;  // عرض خيط واحد بالـ mm
    return (threadWidthMm * 2).clamp(0.1, 2.0);  // خيطان على الأقل
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
    if (colorCount < 1 || colorCount > 10) {
      errors.add('Color count must be between 1 and 10.');
    }
    if (dpi < 72 || dpi > 1200) {
      errors.add('DPI must be between 72 and 1200.');
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
    PrintFinish? printFinish,
    DetailLevel? detailLevel,
    double? dpi,
    double? strokeWidthMm,
    int? meshCount,
    EdgeEnhancement? edgeEnhancement,
    HalftoneSettings? halftoneSettings,
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
                json['halftoneSettings'] as Map<String, dynamic>)
            : null,
      );
}
