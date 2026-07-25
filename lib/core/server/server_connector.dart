// lib/core/server/server_connector.dart
//
// Decides transparently whether to route image processing to:
//   A) The FastAPI server on the PC (WiFi/LAN)  — full Qwen pipeline
//   B) The local Python bridge (desktop only)   — same pipeline, Process.run
//
// The Flutter UI only calls processImage() and reacts to [mode].

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:archive/archive_io.dart';
import 'package:get/get.dart' hide Response;
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import 'package:virtual_design/core/python_bridge/python_processor.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Supporting types
// ─────────────────────────────────────────────────────────────────────────────

enum ConnectionMode { server, local }

class ProcessingResult {
  final bool success;
  final String? outputDirectory;
  final String? error;

  const ProcessingResult._({
    required this.success,
    this.outputDirectory,
    this.error,
  });

  factory ProcessingResult.success(String outputDirectory) =>
      ProcessingResult._(success: true, outputDirectory: outputDirectory);

  factory ProcessingResult.failure(String error) =>
      ProcessingResult._(success: false, error: error);
}

// ─────────────────────────────────────────────────────────────────────────────
// ServerConnector
// ─────────────────────────────────────────────────────────────────────────────

class ServerConnector extends GetxController {
  // ── Singleton ──────────────────────────────────────────────────────────────
  static final ServerConnector _instance = ServerConnector._internal();
  factory ServerConnector() => _instance;
  ServerConnector._internal();

  // ── Observables (the UI can watch these with Obx) ─────────────────────────
  final Rx<ConnectionMode> mode = ConnectionMode.local.obs;
  final RxBool isChecking = false.obs;
  final RxString serverUrl = 'http://192.168.1.100:8000'.obs;

  // ── Internal ───────────────────────────────────────────────────────────────
  Timer? _pingTimer;
  static const _pingInterval = Duration(seconds: 30);
  static const _pingTimeout = Duration(seconds: 3);
  static const _uploadTimeout = Duration(minutes: 5);

  bool get isServerMode => mode.value == ConnectionMode.server;

  // ── Auto-detect ────────────────────────────────────────────────────────────

  void startAutoDetect() {
    _checkServer();
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(_pingInterval, (_) => _checkServer());
  }

  @override
  void onClose() {
    _pingTimer?.cancel();
    super.onClose();
  }

  Future<void> _checkServer() async {
    if (isChecking.value) return;
    isChecking.value = true;
    try {
      final uri = Uri.parse('${serverUrl.value}/health');
      final response = await http.get(uri).timeout(_pingTimeout);
      mode.value = (response.statusCode == 200)
          ? ConnectionMode.server
          : ConnectionMode.local;
    } catch (_) {
      mode.value = ConnectionMode.local;
    } finally {
      isChecking.value = false;
    }
  }

  /// Manually set the PC server URL and immediately re-check connectivity.
  void setServerUrl(String url) {
    final sanitized = url.trim().replaceAll(RegExp(r'/$'), '');
    serverUrl.value = sanitized;
    _checkServer();
  }

  // ── Primary entry point ───────────────────────────────────────────────────

  /// Route processing automatically: server if reachable, local otherwise.
  Future<ProcessingResult> processImage({
    required String imagePath,
    required Map<String, dynamic> settings,
    String? maskPath,
    String imageClassHint = 'auto',
    double aiConfidence = 0.0,
    void Function(double progress, String message)? onProgress,
  }) async {
    if (isServerMode) {
      return _processViaServer(
        imagePath: imagePath,
        settings: settings,
        maskPath: maskPath,
        imageClassHint: imageClassHint,
        aiConfidence: aiConfidence,
        onProgress: onProgress,
      );
    }

    return _processLocally(
      imagePath: imagePath,
      settings: settings,
      maskPath: maskPath,
      imageClassHint: imageClassHint,
      aiConfidence: aiConfidence,
      onProgress: onProgress,
    );
  }

  // ── Server path ───────────────────────────────────────────────────────────

  Future<ProcessingResult> _processViaServer({
    required String imagePath,
    required Map<String, dynamic> settings,
    String? maskPath,
    required String imageClassHint,
    required double aiConfidence,
    void Function(double, String)? onProgress,
  }) async {
    onProgress?.call(0.05, 'Connecting to server…');

    // Re-check server just in case it dropped since last ping
    await _checkServer();
    if (!isServerMode) {
      return ProcessingResult.failure(
        'Server not reachable. Connect your PC to the same WiFi network.',
      );
    }

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${serverUrl.value}/process'),
      );

      // ── image file ──────────────────────────────────────────────────────
      request.files.add(
        await http.MultipartFile.fromPath('file', imagePath),
      );

      // ── settings from controller ────────────────────────────────────────
      settings.forEach((k, v) => request.fields[k] = v.toString());

      // ── mobile-AI hints ─────────────────────────────────────────────────
      request.fields['image_class_hint'] = imageClassHint;
      request.fields['ai_confidence'] = aiConfidence.toStringAsFixed(4);

      if (aiConfidence >= 0.90 && imageClassHint != 'auto') {
        request.fields['no_ai'] = 'true';
      }

      // ── DeepLabV3 mask (base64) ─────────────────────────────────────────
      if (maskPath != null) {
        final maskFile = File(maskPath);
        if (maskFile.existsSync()) {
          final maskBytes = await maskFile.readAsBytes();
          request.fields['pre_mask_b64'] = base64Encode(maskBytes);
        }
      }

      onProgress?.call(0.2, 'Uploading image to PC…');

