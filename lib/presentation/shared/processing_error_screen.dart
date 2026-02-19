// processing_error_screen.dart — User-Friendly Error Display
// Virtual Design Silk Screen Studio

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/errors/error_codes.dart';

class ProcessingErrorScreen extends StatelessWidget {
  final ErrorCode errorCode;
  final String? context;
  final VoidCallback? onRetry;
  final VoidCallback? onGoHome;

  const ProcessingErrorScreen({
    super.key,
    required this.errorCode,
    this.context,
    this.onRetry,
    this.onGoHome,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = _getSeverityColor(errorCode.severity);
    
    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text('Error'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Get.back(),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Error Icon
              Center(
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: color.withAlpha((0.1 * 255).round()),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    _getSeverityIcon(errorCode.severity),
                    size: 40,
                    color: color,
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Title
              Text(
                errorCode.title,
                style: theme.textTheme.headlineSmall?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w700,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),

              // Message
              Text(
                errorCode.getDisplayMessage(this.context),
                style: theme.textTheme.bodyLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),

              // Suggested Action Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: theme.dividerColor),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.lightbulb_outline, color: color, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          'Suggested Action',
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      errorCode.suggestedAction,
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),

              // Action Buttons
              if (errorCode.canRetry && onRetry != null)
                ElevatedButton.icon(
                  onPressed: () {
                    Get.back(); // Close error screen
                    onRetry!();
                  },
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: color,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              if (errorCode.canRetry && onRetry != null)
                const SizedBox(height: 12),

              OutlinedButton.icon(
                onPressed: () {
                  if (onGoHome != null) {
                    onGoHome!();
                  } else {
                    Get.offAllNamed('/dashboard');
                  }
                },
                icon: const Icon(Icons.home),
                label: const Text('Go to Dashboard'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
              const SizedBox(height: 12),

              TextButton(
                onPressed: () => Get.back(),
                child: const Text('Go Back'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getSeverityColor(ErrorSeverity severity) {
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

  IconData _getSeverityIcon(ErrorSeverity severity) {
    switch (severity) {
      case ErrorSeverity.low:
        return Icons.info_outline;
      case ErrorSeverity.medium:
        return Icons.warning_amber;
      case ErrorSeverity.high:
        return Icons.error;
      case ErrorSeverity.critical:
        return Icons.cancel;
    }
  }
}
