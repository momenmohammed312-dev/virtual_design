// lib/core/mobile_ai/mobile_ai_service.dart
//
// On-device AI analysis:
//   • MobileNetV3 Small  → image class (text_logo / artwork / photo)
//   • DeepLabV3          → binary foreground mask (passed to FastAPI as hint)
//
// Falls back gracefully to a file-size heuristic when the model assets
// are absent (desktop dev builds, first-run before asset download, etc.)

import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';

// ── TFLite is optional: wrapped in a try/catch at runtime so the app
//    compiles and runs on desktop without the native .so / .dylib files.
//    On Android/iOS the tflite_flutter plugin is fully available.
// ignore: depend_on_referenced_packages
import 'package:tflite_flutter/tflite_flutter.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Public data types
// ─────────────────────────────────────────────────────────────────────────────

class MobileAISuggestions {
  final int? suggestedColors;
  final bool? forceHalftone;
  final int? suggestedLpi;
  final String? suggestedDotShape;
  final double? smoothingFactor;
  final double? cornerThreshold;

  const MobileAISuggestions({
    this.suggestedColors,
    this.forceHalftone,
    this.suggestedLpi,
    this.suggestedDotShape,
    this.smoothingFactor,
    this.cornerThreshold,
  });
}

class ImageAnalysisResult {
  /// One of: 'text_logo', 'artwork', 'photo', 'auto'
  final String imageClass;
  final double confidence;

  /// Absolute path to the DeepLabV3 foreground mask PNG, or null.
  final String? maskPath;

  final MobileAISuggestions? suggestions;

  /// 'tflite' | 'heuristic'
  final String source;

  const ImageAnalysisResult({
    required this.imageClass,
    required this.confidence,
    this.maskPath,
    this.suggestions,
    required this.source,
  });

  /// Legacy helper: args passed to python Process.run pipeline
  Map<String, String> toPythonArgs() {
    final map = <String, String>{
      '--image-class-hint': imageClass,
      '--ai-confidence': confidence.toString(),
    };
    if (maskPath != null && maskPath!.isNotEmpty) {
      map['--pre-mask'] = maskPath!;
    }
    return map;
  }

  /// API form-fields for FastAPI /process endpoint
  Map<String, String> toApiHints() => {
        'image_class_hint': imageClass,
        'ai_confidence': confidence.toStringAsFixed(4),
      };
}

// ─────────────────────────────────────────────────────────────────────────────
// Service
// ─────────────────────────────────────────────────────────────────────────────

class MobileAIService {
  // ── Singleton ──────────────────────────────────────────────────────────────
  static final MobileAIService _instance = MobileAIService._internal();
  factory MobileAIService() => _instance;
  MobileAIService._internal();

  // ── Model handles (null = not loaded / not available) ─────────────────────
  Interpreter? _classifier;
  Interpreter? _segmenter;
  List<String> _labels = [];
  bool _isInitialized = false;

  // ── Constants ──────────────────────────────────────────────────────────────
  static const int _clsSize = 224;   // MobileNetV3 input HxW
  static const int _segSize = 257;   // DeepLabV3  input HxW
  static const int _numVocClasses = 21; // PASCAL VOC classes (DeepLabV3)

  static const String _clsAsset = 'assets/models/mobilenet_v3.tflite';
  static const String _segAsset = 'assets/models/deeplab_v3.tflite';
  static const String _lblAsset = 'assets/labels/mobilenet_labels.txt';

  // ── Initialization ─────────────────────────────────────────────────────────

  Future<void> initialize() async {
    if (_isInitialized) return;
    _isInitialized = true; // mark early so concurrent calls don't re-enter

    try {
      final opts = InterpreterOptions()..threads = 4;

      _classifier = await Interpreter.fromAsset(_clsAsset, options: opts);
      _segmenter  = await Interpreter.fromAsset(_segAsset,  options: opts);

      final raw = await rootBundle.loadString(_lblAsset);
      _labels = raw
          .split('\n')
          .map((l) => l.trim())
          .where((l) => l.isNotEmpty)
          .toList();
    } catch (e) {
      // Models not bundled (desktop dev build or assets not downloaded yet).
      // Service degrades to pure heuristic — no crash.
      _classifier = null;
      _segmenter  = null;
      _labels     = [];
    }
  }

  // ── Public entry point ─────────────────────────────────────────────────────

  Future<ImageAnalysisResult> analyze(String imagePath) async {
    if (!_isInitialized) await initialize();

    final file = File(imagePath);
    if (!file.existsSync()) {
      return _heuristicFallback(imagePath);
    }

    if (_classifier == null) {
      return _heuristicFallback(imagePath);
    }

    try {
      final classResult = await _runClassification(file);
      final maskPath    = await _runSegmentation(file);
      final suggestions = _buildSuggestions(classResult.imageClass);

      return ImageAnalysisResult(
        imageClass: classResult.imageClass,
        confidence: classResult.confidence,
        maskPath:   maskPath,
        suggestions: suggestions,
        source: 'tflite',
      );
    } catch (_) {
      return _heuristicFallback(imagePath);
    }
  }

  // ── Classification ─────────────────────────────────────────────────────────

  Future<({String imageClass, double confidence})> _runClassification(
      File imageFile) async {
    final bytes   = await imageFile.readAsBytes();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) return (imageClass: 'artwork', confidence: 0.5);

    final resized = img.copyResize(decoded,
        width: _clsSize, height: _clsSize,
        interpolation: img.Interpolation.linear);