      final streamed = await request.send().timeout(_uploadTimeout);

      onProgress?.call(0.55, 'Server processing (Qwen + pipeline)…');

      if (streamed.statusCode != 200) {
        final body = await streamed.stream.bytesToString();
        return ProcessingResult.failure(
          'Server error ${streamed.statusCode}: $body',
        );
      }

      onProgress?.call(0.85, 'Downloading film results…');

      final zipBytes = await streamed.stream.toBytes();
      final outputDir = await _extractZipBytes(zipBytes);

      onProgress?.call(1.0, 'Done!');
      return ProcessingResult.success(outputDir);
    } on TimeoutException {
      return ProcessingResult.failure(
        'Request timed out. The pipeline may still be running on the PC.',
      );
    } catch (e) {
      return ProcessingResult.failure('Network error: $e');
    }
  }

  // ── Local path (desktop / offline) ───────────────────────────────────────

  Future<ProcessingResult> _processLocally({
    required String imagePath,
    required Map<String, dynamic> settings,
    String? maskPath,
    String imageClassHint = 'auto',
    double aiConfidence = 0.0,
    void Function(double, String)? onProgress,
  }) async {
    // On mobile there is no Python interpreter — show a friendly message.
    if (Platform.isAndroid || Platform.isIOS) {
      return ProcessingResult.failure(
        'PC server not found.\n'
        'Make sure your PC is running Virtual Designer Server\n'
        'and both devices are on the same WiFi network.',
      );
    }

    // ── Desktop: run the existing PythonProcessor (Process.start) ──────────
    onProgress?.call(0.1, 'Starting local pipeline…');

    // Map the API-style settings to python/main.py flags.
    // Server: uses snake_case keys and cm units
    // Python: uses kebab-case keys and mm units
    final pythonSettings = <String, dynamic>{
      if (settings.containsKey('colors')) 'colors': settings['colors'],
      if (settings.containsKey('dpi')) 'dpi': settings['dpi'],
      if (settings.containsKey('halftone')) 'halftone': settings['halftone'],
      if (settings.containsKey('lpi')) 'lpi': settings['lpi'],
      if (settings.containsKey('dot_shape')) 'dot-shape': settings['dot_shape'],
      if (settings.containsKey('dot_size')) 'dot-size': settings['dot_size'],
      if (settings.containsKey('mesh_count'))
        'mesh-count': settings['mesh_count'],
      if (settings.containsKey('detail_level'))
        'detail-level': settings['detail_level'],
      if (settings.containsKey('target_width_mm'))
        'target-width-mm': settings['target_width_mm'],
      if (settings.containsKey('source_dpi'))
        'source-dpi': settings['source_dpi'],
      if (settings.containsKey('scale_mode'))
        'scale-mode': settings['scale_mode'],
      if (settings.containsKey('custom_scale_percent'))
        'custom-scale-percent': settings['custom_scale_percent'],
      if (settings.containsKey('paper_width'))
        'page-width': (settings['paper_width'] is num)
            ? (settings['paper_width'] as num).toDouble() * 10.0
            : double.tryParse(settings['paper_width'].toString()) == null
                ? null
                : double.parse(settings['paper_width'].toString()) * 10.0,
      if (settings.containsKey('paper_height'))
        'page-height': (settings['paper_height'] is num)
            ? (settings['paper_height'] as num).toDouble() * 10.0
            : double.tryParse(settings['paper_height'].toString()) == null
                ? null
                : double.parse(settings['paper_height'].toString()) * 10.0,
      'page-size': 'CUSTOM',
      // Mobile hints
      'image-class-hint': imageClassHint,
      'ai-confidence': aiConfidence,
      // If Flutter already decided with high confidence, skip expensive AI.
      if (aiConfidence >= 0.90 && imageClassHint != 'auto') 'no-ai': true,
      if (maskPath != null && maskPath.isNotEmpty) 'pre-mask': maskPath,
      // Smoothing & corner parameters (sentinel -1.0 = adaptive from AI/decision engine)
      if (settings.containsKey('smoothing_factor'))
        'smoothing-factor': settings['smoothing_factor'],
      if (settings.containsKey('corner_threshold'))
        'corner-threshold': settings['corner_threshold'],
    };
    pythonSettings.removeWhere((k, v) => v == null);

    try {
      final processor = Get.find<PythonProcessor>();
      final result = await processor.processImage(
        imagePath: imagePath,
        settings: pythonSettings,
        onProgress: onProgress,
      );

      if (result.success && result.outputPath.isNotEmpty) {
        return ProcessingResult.success(result.outputPath);
      }
      return ProcessingResult.failure(
        result.errorMessage ?? 'Local pipeline failed',
      );
    } catch (e) {
      return ProcessingResult.failure('Local processing unavailable: $e');
    }
  }

  // ── ZIP extraction ────────────────────────────────────────────────────────

  Future<String> _extractZipBytes(List<int> zipBytes) async {
    final tempDir = await getTemporaryDirectory();
    final outputDir =
        '${tempDir.path}/vd_output_${DateTime.now().millisecondsSinceEpoch}';
    await Directory(outputDir).create(recursive: true);

    final archive = ZipDecoder().decodeBytes(zipBytes);
    for (final entry in archive) {
      if (entry.isFile) {
        final outFile = File('$outputDir/${entry.name}');
        await outFile.parent.create(recursive: true);
        await outFile.writeAsBytes(entry.content as List<int>);
      }
    }

    return outputDir;
  }
}
