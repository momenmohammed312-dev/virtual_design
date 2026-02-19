// lib/presentation/error/error_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../core/python_bridge/process_result.dart';
import '../../core/errors/error_codes.dart';
import '../shared/error_screen_widget.dart';

class ErrorPage extends StatelessWidget {
  const ErrorPage({super.key});

  @override
  Widget build(BuildContext context) {
    // Get error data from arguments
    final args = Get.arguments as Map<String, dynamic>?;

    ErrorCode errorCode = args?['errorCode'] as ErrorCode? ?? ErrorCode.unknownError;
    String? rawMessage = args?['rawMessage'] as String?;
    VoidCallback? onRetry = args?['onRetry'] as VoidCallback?;
    VoidCallback? onGoBack = args?['onGoBack'] as VoidCallback?;

    // If we got a ProcessResult failure, map it to error code
    if (args?['processResult'] != null) {
      final result = args!['processResult'];
      if (result is ProcessResult && !result.success) {
        final error = ProcessingError.fromMessage(result.errorMessage ?? 'Unknown error');
        errorCode = _mapProcessingErrorToErrorCode(error.type);
        rawMessage = result.errorMessage;
      }
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F1117),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Get.back(),
        ),
      ),
      body: ProcessingErrorScreen(
        error: ProcessingError(
          type: _mapErrorCodeToProcessingErrorType(errorCode),
          rawMessage: rawMessage ?? '',
        ),
        onRetry: onRetry ?? () {
          Get.back();
        },
        onGoBack: onGoBack ?? () {
          Get.offAllNamed('/dashboard');
        },
      ),
    );
  }

  ProcessingErrorType _mapErrorCodeToProcessingErrorType(ErrorCode code) {
    switch (code) {
      case ErrorCode.pythonNotFound:
        return ProcessingErrorType.pythonNotFound;
      case ErrorCode.pythonDependenciesMissing:
        return ProcessingErrorType.missingDependencies;
      case ErrorCode.fileNotFound:
        return ProcessingErrorType.imageNotFound;
      case ErrorCode.fileTooLarge:
        return ProcessingErrorType.imageTooBig;
      case ErrorCode.fileCorrupted:
      case ErrorCode.pythonInvalidImage:
        return ProcessingErrorType.unsupportedFormat;
      case ErrorCode.outputDirCreationFailed:
        return ProcessingErrorType.outputDirFailed;
      case ErrorCode.pythonTimeout:
        return ProcessingErrorType.processingTimeout;
      default:
        return ProcessingErrorType.unknown;
    }
  }

  ErrorCode _mapProcessingErrorToErrorCode(ProcessingErrorType type) {
    switch (type) {
      case ProcessingErrorType.pythonNotFound:
        return ErrorCode.pythonNotFound;
      case ProcessingErrorType.missingDependencies:
        return ErrorCode.pythonDependenciesMissing;
      case ProcessingErrorType.imageNotFound:
        return ErrorCode.fileNotFound;
      case ProcessingErrorType.imageTooBig:
        return ErrorCode.fileTooLarge;
      case ProcessingErrorType.unsupportedFormat:
        return ErrorCode.pythonInvalidImage;
      case ProcessingErrorType.outputDirFailed:
        return ErrorCode.outputDirCreationFailed;
      case ProcessingErrorType.processingTimeout:
        return ErrorCode.pythonTimeout;
      default:
        return ErrorCode.unknownError;
    }
  }
}
