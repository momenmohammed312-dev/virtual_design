// lib/core/errors/error_codes.dart
// Error codes only - ProcessingError and ProcessingErrorType are defined in error_screen_widget.dart

/// Error codes for the application
enum ErrorCode {
  // Python Bridge Errors (1000-1099)
  pythonNotFound(
      'E1000', 'Python not found', 'Please install Python 3.8 or higher'),
  pythonInitFailed('E1001', 'Python initialization failed',
      'Failed to initialize Python environment'),
  pythonDependenciesMissing('E1002', 'Python dependencies missing',
      'Required Python packages are not installed'),
  pythonTimeout('E1003', 'Python timeout', 'Python process timed out'),
  pythonInvalidImage(
      'E1004', 'Invalid image', 'The image file is corrupted or unsupported'),

  // Processing Errors (1100-1199)
  processingFailed('E1100', 'Processing failed', 'Image processing failed'),
  processingTimeout('E1101', 'Processing timeout', 'Processing took too long'),
  invalidSettings(
      'E1102', 'Invalid settings', 'Please check your processing settings'),

  // File Errors (1200-1299)
  fileNotFound('E1200', 'File not found', 'The specified file was not found'),
  fileTooLarge(
      'E1201', 'File too large', 'The file exceeds the maximum allowed size'),
  fileCorrupted(
      'E1202', 'File corrupted', 'The file is corrupted or unreadable'),
  invalidFileFormat(
      'E1203', 'Invalid file format', 'Please use PNG, JPG, or JPEG files'),

  // Output Errors (1300-1399)
  outputDirCreationFailed(
      'E1300', 'Output directory error', 'Failed to create output directory'),

  // License Errors (1400-1499)
  licenseInvalid('E1400', 'Invalid license', 'Please check your license'),
  licenseExpired('E1401', 'License expired', 'Your license has expired'),

  // Permission Errors (1500-1599)
  permissionDenied(
      'E1500', 'Permission denied', 'Please grant the required permissions'),

  // Unknown Error
  unknownError('E9999', 'Unknown error', 'An unexpected error occurred');

  final String code;
  final String title;
  final String message;

  const ErrorCode(this.code, this.title, this.message);
}

/// Custom exception for processing errors
class ProcessingException implements Exception {
  final ErrorCode errorCode;
  final String? details;

  ProcessingException(this.errorCode, {this.details});

  @override
  String toString() {
    return '${errorCode.code}: ${errorCode.title}${details != null ? ' - $details' : ''}';
  }
}
