// lib/presentation/shared/error_screen_widget.dart

import 'package:flutter/material.dart';

// Error Types - defined here to avoid circular imports
enum ProcessingErrorType {
  pythonNotFound,
  missingDependencies,
  imageNotFound,
  imageTooBig,
  unsupportedFormat,
  processingTimeout,
  outputDirFailed,
  unknown,
}

// Error Model - defined here to avoid circular imports
class ProcessingError {
  final ProcessingErrorType type;
  final String rawMessage;
  final List<String> missingPackages;

  const ProcessingError({
    required this.type,
    this.rawMessage = '',
    this.missingPackages = const [],
  });

  factory ProcessingError.fromMessage(String message) {
    final lower = message.toLowerCase();
    if (lower.contains('python not found') ||
        (lower.contains('not found') && lower.contains('python'))) {
      return ProcessingError(
          type: ProcessingErrorType.pythonNotFound, rawMessage: message);
    }
    if (lower.contains('pip install') ||
        lower.contains('missing python package') ||
        lower.contains('modulenotfounderror')) {
      return ProcessingError(
          type: ProcessingErrorType.missingDependencies, rawMessage: message);
    }
    if (lower.contains('image file not found') || lower.contains('file not found')) {
      return ProcessingError(
          type: ProcessingErrorType.imageNotFound, rawMessage: message);
    }
    if (lower.contains('memoryerror') || lower.contains('too large')) {
      return ProcessingError(
          type: ProcessingErrorType.imageTooBig, rawMessage: message);
    }
    if (lower.contains('invalid image format') ||
        lower.contains('cannot read') ||
        lower.contains('cannot decode') ||
        lower.contains('decode error') ||
        lower.contains('unsupported image format')) {
      return ProcessingError(
          type: ProcessingErrorType.unsupportedFormat, rawMessage: message);
    }
    return ProcessingError(
        type: ProcessingErrorType.unknown, rawMessage: message);
  }
}

// Main Error Widget
class ProcessingErrorScreen extends StatelessWidget {
  final ProcessingError error;
  final VoidCallback onRetry;
  final VoidCallback onGoBack;

  const ProcessingErrorScreen({
    super.key,
    required this.error,
    required this.onRetry,
    required this.onGoBack,
  });

  @override
  Widget build(BuildContext context) {
    final errorInfo = _getErrorInfo(error.type);

    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 500),
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(errorInfo.icon, size: 64, color: errorInfo.color),
            const SizedBox(height: 24),
            Text(
              errorInfo.title,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Text(
              errorInfo.description,
              style: const TextStyle(
                fontSize: 16,
                color: Colors.white70,
              ),
              textAlign: TextAlign.center,
            ),
            if (errorInfo.instructions != null) ...[
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.black26,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SelectableText(
                  errorInfo.instructions!,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 14,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 32),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton(
                  onPressed: onGoBack,
                  child: const Text('Go Back'),
                ),
                const SizedBox(width: 16),
                ElevatedButton(
                  onPressed: onRetry,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  _ErrorInfo _getErrorInfo(ProcessingErrorType type) {
    switch (type) {
      case ProcessingErrorType.pythonNotFound:
        return _ErrorInfo(
          icon: Icons.code_off,
          color: const Color(0xFFF87171),
          title: 'Python Not Found',
          description: 'The app requires Python 3.8+ to process images.\n'
              'Please install Python from the official website and add it to PATH.',
          instructions: 'https://python.org/downloads',
        );
      case ProcessingErrorType.missingDependencies:
        return _ErrorInfo(
          icon: Icons.extension_off,
          color: const Color(0xFFFB923C),
          title: 'Missing Dependencies',
          description: 'Some required packages are not installed.\n'
              'Run the following command in Command Prompt:',
          instructions: 'pip install -r python/requirements.txt',
        );
      case ProcessingErrorType.imageNotFound:
        return _ErrorInfo(
          icon: Icons.image_not_supported,
          color: const Color(0xFFFACC15),
          title: 'Image Not Found',
          description: 'The image was not found at the specified path.\n'
              'It may have been moved or deleted.',
          instructions: null,
        );
      case ProcessingErrorType.imageTooBig:
        return _ErrorInfo(
          icon: Icons.photo_size_select_large,
          color: const Color(0xFFFB923C),
          title: 'Image Too Large',
          description: 'The image exceeds the allowed size limit.\n'
              'Try reducing the DPI or using a smaller image.',
          instructions: null,
        );
      case ProcessingErrorType.unsupportedFormat:
        return _ErrorInfo(
          icon: Icons.file_present,
          color: const Color(0xFFFACC15),
          title: 'Unsupported Format',
          description: 'The image format is not supported.\n'
              'Use: PNG, JPG, TIFF, or BMP.',
          instructions: null,
        );
      case ProcessingErrorType.processingTimeout:
        return _ErrorInfo(
          icon: Icons.timer_off,
          color: const Color(0xFF94A3B8),
          title: 'Processing Timeout',
          description: 'Processing took too long and was cancelled.\n'
              'Try with a smaller image or lower settings.',
          instructions: null,
        );
      default:
        return _ErrorInfo(
          icon: Icons.error_outline,
          color: const Color(0xFF94A3B8),
          title: 'Unknown Error',
          description: error.rawMessage.isNotEmpty
              ? error.rawMessage
              : 'An unexpected error occurred. Please try again.',
          instructions: null,
        );
    }
  }
}

class _ErrorInfo {
  final IconData icon;
  final Color color;
  final String title;
  final String description;
  final String? instructions;

  _ErrorInfo({
    required this.icon,
    required this.color,
    required this.title,
    required this.description,
    this.instructions,
  });
}
