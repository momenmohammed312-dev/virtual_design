import 'dart:convert';
import 'dart:io';

import 'python_config.dart';
import 'process_result.dart';
import '../../domain/entities/processing_settings.dart';
import '../../core/enums/app_enums.dart';

class PythonProcessor {
  final PythonConfig config;

  PythonProcessor({this.config = const PythonConfig()});

  Future<ProcessResult> runScript(
    List<String> args, {
    String? workingDirectory,
  }) async {
    try {
      final result = await Process.run(
        config.pythonCommand,
        args,
        workingDirectory: workingDirectory,
        runInShell: true,
      );

      final out = result.stdout is String
          ? result.stdout as String
          : const Utf8Decoder().convert(result.stdout as List<int>);

      final err = result.stderr is String
          ? result.stderr as String
          : const Utf8Decoder().convert(result.stderr as List<int>);

      return ProcessResult(
        success: result.exitCode == 0,
        stdout: out,
        stderr: err,
      );
    } catch (e) {
      return ProcessResult(success: false, stderr: e.toString());
    }
  }

  Future<ProcessResult> processImage({
    required String imagePath,
    required ProcessingSettings settings,
    void Function(double, String)? onProgress,
  }) async {
    // Construct output path
    final outputPath = '${imagePath}_processed.png';

    // Map settings to script arguments
    final args = [
      'python/core/registration_marks.py',
      '--input',
      imagePath,
      '--output',
      outputPath,
      '--color-name',
      'Color',
      '--color-index',
      '1',
      '--total-colors',
      settings.colorCount.toString(),
      '--color-rgb',
      '0',
      '0',
      '0',
      '--mark-type',
      'full',
      '--dpi',
      settings.dpi.toString(),
      '--border',
      '120',
    ];

    if (settings.printType == PrintType.screenPrinting &&
        settings.colorCount > 1) {
      // For multi-color, could call multiple times, but for now, assume single
    }

    // Run the script
    final result = await runScript(
      args,
      workingDirectory: Directory.current.parent.parent.path,
    );

    if (result.success && onProgress != null) {
      onProgress(1.0, 'Processing completed');
    }

    return result;
  }
}
