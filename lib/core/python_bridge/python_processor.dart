/// python_processor.dart — Fixed Dart↔Python Bridge
/// Virtual Design Silk Screen Studio
///
/// FATAL #1 FIX: يستدعي main.py بدل registration_marks.py
/// FATAL #3 FIX: يقرأ OUTPUT_DIR: من stdout
/// FATAL #4 FIX: يستخدم Process.start() لـ real-time progress streaming
/// HIGH #1 FIX:  يستخدم PythonConfig لاكتشاف أمر Python تلقائياً

import 'dart:async';
import 'dart:convert';
import 'dart:io';

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
  /// [onProgress]  callback لتحديث شريط التقدم (0.0 → 1.0, message)
  ///
  /// Returns [ProcessResult] يحتوي على:
  ///   - success: نجاح أم فشل
  ///   - outputDirectory: مسار مجلد الـ output (غير null لو نجح)
  ///   - errorMessage: رسالة الخطأ (لو فشل)
  Future<ProcessResult> processImage({
    required String imagePath,
    required ProcessingSettings settings,
    void Function(double progress, String message)? onProgress,
  }) async {
    // التحقق من الصورة
    if (!File(imagePath).existsSync()) {
      return ProcessResult.failure('Image file not found: $imagePath');
    }

    // مجلد الـ output
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final outputDir =
        '${File(imagePath).parent.path}/silk_output_$timestamp';

    // بناء قائمة الـ arguments
    final args = _buildArgs(imagePath, outputDir, settings);

    // مسار مجلد python scripts
    final scriptsDir = await config.getPythonScriptsDir();
    final pythonCommand = await config.resolvePythonCommand();

    // بدء العملية
    Process process;
    try {
      process = await Process.start(
        pythonCommand,
        args,
        runInShell: true,
        workingDirectory: scriptsDir,
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

    process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
          (line) {
            // FATAL #3 FIX: استخراج مسار output
            if (line.startsWith('OUTPUT_DIR:')) {
              outputDirectory = line.substring('OUTPUT_DIR:'.length).trim();
              return;
            }

            // FATAL #4 FIX: تحديث progress من "Step X/9: ..."
            final stepMatch =
                RegExp(r'Step (\d+)/(\d+):\s*(.*)').firstMatch(line);
            if (stepMatch != null && onProgress != null) {
              final current = int.parse(stepMatch.group(1)!);
              final total = int.parse(stepMatch.group(2)!);
              final stepName = stepMatch.group(3) ?? '';
              onProgress(current / total, 'Step $current/$total: $stepName');
            }
          },
          onDone: () => stdoutCompleter.complete(),
          onError: (_) => stdoutCompleter.complete(),
        );

    process.stderr
        .transform(utf8.decoder)
        .listen(
          (chunk) => stderrBuffer.write(chunk),
          onDone: () => stderrCompleter.complete(),
          onError: (_) => stderrCompleter.complete(),
        );

    // انتظار انتهاء العملية
    final exitCode = await process.exitCode;
    await Future.wait([stdoutCompleter.future, stderrCompleter.future]);

    if (exitCode == 0 && outputDirectory.isNotEmpty) {
      if (onProgress != null) onProgress(1.0, 'Processing complete!');
      return ProcessResult.success(outputDirectory: outputDirectory);
    }

    // تحديد نوع الخطأ من exit code
    final errorMessage = _parseError(exitCode, stderrBuffer.toString());
    return ProcessResult.failure(errorMessage);
  }

  /// بناء arguments لـ main.py
  List<String> _buildArgs(
    String imagePath,
    String outputDir,
    ProcessingSettings settings,
  ) {
    final args = <String>[
      'main.py',
      '--input', imagePath,
      '--output', outputDir,
      '--colors', settings.colorCount.toString(),
      '--dpi', settings.dpi.toInt().toString(),
      '--detail-level', settings.detailLevel.name,
      '--clean',
      '--validate-strokes',
      '--min-stroke', settings.strokeWidthMm.toString(),
    ];

    // Halftone mode
    if (settings.printFinish == PrintFinish.halftone) {
      args.add('--halftone');
      final lpi = settings.halftoneSettings?.lpi ?? 65;
      args.addAll(['--lpi', lpi.toString()]);
    }

    // Edge enhancement
    if (settings.edgeEnhancement != EdgeEnhancement.none) {
      args.addAll(['--edge-enhance', settings.edgeEnhancement.name]);
    }

    return args;
  }

  /// تحويل exit code لرسالة خطأ مفهومة
  String _parseError(int exitCode, String stderr) {
    switch (exitCode) {
      case 2:
        return 'Image file not found. Please re-select the image.';
      case 3:
        return 'Invalid image format. Use PNG, JPG, or TIFF.';
      case 1:
        // البحث في stderr عن تفاصيل
        if (stderr.contains('ModuleNotFoundError') ||
            stderr.contains('ImportError')) {
          final missing = _extractMissingModule(stderr);
          return 'Missing Python package: $missing\n'
              'Run: pip install -r requirements.txt';
        }
        if (stderr.contains('MemoryError')) {
          return 'Image is too large. Try reducing resolution or file size.';
        }
        if (stderr.contains('cv2.error')) {
          return 'Image processing error. Check image format.';
        }
        return 'Processing failed (exit code $exitCode).\n$stderr';
      default:
        return 'Unknown error (exit code $exitCode).';
    }
  }

  String _extractMissingModule(String stderr) {
    final match = RegExp(r"No module named '([^']+)'").firstMatch(stderr);
    return match?.group(1) ?? 'unknown module';
  }
}
