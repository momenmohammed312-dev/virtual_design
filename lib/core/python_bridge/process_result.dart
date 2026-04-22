// lib/core/python_bridge/process_result.dart

import 'dart:io';

/// Result of a Python image processing operation
class ProcessResult {
  final bool success;
  final String outputPath;
  final String? errorMessage;
  final List<String> generatedFiles;
  final Map<String, dynamic>? metadata;

  ProcessResult({
    required this.success,
    required this.outputPath,
    this.errorMessage,
    this.generatedFiles = const [],
    this.metadata,
  });

  factory ProcessResult.success({
    required String outputPath,
    List<String>? generatedFiles,
    Map<String, dynamic>? metadata,
  }) {
    return ProcessResult(
      success: true,
      outputPath: outputPath,
      generatedFiles: generatedFiles ?? [],
      metadata: metadata,
    );
  }

  factory ProcessResult.failure({
    required String errorMessage,
    String outputPath = '',
  }) {
    return ProcessResult(
      success: false,
      outputPath: outputPath,
      errorMessage: errorMessage,
    );
  }

  /// Check if the output directory exists and contains files
  bool get hasValidOutput {
    if (!success || outputPath.isEmpty) return false;
    final dir = Directory(outputPath);
    if (!dir.existsSync()) return false;

    final files = dir.listSync().whereType<File>().toList();
    return files.isNotEmpty;
  }

  get outputDirectory => outputPath;

  /// Get list of film files (PNG/PDF) from the output directory
  List<File> getFilmFiles() {
    if (!hasValidOutput) return [];

    final dir = Directory(outputPath);
    return dir
        .listSync()
        .whereType<File>()
        .where((f) =>
            f.path.toLowerCase().endsWith('.png') ||
            f.path.toLowerCase().endsWith('.pdf'))
        .toList();
  }

  @override
  String toString() {
    return 'ProcessResult(success: $success, outputPath: $outputPath, files: ${generatedFiles.length})';
  }
}

/// Result of Python initialization
class PythonInitResult {
  final bool success;
  final String? errorMessage;
  final String? pythonVersion;
  final String? venvPath;

  PythonInitResult({
    required this.success,
    this.errorMessage,
    this.pythonVersion,
    this.venvPath,
  });

  factory PythonInitResult.success({
    String? pythonVersion,
    String? venvPath,
  }) {
    return PythonInitResult(
      success: true,
      pythonVersion: pythonVersion,
      venvPath: venvPath,
    );
  }

  factory PythonInitResult.failure(String errorMessage) {
    return PythonInitResult(
      success: false,
      errorMessage: errorMessage,
    );
  }
}
