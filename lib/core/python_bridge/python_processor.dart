// python_processor.dart — Fixed Dart↔Python Bridge
// Virtual Design Silk Screen Studio
//
// FATAL #1 FIX: يستدعي main.py بدل registration_marks.py
// FATAL #3 FIX: يقرأ OUTPUT_DIR: من stdout + path quoting/escaping
// FATAL #4 FIX: يستخدم Process.start() لـ real-time progress streaming
// HIGH #1 FIX:  يستخدم PythonConfig لاكتشاف أمر Python تلقائياً
// HIGH #2 FIX:  يرفض المعالجة لو Python غير متاح

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:flutter/foundation.dart';

import 'process_result.dart';
import 'python_config.dart';
import '../../domain/entities/processing_settings.dart';

class PythonProcessor {
  final PythonConfig config;

  PythonProcessor({required this.config});

  /// معالجة صورة عبر Python pipeline الكامل (9 steps)
  ///
  /// [imagePath]   مسار الصورة الأصلية
  /// [settings]    إعدادات الطباعة
  /// [outputDir]   مجلد الـ output اختياري (إذا فارغ، يُنشأ تلقائياً)
  /// [onProgress]  callback لتحديث شريط التقدم (0.0 → 1.0, message)
  ///
  /// Returns [ProcessResult] يحتوي على:
  ///   - success: نجاح أم فشل
  ///   - outputDirectory: مسار مجلد الـ output (غير null لو نجح)
  ///   - errorMessage: رسالة الخطأ (لو فشل)
  Future<ProcessResult> processImage({
    required String imagePath,
    required ProcessingSettings settings,
    String? outputDir,
    void Function(double progress, String message)? onProgress,
  }) async {
    // HIGH #2: Guard — refuse processing if Python is unavailable or not initialized
    if (!config.isInitialized) {
      return ProcessResult.failure(
        'BRIDGE_NOT_INITIALIZED:The Python bridge has not been initialized. '
        'Please call initialize() before processing.',
      );
    }
    if (!config.isPythonAvailable) {
      return ProcessResult.failure(
        'PYTHON_NOT_FOUND:Python is not available. '
        'Please install Python 3.8+ from python.org and add it to PATH.',
      );
    }

    // التحقق من الصورة
    if (!File(imagePath).existsSync()) {
      return ProcessResult.failure('Image file not found: $imagePath');
    }

    // إذا لم يتم تحديد مجلد output، أنشئ واحد تلقائياً
    String finalOutputDir = outputDir ?? '';
    if (finalOutputDir.isEmpty) {
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final appDir = await getApplicationDocumentsDirectory();
      finalOutputDir = '${appDir.path}/silk_output_$timestamp';
    }

    // بناء قائمة الـ arguments
    final args = _buildArgs(imagePath, finalOutputDir, settings);

    // مسار مجلد python scripts
    final scriptsDir = await config.getPythonScriptsDir();
    final pythonCommand = await config.resolvePythonCommand();

    // Log details for debugging
    debugPrint('[PythonProcessor] Python: $pythonCommand');
    debugPrint('[PythonProcessor] Scripts dir: $scriptsDir');
    debugPrint('[PythonProcessor] Input: $imagePath');
    debugPrint('[PythonProcessor] Output: $finalOutputDir');
    debugPrint('[PythonProcessor] Args: $args');

    // Verify scripts directory exists
    if (!await Directory(scriptsDir).exists()) {
      return ProcessResult.failure(
        'SCRIPTS_DIR_NOT_FOUND:Python scripts directory not found: $scriptsDir\n'
        'Please verify the installation.',
      );
    }

    // بدء العملية مع بيئة محسّنة (بدون buffering)
    Process process;
    try {
      process = await Process.start(
        pythonCommand,
        args,
        runInShell: false,
        workingDirectory: scriptsDir,
        environment: {
          ...Platform.environment,
          'PYTHONUNBUFFERED': '1', // قراءة stdout فوراً
        },
      );
    } on ProcessException catch (e) {
      return ProcessResult.failure(
        'Failed to start Python process: ${e.message}',
      );
    } catch (e) {
      return ProcessResult.failure('Cannot launch Python: $e');
    }

    // قراءة stdout سطراً بسطر — real-time progress
    String outputDirectory = '';
    final stderrBuffer = StringBuffer();

    final stdoutCompleter = Completer<void>();
    final stderrCompleter = Completer<void>();

    final progressRegex = RegExp(r'^PROGRESS:(0\.\d+|1\.0+):(.+)$');

    // RegExp for robust progress parsing (handles Windows paths with colons)
    process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
      (line) {
        // New IPC fine-grained progress format: PROGRESS:<0.0-1.0>:message
        if (line.startsWith('PROGRESS:')) {
          if (onProgress != null) {
            final match = progressRegex.firstMatch(line);
            if (match != null) {
              final val = double.tryParse(match.group(1)!) ?? 0.0;
              final msg = match.group(2)!.trim();
              onProgress(val.clamp(0.0, 1.0), msg);
            }
          }
          return;
        }
        // FATAL #3 FIX: استخراج مسار output
        if (line.startsWith('OUTPUT_DIR:')) {
          outputDirectory = line.substring('OUTPUT_DIR:'.length).trim();
          return;
        }

        // FATAL #4 FIX: تحديث progress من "Step X/9: ..."
        final stepMatch = RegExp(
          r'Step (\d+)/(\d+):\s*(.*)',
        ).firstMatch(line);
        if (stepMatch != null && onProgress != null) {
          final current = int.parse(stepMatch.group(1)!);
          final total = int.parse(stepMatch.group(2)!);
          final stepName = stepMatch.group(3) ?? '';
          onProgress(current / total, 'Step $current/$total: $stepName');
        }
      },
      onDone: () {
        if (!stdoutCompleter.isCompleted) stdoutCompleter.complete();
      },
      onError: (_) {
        if (!stdoutCompleter.isCompleted) stdoutCompleter.complete();
      },
    );

