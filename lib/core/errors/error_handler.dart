// error_handler.dart — Centralized Error Processing
// Virtual Design Silk Screen Studio

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'error_codes.dart';

class ErrorHandler {
  /// Process an error and show appropriate UI
  static void handleError(
    dynamic error, {
    String? context,
    bool showDialog = true,
    VoidCallback? onRetry,
  }) {
    final errorCode = _mapToErrorCode(error);
    final message = errorCode.getDisplayMessage(context);
    
    if (showDialog) {
      _showErrorDialog(
        title: errorCode.title,
        message: message,
        errorCode: errorCode,
        onRetry: onRetry,
      );
    } else {
      // Show snackbar instead
      Get.snackbar(
        errorCode.title,
        message,
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: _getSeverityColor(errorCode.severity),
        colorText: Colors.white,
        mainButton: errorCode.canRetry
            ? TextButton(
                onPressed: () {
                  Get.back(); // Close snackbar
                  onRetry?.call();
                },
                child: const Text('Retry', style: TextStyle(color: Colors.white)),
              )
            : null,
        duration: const Duration(seconds: 5),
      );
    }
  }

  /// Map various error types to ErrorCode
  static ErrorCode _mapToErrorCode(dynamic error) {
    if (error is ErrorCode) return error;
    
    if (error is String) {
      // Check for prefixed error codes first (from PythonProcessor)
      if (error.startsWith('FILE_NOT_FOUND:')) {
        return ErrorCode.fileNotFound;
      }
      if (error.startsWith('INVALID_FORMAT:')) {
        return ErrorCode.pythonInvalidImage;
      }
      if (error.startsWith('MISSING_DEPENDENCY:')) {
        return ErrorCode.pythonDependenciesMissing;
      }
      if (error.startsWith('MEMORY_ERROR:')) {
        return ErrorCode.pythonMemoryError;
      }
      if (error.startsWith('PROCESSING_FAILED:')) {
        return ErrorCode.pythonProcessingFailed;
      }
      if (error.startsWith('UNKNOWN_ERROR:')) {
        return ErrorCode.unknownError;
      }

      // Fallback to keyword matching
      final lower = error.toLowerCase();
      if (lower.contains('python') && lower.contains('not found')) {
        return ErrorCode.pythonNotFound;
      }
      if (lower.contains('module') && lower.contains('import')) {
        return ErrorCode.pythonDependenciesMissing;
      }
      if (lower.contains('memory')) {
        return ErrorCode.pythonMemoryError;
      }
      if (lower.contains('file not found') || lower.contains('no such file')) {
        return ErrorCode.fileNotFound;
      }
      if (lower.contains('permission') && lower.contains('denied')) {
        return ErrorCode.permissionDenied;
      }
      if (lower.contains('license')) {
        if (lower.contains('expired')) return ErrorCode.licenseExpired;
        if (lower.contains('invalid')) return ErrorCode.licenseInvalid;
        return ErrorCode.licenseNotActivated;
      }
    }
    
    if (error is Exception) {
      final msg = error.toString().toLowerCase();
      if (msg.contains('processexception')) {
        return ErrorCode.pythonNotFound;
      }
      if (msg.contains('socketexception')) {
        return ErrorCode.networkUnavailable;
      }
    }
    
    return ErrorCode.unknownError;
  }

  /// Show error dialog with retry option
  static void _showErrorDialog({
    required String title,
    required String message,
    required ErrorCode errorCode,
    VoidCallback? onRetry,
  }) {
    Get.dialog(
      AlertDialog(
        icon: _getSeverityIcon(errorCode.severity),
        title: Text(title),
        content: Text(message),
        actions: [
          if (errorCode.canRetry && onRetry != null)
            TextButton(
              onPressed: () {
                Get.back(); // Close dialog
                onRetry();
              },
              child: const Text('Retry'),
            ),
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  /// Get color based on severity
  static Color _getSeverityColor(ErrorSeverity severity) {
    switch (severity) {
      case ErrorSeverity.low:
        return Colors.blue;
      case ErrorSeverity.medium:
        return Colors.orange;
      case ErrorSeverity.high:
        return Colors.deepOrange;
      case ErrorSeverity.critical:
        return Colors.red;
    }
  }

  /// Get icon based on severity
  static Icon? _getSeverityIcon(ErrorSeverity severity) {
    switch (severity) {
      case ErrorSeverity.low:
        return const Icon(Icons.info_outline, color: Colors.blue);
      case ErrorSeverity.medium:
        return const Icon(Icons.warning_amber, color: Colors.orange);
      case ErrorSeverity.high:
        return const Icon(Icons.error, color: Colors.deepOrange);
      case ErrorSeverity.critical:
        return const Icon(Icons.cancel, color: Colors.red);
    }
  }

  /// Log error to console (for debugging)
  static void logError(dynamic error, {String? context}) {
    final errorCode = _mapToErrorCode(error);
    debugPrint('''
❌ ERROR: ${errorCode.code} - ${errorCode.title}
Context: ${context ?? 'N/A'}
Error: $error
Severity: ${errorCode.severity}
Suggested Action: ${errorCode.suggestedAction}
    ''');
  }
}
