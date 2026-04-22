import 'dart:io';

class MobileAISuggestions {
  final int? suggestedColors;
  final bool? forceHalftone;
  final int? suggestedLpi;
  final String? suggestedDotShape;
  final double? smoothingFactor;
  final double? cornerThreshold;

  MobileAISuggestions({
    this.suggestedColors,
    this.forceHalftone,
    this.suggestedLpi,
    this.suggestedDotShape,
    this.smoothingFactor,
    this.cornerThreshold,
  });
}

class ImageAnalysisResult {
  final String imageClass; // 'photo', 'artwork', 'text_logo', 'auto'
  final double confidence;
  final String? maskPath;
  final MobileAISuggestions? suggestions;
  final String source; // 'tflite' or 'heuristic'

  ImageAnalysisResult({
    required this.imageClass,
    required this.confidence,
    this.maskPath,
    this.suggestions,
    required this.source,
  });

  Map<String, String> toPythonArgs() {
    final Map<String, String> args = {
      '--image-class-hint': imageClass,
      '--ai-confidence': confidence.toString(),
    };
    if (maskPath != null && maskPath!.isNotEmpty) {
      args['--pre-mask'] = maskPath!;
    }
    return args;
  }
}

class MobileAIService {
  // Singleton
  static final MobileAIService _instance = MobileAIService._internal();
  factory MobileAIService() => _instance;
  MobileAIService._internal();

  bool _isInitialized = false;

  Future<void> initialize() async {
    // Stage 1: Load TF Lite / TFLite_Flutter model here in the future
    // e.g. Tflite.loadModel(...)
    await Future.delayed(const Duration(milliseconds: 500));
    _isInitialized = true;
  }

  Future<ImageAnalysisResult> analyze(String imagePath) async {
    if (!_isInitialized) {
      await initialize();
    }
    
    // Stage 2 analysis: Heuristic or TFLite
    // For now, returning basic heuristic or dummy values
    String imgClass = _heuristicClassify(imagePath);
    String? mask = await _segment(imagePath);
    
    return ImageAnalysisResult(
      imageClass: imgClass,
      confidence: 0.85, // pseudo-confidence
      maskPath: mask,
      source: 'heuristic',
      suggestions: MobileAISuggestions(
        forceHalftone: imgClass == 'photo',
        suggestedColors: imgClass == 'text_logo' ? 2 : (imgClass == 'artwork' ? 5 : 0),
      ),
    );
  }

  String _heuristicClassify(String imagePath) {
    // Dummy Dart Heuristic - In real app, counts edges/colors using image package
    // Fallback logic of smart_analyzer.py
    final file = File(imagePath);
    if (!file.existsSync()) return 'auto';
    final size = file.lengthSync();
    // larger files -> might be photos if > 5MB
    if (size > 5 * 1024 * 1024) return 'photo';
    if (size < 100 * 1024) return 'text_logo';
    return 'artwork';
  }

  Future<String?> _segment(String imagePath) async {
    // Without DeeplabV3 loaded, return null to fallback to Python OR return a specific mask
    return null; 
  }
}