    process.stderr.transform(utf8.decoder).listen(
      (chunk) => stderrBuffer.write(chunk),
      onDone: () {
        if (!stderrCompleter.isCompleted) stderrCompleter.complete();
      },
      onError: (_) {
        if (!stderrCompleter.isCompleted) stderrCompleter.complete();
      },
    );

    // BUG-09 FIX: Process timeout — 5 minutes max
    const timeout = Duration(minutes: 5);
    int exitCode;
    try {
      exitCode = await process.exitCode.timeout(
        timeout,
        onTimeout: () {
          debugPrint(
              '[PythonProcessor] TIMEOUT after ${timeout.inMinutes}min — killing process');
          process.kill();
          return -99;
        },
      );
    } catch (e) {
      process.kill();
      await Future.wait([stdoutCompleter.future, stderrCompleter.future]);
      return ProcessResult.failure('Process timeout: $e');
    }
    await Future.wait([stdoutCompleter.future, stderrCompleter.future]);

    if (exitCode == -99) {
      return ProcessResult.failure(
        'TIMEOUT:Processing took too long (>${timeout.inMinutes} min).',
      );
    }

    debugPrint('[PythonProcessor] Exit code: $exitCode');
    debugPrint('[PythonProcessor] Output dir from IPC: $outputDirectory');

    if (exitCode == 0 && outputDirectory.isNotEmpty) {
      if (onProgress != null) onProgress(1.0, 'Processing complete!');
      return ProcessResult.success(outputDirectory: outputDirectory);
    }