    // Build float32 input tensor [1, 224, 224, 3] — values in [0, 1]
    final inputData = Float32List(_clsSize * _clsSize * 3);
    int idx = 0;
    for (int y = 0; y < _clsSize; y++) {
      for (int x = 0; x < _clsSize; x++) {
        final p = resized.getPixel(x, y);
        inputData[idx++] = p.r / 255.0;
        inputData[idx++] = p.g / 255.0;
        inputData[idx++] = p.b / 255.0;
      }
    }
    final input = inputData.reshape([1, _clsSize, _clsSize, 3]);

    // Output [1, numLabels]
    final numLabels = _labels.isEmpty ? 3 : _labels.length;
    final outputData = Float32List(numLabels);
    final output = outputData.reshape([1, numLabels]);

    _classifier!.run(input, output);

    // Find argmax
    int bestIdx   = 0;
    double bestScore = outputData[0];
    for (int i = 1; i < outputData.length; i++) {
      if (outputData[i] > bestScore) {
        bestScore = outputData[i];
        bestIdx   = i;
      }
    }

    final rawLabel = (bestIdx < _labels.length)
        ? _labels[bestIdx].toLowerCase()
        : '';

    // Map raw ImageNet-style label → 3 silk-screen classes
    String imageClass = 'artwork';
    if (rawLabel.contains('logo') ||
        rawLabel.contains('text') ||
        rawLabel.contains('sign') ||
        rawLabel.contains('label')) {
      imageClass = 'text_logo';
    } else if (rawLabel.contains('photo') ||
        rawLabel.contains('portrait') ||
        rawLabel.contains('landscape') ||
        rawLabel.contains('face')) {
      imageClass = 'photo';
    }

    return (imageClass: imageClass, confidence: bestScore.clamp(0.0, 1.0));
  }

  // ── Segmentation ───────────────────────────────────────────────────────────

  Future<String?> _runSegmentation(File imageFile) async {
    if (_segmenter == null) return null;

    try {
      final bytes   = await imageFile.readAsBytes();
      final decoded = img.decodeImage(bytes);
      if (decoded == null) return null;

      final resized = img.copyResize(decoded,
          width: _segSize, height: _segSize,
          interpolation: img.Interpolation.linear);

      // Input [1, 257, 257, 3] — values in [-1, 1]
      final inputData = Float32List(_segSize * _segSize * 3);
      int idx = 0;
      for (int y = 0; y < _segSize; y++) {
        for (int x = 0; x < _segSize; x++) {
          final p = resized.getPixel(x, y);
          inputData[idx++] = (p.r / 127.5) - 1.0;
          inputData[idx++] = (p.g / 127.5) - 1.0;
          inputData[idx++] = (p.b / 127.5) - 1.0;
        }
      }
      final input = inputData.reshape([1, _segSize, _segSize, 3]);

      // Output [1, 257, 257, 21]
      final outputData =
          Float32List(_segSize * _segSize * _numVocClasses);
      final output =
          outputData.reshape([1, _segSize, _segSize, _numVocClasses]);

      _segmenter!.run(input, output);

      // Build binary mask: foreground (any class != 0) = 255, bg = 0
      final maskImage =
          img.Image(width: _segSize, height: _segSize);

      for (int y = 0; y < _segSize; y++) {
        for (int x = 0; x < _segSize; x++) {
          final base   = (y * _segSize + x) * _numVocClasses;
          final bgScore = outputData[base]; // class 0 = background

          double fgBest = 0.0;
          for (int c = 1; c < _numVocClasses; c++) {
            final s = outputData[base + c];
            if (s > fgBest) fgBest = s;
          }

          final val = fgBest > bgScore ? 255 : 0;
          maskImage.setPixelRgb(x, y, val, val, val);
        }
      }

      final tempDir  = await getTemporaryDirectory();
      final maskPath =
          '${tempDir.path}/pre_mask_${DateTime.now().millisecondsSinceEpoch}.png';
      await File(maskPath).writeAsBytes(img.encodePng(maskImage));
      return maskPath;
    } catch (_) {
      return null;
    }
  }

  // ── Suggestions ────────────────────────────────────────────────────────────

  MobileAISuggestions _buildSuggestions(String imageClass) {
    switch (imageClass) {
      case 'text_logo':
        return const MobileAISuggestions(
          suggestedColors: 2,
          forceHalftone: false,
          suggestedLpi: 65,
          suggestedDotShape: 'round',
          smoothingFactor: 0.1,
          cornerThreshold: 20.0,
        );
      case 'photo':
        return const MobileAISuggestions(
          suggestedColors: 0, // auto
          forceHalftone: true,
          suggestedLpi: 85,
          suggestedDotShape: 'round',
          smoothingFactor: 0.5,
          cornerThreshold: 40.0,
        );
      case 'artwork':
      default:
        return const MobileAISuggestions(
          suggestedColors: 4,
          forceHalftone: false,
          suggestedLpi: 75,
          suggestedDotShape: 'ellipse',
          smoothingFactor: 0.3,
          cornerThreshold: 30.0,
        );
    }
  }

  // ── Heuristic fallback ─────────────────────────────────────────────────────

  ImageAnalysisResult _heuristicFallback(String imagePath) {
    final file = File(imagePath);
    String imageClass = 'artwork';
    double confidence = 0.55;

    if (file.existsSync()) {
      final sizeBytes = file.lengthSync();
      if (sizeBytes > 5 * 1024 * 1024) {
        imageClass = 'photo';
        confidence = 0.65;
      } else if (sizeBytes < 200 * 1024) {
        imageClass = 'text_logo';
        confidence = 0.65;
      }
    }

    return ImageAnalysisResult(
      imageClass: imageClass,
      confidence: confidence,
      source: 'heuristic',
      suggestions: _buildSuggestions(imageClass),
    );
  }

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  void dispose() {
    _classifier?.close();
    _segmenter?.close();
    _classifier = null;
    _segmenter  = null;
    _isInitialized = false;
  }
}
