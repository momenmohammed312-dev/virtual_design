// error_screen_widget.dart — Professional Error Screens
// Virtual Design Silk Screen Studio
//
// HIGH #2 FIX: شاشات خطأ احترافية بدل Snackbar أو Demo Mode بدون توضيح

import 'package:flutter/material.dart';

// ─── Error Types ──────────────────────────────────────────────────────────────

enum ProcessingErrorType {
  pythonNotFound,
  missingDependencies,
  imageNotFound,
  imageTooBig,
  unsupportedFormat,
  colorSeparationFailed,
  outputDirFailed,
  processingTimeout,
  unknown,
}

class ProcessingError {
  final ProcessingErrorType type;
  final String rawMessage;
  final List<String> missingPackages;

  const ProcessingError({
    required this.type,
    this.rawMessage = '',
    this.missingPackages = const [],
  });

  /// اكتشاف نوع الخطأ من رسالة الـ stderr
  factory ProcessingError.fromMessage(String message) {
    if (message.contains('Python غير مثبّت') ||
        message.contains('not found') && message.contains('python')) {
      return ProcessingError(
          type: ProcessingErrorType.pythonNotFound, rawMessage: message);
    }
    if (message.contains('pip install') ||
        message.contains('Missing Python package') ||
        message.contains('ModuleNotFoundError')) {
      return ProcessingError(
          type: ProcessingErrorType.missingDependencies, rawMessage: message);
    }
    if (message.contains('Image file not found')) {
      return ProcessingError(
          type: ProcessingErrorType.imageNotFound, rawMessage: message);
    }
    if (message.contains('MemoryError') || message.contains('too large')) {
      return ProcessingError(
          type: ProcessingErrorType.imageTooBig, rawMessage: message);
    }
    if (message.contains('Invalid image format') ||
        message.contains('cannot read')) {
      return ProcessingError(
          type: ProcessingErrorType.unsupportedFormat, rawMessage: message);
    }
    return ProcessingError(
        type: ProcessingErrorType.unknown, rawMessage: message);
  }
}