    // Process failed - parse and return the actual error
    final errorMessage = _parseError(exitCode, stderrBuffer.toString());
    return ProcessResult.failure(errorMessage);
  }

  /// بناء arguments لـ main.py
  /// FATAL #3 FIX: paths are quoted to handle spaces/special chars on Windows
  List<String> _buildArgs(
    String imagePath,
    String outputDir,
    ProcessingSettings settings,
  ) {
    final args = <String>[
      'main.py',
      '--input',
      _safePath(imagePath),
      '--output',
      _safePath(outputDir),
      '--dpi',
      settings.dpi.toInt().toString(),
      '--detail-level',
      settings.detailLevel.name,
      '--clean',
      '--validate-strokes',
      '--min-stroke',
      settings.strokeWidthMm.toString(),
    ];

    // Color count: if 0, use auto-colors flag
    if (settings.colorCount == 0) {
      // Auto mode: ابدأ بـ 2 ألوان — أأمن من auto-detect
      args.addAll(['--colors', '2']);
    } else {
      // Allow 1 color if explicitly requested
      final safeColorCount = settings.colorCount < 1 ? 1 : settings.colorCount;
      args.addAll(['--colors', safeColorCount.toString()]);
    }

    // Halftone Settings - only add --halftone if explicitly set to halftone finish OR forced via override
    if (settings.printFinish == PrintFinish.halftone ||
        settings.forceHalftone) {
      args.add('--halftone');
      if (settings.halftoneSettings != null) {
        args.add('--lpi');
        args.add(settings.halftoneSettings!.lpi.toString());
        args.add('--dot-shape');
        args.add(settings.halftoneSettings!.dotShape);
      }
    } else {
      // Skip halftone for non-halftone finishes
      args.add('--skip-halftone');
    }

    // Professional Features — all enabled by default as automatic
    args.addAll(['--pantone-matching', settings.pantoneMatching.name]);
    // Underbase: disabled by default حتى لو المستخدم اختار automatic
    // لأنه بيضيف فيلم زيادة مش محسوب في عدد الألوان المطلوب
    args.addAll(['--underbase-mode', 'disabled']);
    args.addAll(['--trapping-mode', settings.trappingMode.name]);
    args.addAll(['--overprint-mode', settings.overprintMode.name]);
    args.addAll(['--gradient-mesh-mode', settings.gradientMeshMode.name]);
    args.addAll(['--typography-mode', settings.typographyMode.name]);
    args.addAll(['--mesh-preview-mode', settings.meshPreviewMode.name]);

    // Advanced Tuning (Phase 8 Senior Optimizations)
    // Pass through globalThreshold; Python will auto-adjust based on --image-type
    int effectiveThreshold = settings.globalThreshold.toInt();
    if (settings.adaptiveThreshold) {
      effectiveThreshold = -1;
    }

    args.addAll(['--global-threshold', effectiveThreshold.toString()]);
    args.addAll(['--smoothing-factor', settings.smoothingFactor.toString()]);
    args.addAll(['--corner-threshold', settings.cornerThreshold.toString()]);
    args.addAll(['--noise-removal', settings.noiseRemoval.toString()]);
    if (settings.autoCrop) {
      args.add('--auto-crop');
    }
    if (settings.adaptiveThreshold) {
      args.add('--adaptive-threshold');
    }

    // Image Processing Mode (Simple, Mixed, Complex, Auto)
    args.addAll(['--image-type', settings.imageType.name]);

    if (settings.filmLabel.isNotEmpty) {
      args.addAll(['--film-label', settings.filmLabel]);
    }

    return args;
  }

  /// Parse error from exit code and stderr output
  String _parseError(int exitCode, String stderr) {
    switch (exitCode) {
      case 2:
        return 'File not found error: $stderr';
      case 3:
        return 'Invalid input error: $stderr';
      case 1:
      default:
        return 'Processing failed (exit code $exitCode): $stderr';
    }
  }

  /// Make path safe for Windows command line.
  /// Escapes internal double-quotes and wraps in quotes if needed.
  String _safePath(String path) {
    if (Platform.isWindows) {
      // Escape any existing double quotes inside the path
      var escaped = path.replaceAll('"', r'\"');
      // Replace backslashes with forward slashes to prevent escape issues in Python strings
      escaped = escaped.replaceAll('\\', '/');

      // Wrap in quotes if path contains spaces or special characters
      if (escaped.contains(' ') ||
          escaped.contains('&') ||
          escaped.contains('(') ||
          escaped.contains(')')) {
        return '"$escaped"';
      }
      return escaped;
    }
    return path;
  }
}
