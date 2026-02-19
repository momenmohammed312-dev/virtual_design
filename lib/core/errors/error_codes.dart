// error_codes.dart — Centralized Error Codes
// Virtual Design Silk Screen Studio
// Phase 9: Error handling with user-friendly messages

enum ErrorCode {
  // Python processing errors (1000-1999)
  pythonNotFound(1000, 'Python not found', 'Python 3.8+ is required. Please install Python.'),
  pythonDependenciesMissing(1001, 'Missing dependencies', 'Python packages missing. Run install_deps.bat/sh.'),
  pythonMemoryError(1002, 'Memory error', 'Image too large. Try reducing resolution.'),
  pythonInvalidImage(1003, 'Invalid image', 'Cannot process this image format.'),
  pythonProcessingFailed(1004, 'Processing failed', 'An error occurred during processing.'),
  pythonTimeout(1005, 'Processing timeout', 'Operation took too long. Try smaller image.'),
  
  // File system errors (2000-2999)
  fileNotFound(2000, 'File not found', 'The selected image could not be found.'),
  fileAccessDenied(2001, 'Access denied', 'Cannot access the file. Check permissions.'),
  fileTooLarge(2002, 'File too large', 'Image exceeds maximum size (8K).'),
  fileCorrupted(2003, 'Corrupted file', 'Image file appears to be corrupted.'),
  outputDirCreationFailed(2004, 'Output error', 'Cannot create output directory.'),
  
  // License errors (3000-3999)
  licenseNotActivated(3000, 'License required', 'Please activate your license to continue.'),
  licenseExpired(3001, 'License expired', 'Your license has expired. Renew to continue.'),
  licenseInvalid(3002, 'Invalid license', 'License is not valid for this device.'),
  licenseLimitReached(3003, 'Project limit reached', 'You\'ve reached your monthly project limit.'),
  
  // Permission errors (4000-4999)
  permissionDenied(4000, 'Permission denied', 'Storage permission is required.'),
  permissionPermanentlyDenied(4001, 'Permission blocked', 'Please enable permissions in Settings.'),
  
  // Network errors (5000-5999) - for future cloud licensing
  networkUnavailable(5000, 'No internet', 'Network connection required.'),
  networkTimeout(5001, 'Connection timeout', 'Server not responding.'),
  serverError(5002, 'Server error', 'Please try again later.'),
  
  // Unknown/Generic (9000-9999)
  unknownError(9000, 'Unknown error', 'An unexpected error occurred.'),
  userCancelled(9001, 'Cancelled', 'Operation was cancelled by user.'),
  ;

  final int code;
  final String title;
  final String message;

  const ErrorCode(this.code, this.title, this.message);

  /// Get ErrorCode from numeric code
  static ErrorCode? fromCode(int code) {
    return ErrorCode.values.firstWhere(
      (e) => e.code == code,
      orElse: () => ErrorCode.unknownError,
    );
  }

  /// Get user-friendly error message with context
  String getDisplayMessage([String? context]) {
    if (context != null) {
      return '$message\n\nDetails: $context';
    }
    return message;
  }

  /// Get error severity level
  ErrorSeverity get severity {
    switch (this) {
      case ErrorCode.unknownError:
      case ErrorCode.pythonProcessingFailed:
      case ErrorCode.fileCorrupted:
      case ErrorCode.serverError:
        return ErrorSeverity.critical;
      case ErrorCode.pythonMemoryError:
      case ErrorCode.fileTooLarge:
      case ErrorCode.outputDirCreationFailed:
        return ErrorSeverity.high;
      case ErrorCode.licenseExpired:
      case ErrorCode.licenseLimitReached:
      case ErrorCode.permissionPermanentlyDenied:
        return ErrorSeverity.medium;
      case ErrorCode.pythonDependenciesMissing:
      case ErrorCode.permissionDenied:
      case ErrorCode.networkUnavailable:
        return ErrorSeverity.low;
      default:
        return ErrorSeverity.medium;
    }
  }

  /// Should show retry button
  bool get canRetry {
    switch (this) {
      case ErrorCode.pythonNotFound:
      case ErrorCode.pythonDependenciesMissing:
      case ErrorCode.licenseNotActivated:
      case ErrorCode.licenseExpired:
      case ErrorCode.permissionPermanentlyDenied:
      case ErrorCode.networkUnavailable:
        return false;
      default:
        return true;
    }
  }

  /// Suggested action for user
  String get suggestedAction {
    switch (this) {
      case ErrorCode.pythonNotFound:
        return 'Install Python 3.8+ from python.org';
      case ErrorCode.pythonDependenciesMissing:
        return 'Run install_deps.bat (Windows) or install_deps.sh (Linux/macOS)';
      case ErrorCode.pythonMemoryError:
      case ErrorCode.fileTooLarge:
        return 'Try a smaller image or reduce resolution';
      case ErrorCode.fileNotFound:
        return 'Select the image again';
      case ErrorCode.permissionDenied:
      case ErrorCode.permissionPermanentlyDenied:
        return 'Open Settings and grant storage permission';
      case ErrorCode.licenseNotActivated:
        return 'Go to License page to activate';
      case ErrorCode.licenseExpired:
        return 'Renew your license to continue';
      case ErrorCode.licenseInvalid:
        return 'Contact support for assistance';
      case ErrorCode.licenseLimitReached:
        return 'Upgrade your plan or wait for next month';
      case ErrorCode.networkUnavailable:
        return 'Check your internet connection';
      case ErrorCode.unknownError:
        return 'Restart the app and try again';
      default:
        return 'Try again or select a different image';
    }
  }
}

enum ErrorSeverity {
  low,      // Informational, non-blocking
  medium,   // User action needed but not critical
  high,     // Significant issue, may lose data
  critical, // App may be unstable
}
