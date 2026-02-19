// batch_process_usecase.dart — Batch Processing Use Case
// Virtual Design Silk Screen Studio
//
// MED #5 FIX: Batch Processing مذكور في SOP ومفيش له كود — إضافة جديدة

import 'dart:async';
import '../../core/python_bridge/python_processor.dart';
import '../../core/python_bridge/process_result.dart';
import '../entities/processing_settings.dart';

// ─── Batch Progress ────────────────────────────────────────────────────────

class BatchProgress {
  final int currentIndex;    // رقم الصورة الحالية (0-based)
  final int totalImages;     // إجمالي الصور
  final String currentPath;  // مسار الصورة الحالية
  final double imageProgress; // تقدم الصورة الحالية (0.0 → 1.0)
  final String message;
  final List<BatchImageResult> completed; // الصور المنتهية

  const BatchProgress({
    required this.currentIndex,
    required this.totalImages,
    required this.currentPath,
    this.imageProgress = 0.0,
    this.message = '',
    this.completed = const [],
  });

  /// التقدم الكلي (0.0 → 1.0) بحساب الصور المنتهية + تقدم الحالية
  double get overallProgress {
    if (totalImages == 0) return 0.0;
    final completedFraction = currentIndex / totalImages;
    final currentFraction = imageProgress / totalImages;
    return (completedFraction + currentFraction).clamp(0.0, 1.0);
  }

  String get displayText =>
      'صورة ${currentIndex + 1} من $totalImages: $message';
}

class BatchImageResult {
  final String imagePath;
  final bool success;
  final String? outputDirectory;
  final String? errorMessage;

  const BatchImageResult({
    required this.imagePath,
    required this.success,
    this.outputDirectory,
    this.errorMessage,
  });
}

// ─── Use Case ──────────────────────────────────────────────────────────────

class BatchProcessUseCase {
  final PythonProcessor processor;

  BatchProcessUseCase({required this.processor});

  /// معالجة قائمة صور بنفس الإعدادات — تُرجع Stream للـ progress
  ///
  /// [imagePaths]  قائمة مسارات الصور
  /// [settings]    إعدادات الطباعة (تُطبَّق على الكل)
  Stream<BatchProgress> execute(
    List<String> imagePaths,
    ProcessingSettings settings,
  ) async* {
    final results = <BatchImageResult>[];

    for (int i = 0; i < imagePaths.length; i++) {
      final path = imagePaths[i];

      // تحديث البداية
      yield BatchProgress(
        currentIndex: i,
        totalImages: imagePaths.length,
        currentPath: path,
        imageProgress: 0.0,
        message: 'جاري البدء...',
        completed: List.unmodifiable(results),
      );

      ProcessResult result;
      try {
        result = await processor.processImage(
          imagePath: path,
          settings: settings,
          onProgress: (progress, msg) {
            // نُرسِل progress updates لكن يصعب yield من داخل callback
            // يمكن تحسين هذا لاحقاً بـ StreamController
          },
        );
      } catch (e) {
        result = ProcessResult.failure('Exception: $e');
      }

      final imageResult = BatchImageResult(
        imagePath: path,
        success: result.success,
        outputDirectory: result.outputDirectory,
        errorMessage: result.errorMessage,
      );
      results.add(imageResult);

      yield BatchProgress(
        currentIndex: i,
        totalImages: imagePaths.length,
        currentPath: path,
        imageProgress: 1.0,
        message: result.success ? 'تم بنجاح ✓' : 'فشل: ${result.errorMessage}',
        completed: List.unmodifiable(results),
      );
    }

    // الانتهاء
    final successCount = results.where((r) => r.success).length;
    yield BatchProgress(
      currentIndex: imagePaths.length,
      totalImages: imagePaths.length,
      currentPath: '',
      imageProgress: 1.0,
      message:
          'اكتملت المعالجة: $successCount/${imagePaths.length} ناجح',
      completed: List.unmodifiable(results),
    );
  }

  /// إلغاء المعالجة الحالية
  Future<void> cancel() async {
    // يمكن تطبيق إلغاء العملية بـ Process.kill() لاحقاً
  }
}
