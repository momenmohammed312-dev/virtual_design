// lib/core/python_bridge/python_processor.dart
// Senior-grade Python Bridge with full error handling and progress reporting.

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

import 'python_config.dart';
import 'process_result.dart';

class PythonProcessor {
  final PythonConfig config;
  final List<Process> _activeProcesses = [];

  PythonProcessor({required this.config});

  Future<ProcessResult> processImage({
    required String imagePath,
    required Map<String, dynamic> settings,
    String? outputDir,
    void Function(double progress, String message)? onProgress,
    Duration timeout = const Duration(minutes: 30),
  }) async {
    // Guard: refuse processing if Python is unavailable or not initialized
    if (!config.isInitialized) {
      return ProcessResult.failure(
          errorMessage:
              'BRIDGE_NOT_INITIALIZED: The Python bridge has not been initialized. '
              'Please call initialize() before processing.');
    }
    if (!config.isPythonAvailable) {
      return ProcessResult.failure(
        errorMessage: 'PYTHON_NOT_FOUND: Python is not available. '
            'Please install Python 3.8+ from python.org and add it to PATH.',
      );
    }

    // Verify image exists
    if (!File(imagePath).existsSync()) {
      return ProcessResult.failure(
          errorMessage: 'Image file not found: $imagePath');
    }

    // Auto-create output directory if not specified
    final finalOutputDir = outputDir ?? await _generateOutputDir();
    await Directory(finalOutputDir).create(recursive: true);

    // Get scripts directory from config
    final scriptsDir = await config.getPythonScriptsDir();

    // Verify scripts directory exists
    if (!await Directory(scriptsDir).exists()) {
      return ProcessResult.failure(
        errorMessage:
            'SCRIPTS_DIR_NOT_FOUND: Python scripts directory not found: $scriptsDir\n'
            'Please verify the installation.',
      );
    }

    final mainScript = p.join(scriptsDir, 'main.py');

    // Build arguments
    final args = _buildArgs(
      imagePath: imagePath,
      outputDir: finalOutputDir,
      settings: settings,
    );

    // Launch Python process
    Process process;
    try {
      final pythonCmd = await config.resolvePythonCommand();
      process = await Process.start(
        pythonCmd,
        [mainScript, ...args],
        workingDirectory: scriptsDir,
        environment: {
          'PYTHONPATH': scriptsDir,
        },
      );
      _activeProcesses.add(process);
    } on ProcessException catch (e) {
      return ProcessResult.failure(
        errorMessage: 'Failed to start Python process: ${e.message}',
      );
    } catch (e) {
      return ProcessResult.failure(errorMessage: 'Cannot launch Python: $e');
    }

    // Read stdout line by line - real-time progress
    final stdoutBuffer = StringBuffer();
    final stderrBuffer = StringBuffer();
    final stdoutCompleter = Completer<void>();
    final stderrCompleter = Completer<void>();

    process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
      (line) {
        stdoutBuffer.writeln(line);
        _parseProgress(line, onProgress);
        // LOG: Show all Python stdout in Flutter logs
        Get.log('[Python] $line');
        debugPrint('[Python] $line');
      },
      onDone: stdoutCompleter.complete,
      onError: (_) => stdoutCompleter.complete(),
    );

