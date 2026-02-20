// lib/core/enums/app_enums.dart

enum PrintType {
  screenPrinting('Screen Printing', 'screen_printing', true),
  dtf('DTF (Direct to Film)', 'dtf', false),
  sublimation('Sublimation', 'sublimation', true),
  dtg('DTG (Direct to Garment)', 'dtg', false),
  flexVinyl('Flex/Vinyl Cutting', 'flex_vinyl', false);

  final String displayName;
  final String technicalName;
  final bool isAvailable;

  const PrintType(this.displayName, this.technicalName, this.isAvailable);

  bool get requiresFabricType => 
      this == dtf || this == dtg || this == sublimation;
  
  bool get requiresVectorization => this == flexVinyl;
  
  bool get supportsHalftone => this == screenPrinting;
}

enum DetailLevel {
  high('High', 0.1, 0.5),
  medium('Medium', 0.3, 1.0),
  low('Low', 0.5, 2.0);

  final String displayName;
  final double threshold;
  final double simplificationFactor;

  const DetailLevel(this.displayName, this.threshold, this.simplificationFactor);
}

enum PrintFinish {
  solid('Solid', false),
  halftone('Halftone', true);

  final String displayName;
  final bool requiresHalftoneSettings;

  const PrintFinish(this.displayName, this.requiresHalftoneSettings);
}

enum DotShape {
  round('Round', 'circle'),
  square('Square', 'square'),
  ellipse('Ellipse', 'ellipse');

  final String displayName;
  final String technicalName;

  const DotShape(this.displayName, this.technicalName);
}

enum FabricType {
  cotton('Cotton', 'cotton', false),
  polyester('Polyester', 'polyester', true),
  darkFabric('Dark Fabric', 'dark', false),
  lightFabric('Light Fabric', 'light', false);

  final String displayName;
  final String technicalName;
  final bool requiresSpecialHandling;

  const FabricType(this.displayName, this.technicalName, this.requiresSpecialHandling);
}

enum ProcessingStatus {
  idle('Idle'),
  uploading('Uploading'),
  preprocessing('Pre-processing'),
  analyzingColors('Analyzing Colors'),
  separatingColors('Separating Colors'),
  applyingHalftone('Applying Halftone'),
  generating('Generating Films'),
  completed('Completed'),
  failed('Failed');

  final String displayName;
  const ProcessingStatus(this.displayName);
}