// ─── Main Error Widget ────────────────────────────────────────────────────────

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
    final info = _getErrorInfo(error.type);
    return Container(
      color: const Color(0xFF0F1117),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // أيقونة الخطأ
                Container(
                  width: 80, height: 80,
                  decoration: BoxDecoration(
                    color: info.color.withAlpha((0.12 * 255).round()),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: info.color.withAlpha((0.3 * 255).round())),
                  ),
                  child: Icon(info.icon, size: 40, color: info.color),
                ),
                const SizedBox(height: 24),

                // العنوان
                Text(
                  info.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),

                // الوصف
                Text(
                  info.description,
                  style: TextStyle(
                    color: Colors.white.withAlpha((0.65 * 255).round()),
                    fontSize: 14,
                    height: 1.7,
                  ),
                  textAlign: TextAlign.center,
                ),

                // تعليمات إضافية
                if (info.instructions != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1A1F2E),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF2D3748)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.terminal, size: 14, color: Color(0xFF94A3B8)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            info.instructions!,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              color: Color(0xFF86EFAC),
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                // رسالة تقنية (قابلة للطي)
                if (error.rawMessage.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _TechnicalDetails(message: error.rawMessage),
                ],

                const SizedBox(height: 28),

                // أزرار الإجراءات
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: onGoBack,
                        icon: const Icon(Icons.arrow_back, size: 16),
                        label: const Text('رجوع'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.white70,
                          side: const BorderSide(color: Color(0xFF2D3748)),
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: onRetry,
                        icon: const Icon(Icons.refresh, size: 16),
                        label: const Text('إعادة المحاولة'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF4F46E5),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
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
          title: 'Python غير مثبّت',
          description:
              'يحتاج التطبيق Python 3.8+ لمعالجة الصور.\nحمّل Python من الموقع الرسمي وتأكد من إضافته لـ PATH.',
          instructions: 'https://python.org/downloads',
        );
      case ProcessingErrorType.missingDependencies:
        return _ErrorInfo(
          icon: Icons.extension_off,
          color: const Color(0xFFFB923C),
          title: 'مكتبات Python ناقصة',
          description:
              'بعض المكتبات المطلوبة غير مثبّتة.\nشغّل الأمر التالي في Command Prompt:',
          instructions: 'pip install -r python/requirements.txt',
        );
      case ProcessingErrorType.imageNotFound:
        return _ErrorInfo(
          icon: Icons.image_not_supported,
          color: const Color(0xFFFACC15),
          title: 'الصورة غير موجودة',
          description: 'لم يُعثَر على الصورة في المسار المحدد.\nربما تم نقلها أو حذفها.',
          instructions: null,
        );
      case ProcessingErrorType.imageTooBig:
        return _ErrorInfo(
          icon: Icons.photo_size_select_large,
          color: const Color(0xFFFB923C),
          title: 'الصورة كبيرة جداً',
          description:
              'الصورة تتجاوز الحجم المسموح.\nجرّب تقليل الـ DPI أو استخدام صورة أصغر حجماً.',
          instructions: null,
        );
      case ProcessingErrorType.unsupportedFormat:
        return _ErrorInfo(
          icon: Icons.file_present,
          color: const Color(0xFFFACC15),
          title: 'صيغة غير مدعومة',
          description:
              'صيغة الصورة غير مدعومة.\nاستخدم: PNG, JPG, TIFF, أو BMP.',
          instructions: null,
        );
      case ProcessingErrorType.processingTimeout:
        return _ErrorInfo(
          icon: Icons.timer_off,
          color: const Color(0xFF94A3B8),
          title: 'انتهت مهلة المعالجة',
          description:
              'استغرقت المعالجة وقتاً طويلاً.\nجرّب صورة أصغر أو قلّل عدد الألوان.',
          instructions: null,
        );
      default:
        return _ErrorInfo(
          icon: Icons.error_outline,
          color: const Color(0xFFF87171),
          title: 'خطأ في المعالجة',
          description: 'حدث خطأ غير متوقع أثناء معالجة الصورة.',
          instructions: null,
        );
    }
  }
}

// ─── Supporting Widgets ───────────────────────────────────────────────────────

class _ErrorInfo {
  final IconData icon;
  final Color color;
  final String title;
  final String description;
  final String? instructions;

  const _ErrorInfo({
    required this.icon,
    required this.color,
    required this.title,
    required this.description,
    this.instructions,
  });
}

class _TechnicalDetails extends StatefulWidget {
  final String message;
  const _TechnicalDetails({required this.message});

  @override
  State<_TechnicalDetails> createState() => _TechnicalDetailsState();
}

class _TechnicalDetailsState extends State<_TechnicalDetails> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        GestureDetector(
          onTap: () => setState(() => _expanded = !_expanded),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'تفاصيل تقنية',
                style: TextStyle(
                  color: Colors.white.withAlpha((0.4 * 255).round()),
                  fontSize: 12,
                ),
              ),
              const SizedBox(width: 4),
              Icon(
                _expanded ? Icons.expand_less : Icons.expand_more,
                size: 14,
                color: Colors.white.withAlpha((0.4 * 255).round()),
              ),
            ],
          ),
        ),
        if (_expanded) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF0A0D14),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF2D3748)),
            ),
            child: Text(
              widget.message,
              style: const TextStyle(
                fontFamily: 'monospace',
                color: Color(0xFF94A3B8),
                fontSize: 11,
                height: 1.5,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

// ─── Inline Error Banner (للـ Snackbar replacement) ───────────────────────────

class ProcessingErrorBanner extends StatelessWidget {
  final String message;
  final VoidCallback? onDismiss;

  const ProcessingErrorBanner({
    super.key,
    required this.message,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1A0A0A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFF87171).withAlpha((0.4 * 255).round())),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFF87171), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 13),
            ),
          ),
          if (onDismiss != null)
            GestureDetector(
              onTap: onDismiss,
              child: const Icon(Icons.close, color: Color(0xFF64748B), size: 16),
            ),
        ],
      ),
    );
  }
}
