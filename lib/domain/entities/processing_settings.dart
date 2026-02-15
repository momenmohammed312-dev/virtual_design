// lib/domain/entities/processing_settings.dart

import 'package:virtual_design/core/enums/app_enums.dart';

class ProcessingSettings {
  // Print Configuration
  final PrintType printType;
  final int colorCount;
  final DetailLevel detailLevel;
  final PrintFinish printFinish;
  
  // Halftone Settings (optional)
  final HalftoneSettings? halftoneSettings;
  
  // Physical Specifications
  final double strokeWidthMm;
  final String paperSize;
  final int copies;
  final double dpi;
  
  // Fabric Settings (optional, for DTF/DTG/Sublimation)
  final FabricType? fabricType;
  
  // Advanced Processing Options
  final bool autoUpscale;
  final bool removeBackground;
  final bool edgeEnhancement;
  final bool colorCorrection;
  
  ProcessingSettings({
    required this.printType,
    required this.colorCount,
    required this.detailLevel,
    required this.printFinish,
    this.halftoneSettings,
    required this.strokeWidthMm,
    required this.paperSize,
    required this.copies,
    required this.dpi,
    this.fabricType,
    this.autoUpscale = true,
    this.removeBackground = true,
    this.edgeEnhancement = false,
    this.colorCorrection = false,
  });
  
  // Validation
  bool isValid() {
    if (strokeWidthMm < 0.5) return false;
    if (colorCount < 1 || colorCount > 16) return false;
    if (dpi < 150) return false;
    if (printType.requiresFabricType && fabricType == null) return false;
    if (printFinish.requiresHalftoneSettings && halftoneSettings == null) return false;
    return true;
  }
  
  // Calculate stroke width in pixels
  int get strokeWidthInPixels {
    final strokeWidthCm = strokeWidthMm / 10;
    final strokeWidthInches = strokeWidthCm / 2.54;
    return (strokeWidthInches * dpi).round();
  }
  
  // Validation warnings
  List<String> getWarnings() {
    List<String> warnings = [];
    
    if (strokeWidthMm < 0.5 || strokeWidthInPixels < 6) {
      warnings.add('Strokes below 0.5mm may not print clearly');
    }
    
    if (dpi < 300) {
      warnings.add('Image resolution below recommended 300 DPI');
    }
    
    if (printType == PrintType.flexVinyl && colorCount > 3) {
      warnings.add('Flex printing works best with 1-3 colors');
    }
    
    if (halftoneSettings != null && 
        halftoneSettings!.lpi > 65 && 
        fabricType == FabricType.darkFabric) {
      warnings.add('High LPI on dark fabric may clog mesh');
    }
    
    return warnings;
  }
  
  // Factory constructor with defaults
  factory ProcessingSettings.defaults() {
    return ProcessingSettings(
      printType: PrintType.screenPrinting,
      colorCount: 4,
      detailLevel: DetailLevel.medium,
      printFinish: PrintFinish.solid,
      strokeWidthMm: 0.5,
      paperSize: 'A4 (210 × 297 mm)',
      copies: 1,
      dpi: 300,
      autoUpscale: true,
      removeBackground: true,
    );
  }

  ProcessingSettings copyWith({
    PrintType? printType,
    int? colorCount,
    DetailLevel? detailLevel,
    PrintFinish? printFinish,
    HalftoneSettings? halftoneSettings,
    double? strokeWidthMm,
    String? paperSize,
    int? copies,
    double? dpi,
    FabricType? fabricType,
    bool? autoUpscale,
    bool? removeBackground,
    bool? edgeEnhancement,
    bool? colorCorrection,
  }) {
    return ProcessingSettings(
      printType: printType ?? this.printType,
      colorCount: colorCount ?? this.colorCount,
      detailLevel: detailLevel ?? this.detailLevel,
      printFinish: printFinish ?? this.printFinish,
      halftoneSettings: halftoneSettings ?? this.halftoneSettings,
      strokeWidthMm: strokeWidthMm ?? this.strokeWidthMm,
      paperSize: paperSize ?? this.paperSize,
      copies: copies ?? this.copies,
      dpi: dpi ?? this.dpi,
      fabricType: fabricType ?? this.fabricType,
      autoUpscale: autoUpscale ?? this.autoUpscale,
      removeBackground: removeBackground ?? this.removeBackground,
      edgeEnhancement: edgeEnhancement ?? this.edgeEnhancement,
      colorCorrection: colorCorrection ?? this.colorCorrection,
    );
  }
}

class HalftoneSettings {
  final int lpi; // Lines Per Inch (45-85)
  final int meshCount; // Auto-calculated or manual
  final DotShape dotShape;
  final bool autoCalculateMesh;
  
  HalftoneSettings({
    required this.lpi,
    required this.meshCount,
    required this.dotShape,
    this.autoCalculateMesh = true,
  });
  
  // Calculate mesh count based on LPI
  static int calculateMeshCount(int lpi, DetailLevel detailLevel) {
    final multiplier = detailLevel == DetailLevel.high ? 5.0 :
                      detailLevel == DetailLevel.medium ? 4.5 : 4.0;
    return (lpi * multiplier).round();
  }
  
  // Factory with auto-calculated mesh
  factory HalftoneSettings.withAutoMesh({
    required int lpi,
    required DotShape dotShape,
    required DetailLevel detailLevel,
  }) {
    return HalftoneSettings(
      lpi: lpi,
      meshCount: calculateMeshCount(lpi, detailLevel),
      dotShape: dotShape,
      autoCalculateMesh: true,
    );
  }
  
  // Validation
  bool isValid() {
    return lpi >= 45 && lpi <= 85 && meshCount >= 110 && meshCount <= 230;
  }
  
  // Factory with defaults
  factory HalftoneSettings.defaults() {
    return HalftoneSettings(
      lpi: 55,
      meshCount: 110,
      dotShape: DotShape.round,
      autoCalculateMesh: true,
    );
  }

  HalftoneSettings copyWith({
    int? lpi,
    int? meshCount,
    DotShape? dotShape,
    bool? autoCalculateMesh,
  }) {
    return HalftoneSettings(
      lpi: lpi ?? this.lpi,
      meshCount: meshCount ?? this.meshCount,
      dotShape: dotShape ?? this.dotShape,
      autoCalculateMesh: autoCalculateMesh ?? this.autoCalculateMesh,
    );
  }
}