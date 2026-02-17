class ProcessResult {
  final bool success;
  final String stdout;
  final String stderr;
  final String? outputDirectory;
  final String? errorMessage;

  ProcessResult({
    required this.success,
    this.stdout = '',
    this.stderr = '',
    this.outputDirectory,
    this.errorMessage,
  });
}