    process.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
      (line) {
        stderrBuffer.writeln(line);
        // LOG: Show Python stderr in Flutter logs for debugging
        Get.log('[Python:stderr] $line');
        debugPrint('[Python:stderr] $line');
      },
      onDone: stderrCompleter.complete,
      onError: (_) => stderrCompleter.complete(),
    );

    // Wait for process with timeout
    int exitCode;
    try {
      exitCode = await process.exitCode.timeout(timeout);
    } on TimeoutException catch (e) {
      process.kill();
      await Future.wait([stdoutCompleter.future, stderrCompleter.future]);
      return ProcessResult.failure(errorMessage: 'Process timeout: $e');
    }
    await Future.wait([stdoutCompleter.future, stderrCompleter.future]);

    if (exitCode == -99) {
      return ProcessResult.failure(
        errorMessage:
            'TIMEOUT:Processing took too long (>${timeout.inMinutes} min).',
      );
    }

    _activeProcesses.remove(process);

    // Success: parse output and return
    if (exitCode == 0) {
      final outputDirectory =
          _parseOutputDirectory(stdoutBuffer.toString()) ?? finalOutputDir;
      final resolvedDir =
          outputDirectory.isNotEmpty ? outputDirectory : finalOutputDir;
      if (onProgress != null) onProgress(1.0, 'Processing complete!');
      return ProcessResult.success(outputPath: resolvedDir);
    }

    // Process failed - parse and return the actual error
    final fullStderr = stderrBuffer.toString();
    final errorMessage = _parseError(exitCode, fullStderr);

    // Log full stderr for debugging
    print('❌ PYTHON PROCESS FAILED (exit code $exitCode)');
    print('Full stderr:\n$fullStderr');
    Get.log('❌ PYTHON PROCESS FAILED (exit code $exitCode)');
    Get.log('Full stderr:\n$fullStderr');

    return ProcessResult.failure(errorMessage: errorMessage);
  }

  /// Build arguments for main.py
  List<String> _buildArgs({
    required String imagePath,
    required String outputDir,
    required Map<String, dynamic> settings,
  }) {
    final args = <String>[
      '--input',
      imagePath,
      '--output',
      outputDir,
    ];

    // Add settings
    settings.forEach((key, value) {
      if (value != null) {
        final argName = '--${key.replaceAllMapped(
          RegExp(r'[A-Z]'),
          (match) => '-${match.group(0)!.toLowerCase()}',
        )}';
        args.add(argName);
        if (value is! bool) {
          // Convert values to string, but handle doubles that are whole numbers
          // to pass them as integers to Python (e.g., 4800.0 -> "4800")
          String strValue;
          if (value is double) {
            if (value == value.roundToDouble()) {
              // It's a whole number, pass as int
              strValue = value.toInt().toString();
            } else {
              strValue = value.toString();
            }
          } else {
            strValue = value.toString();
          }
          args.add(strValue);
        }
      }
    });

    return args;
  }

  /// Parse progress updates from Python stdout
  void _parseProgress(String line, void Function(double, String)? onProgress) {
    if (onProgress == null) return;

    // Look for progress indicators like: "PROGRESS:0.5:Processing step 3/6"
    final progressRegex = RegExp(r'PROGRESS:(\d+\.?\d*):(.*)');
    final match = progressRegex.firstMatch(line);
    if (match != null) {
      final progress = double.tryParse(match.group(1)!) ?? 0.0;
      final message = match.group(2) ?? 'Processing...';
      onProgress(progress.clamp(0.0, 1.0), message);
    }
  }

  /// Parse output directory from Python stdout
  String? _parseOutputDirectory(String stdout) {
    // Look for output directory indicator like: "OUTPUT_DIR:/path/to/output"
    final regex = RegExp(r'OUTPUT_DIR:(.+)');
    final match = regex.firstMatch(stdout);
    return match?.group(1)?.trim();
  }

  /// Parse error message from exit code and stderr
  String _parseError(int exitCode, String stderr) {
    if (stderr.isNotEmpty) {
      // Extract the most relevant error line
      final lines =
          stderr.split('\n').where((l) => l.trim().isNotEmpty).toList();
      if (lines.isNotEmpty) {
        // Find Traceback index
        int tracebackIndex = -1;
        for (int i = 0; i < lines.length; i++) {
          if (lines[i].contains('Traceback')) {
            tracebackIndex = i;
            break;
          }
        }

        // If we found Traceback, capture all lines from there to the end
        if (tracebackIndex >= 0) {
          final tracebackLines = lines.skip(tracebackIndex).take(15).toList();
          return tracebackLines.join('\n');
        }

        // Prefer lines with "Error:" or "Exception:"
        final errorLines = lines
            .where((l) => l.contains('Error:') || l.contains('Exception:'))
            .toList();
        if (errorLines.isNotEmpty) {
          return errorLines.first.trim();
        }
        return lines.last.trim();
      }
    }
    return 'Processing failed with exit code $exitCode';
  }

  /// Generate a unique output directory
  Future<String> _generateOutputDir() async {
    final tempDir = await getTemporaryDirectory();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final random = math.Random().nextInt(10000);
    return p.join(tempDir.path, 'virtual_design_output_${timestamp}_$random');
  }

  /// Cancel all active processes
  void cancelAll() {
    for (final process in _activeProcesses) {
      process.kill();
    }
    _activeProcesses.clear();
  }

  /// Run AI Auto-Fix with prompt for user-guided adjustments
  Future<Map<String, dynamic>?> runAutoFixWithPrompt({
    required String originalImage,
    required String previewImage,
    required String prompt,
    int iteration = 1,
    Map<String, dynamic>? prevParams,
  }) async {
    // Extract only actual parameters from prevParams (not the full result object)
    Map<String, dynamic>? cleanPrevParams;
    if (prevParams != null) {
      // If prevParams contains 'adjusted_params', extract only those values
      if (prevParams.containsKey('adjusted_params') &&
          prevParams['adjusted_params'] is Map) {
        final adjusted = prevParams['adjusted_params'] as Map<String, dynamic>;
        cleanPrevParams = {
          'smoothing_factor': adjusted['smoothing_factor'],
          'corner_threshold': adjusted['corner_threshold'],
          'simplification_epsilon': adjusted['simplification_epsilon'],
          'use_halftone': adjusted['use_halftone'],
          'lpi': adjusted['lpi'],
        }..removeWhere((key, value) => value == null);
      } else {
        // Already clean params
        cleanPrevParams = prevParams;
      }
    }

    final scriptsDir = await config.getPythonScriptsDir();
    final autoFixScript = p.join(scriptsDir, 'auto_fix.py');

    // Build arguments
    final args = <String>[
      '--original',
      originalImage,
      '--preview',
      previewImage,
      '--prompt',
      prompt,
      '--iteration',
      iteration.toString(),
    ];

    if (cleanPrevParams != null && cleanPrevParams.isNotEmpty) {
      args.addAll(['--prev-params', jsonEncode(cleanPrevParams)]);
    }

    try {
      final pythonCmd = await config.resolvePythonCommand();
      final process = await Process.start(
        pythonCmd,
        [autoFixScript, ...args],
        workingDirectory: scriptsDir,
        environment: {'PYTHONPATH': scriptsDir},
      );

      final stdoutBuffer = StringBuffer();
      final stderrBuffer = StringBuffer();

      await process.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) => stdoutBuffer.writeln(line))
          .asFuture();

      await process.stderr
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) => stderrBuffer.writeln(line))
          .asFuture();

      final exitCode = await process.exitCode;

      if (exitCode == 0) {
        final output = stdoutBuffer.toString().trim();
        // Find the last JSON line
        final lines =
            output.split('\n').where((l) => l.trim().isNotEmpty).toList();
        for (final line in lines.reversed) {
          try {
            final result = jsonDecode(line.trim()) as Map<String, dynamic>;
            return result;
          } catch (_) {
            continue;
          }
        }
      }

      return null;
    } catch (e) {
      return null;
    }
  }

  /// Run standard AI Auto-Fix without prompt
  Future<Map<String, dynamic>?> runAutoFix({
    required String originalImage,
    required String previewImage,
    int iteration = 1,
    Map<String, dynamic>? prevParams,
  }) async {
    return runAutoFixWithPrompt(
      originalImage: originalImage,
      previewImage: previewImage,
      prompt: '',
      iteration: iteration,
      prevParams: prevParams,
    );
  }
}
