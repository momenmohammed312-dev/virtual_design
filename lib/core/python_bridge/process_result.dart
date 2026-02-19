// process_result.dart — Result object from Python processing
// Virtual Design Silk Screen Studio

class ProcessResult {
  final bool success;
  final String? outputDirectory;
  final String? errorMessage;

  const ProcessResult._({
    required this.success,
    this.outputDirectory,
    this.errorMessage,
  });

  /// نجاح مع مسار الـ output
  factory ProcessResult.success({required String outputDirectory}) {
    return ProcessResult._(
      success: true,
      outputDirectory: outputDirectory,
    );
  }

  /// فشل مع رسالة خطأ
  factory ProcessResult.failure(String message) {
    return ProcessResult._(
      success: false,
      errorMessage: message,
    );
  }

  /// هل الـ output directory موجود ويمكن قراءته؟
  bool get hasValidOutput {
    if (outputDirectory == null || outputDirectory!.isEmpty) return false;
    // يمكن إضافة Directory.existsSync() لو أردت
    return true;
  }

  @override
  String toString() => success
      ? 'ProcessResult(success, output=$outputDirectory)'
      : 'ProcessResult(failed, error=$errorMessage)';
}
