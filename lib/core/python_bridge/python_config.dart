// python_config.dart — Python Command Auto-Detection
// Virtual Design Silk Screen Studio
//
// HIGH #1 FIX: بدل hardcoded 'python' يبحث عن الأمر الصح تلقائياً
// يجرب: python3 → python → py (Windows)

import 'dart:io';

/// Exception لما Python مش موجود
class PythonNotFoundError implements Exception {
  final String message;
  const PythonNotFoundError(this.message);
  @override
  String toString() => 'PythonNotFoundError: $message';
}

/// Exception لما مكتبة Python ناقصة
class PythonDependencyError implements Exception {
  final List<String> missing;
  const PythonDependencyError(this.missing);
  @override
  String toString() => 'Missing Python packages: ${missing.join(", ")}';
}

class PythonConfig {
  static const List<String> _candidates = ['python3', 'python', 'py'];

  String? _resolvedCommand;
  String? _resolvedVersion;
  bool _initialized = false;

  /// الأمر المُحدَّد بعد الـ detection
  String? get resolvedCommand => _resolvedCommand;

  /// نسخة Python المُكتشَفة
  String? get resolvedVersion => _resolvedVersion;

  bool get isInitialized => _initialized;

  /// البحث عن أمر Python الصحيح
  /// يُخزَّن في cache بعد أول استدعاء
  Future<String> resolvePythonCommand() async {
    if (_resolvedCommand != null) return _resolvedCommand!;

    for (final cmd in _candidates) {
      try {
        final result = await Process.run(cmd, ['--version']);
        if (result.exitCode == 0) {
          final versionOutput =
              (result.stdout as String).trim().isNotEmpty
                  ? result.stdout as String
                  : result.stderr as String;
          _resolvedCommand = cmd;
          _resolvedVersion = versionOutput.trim();
          return cmd;
        }
      } catch (_) {
        // أمر غير موجود — جرّب التالي
        continue;
      }
    }

    throw const PythonNotFoundError(
      'Python غير مثبّت على هذا الجهاز.\n'
      'حمّل Python 3.8+ من python.org\n'
      'وتأكد من إضافته لـ PATH.',
    );
  }

  /// تهيئة PythonConfig: detect + check dependencies
  /// يُستدعى مرة واحدة عند launch في InitialBinding
  Future<PythonInitResult> initialize() async {
    try {
      await resolvePythonCommand();
      final missing = await _checkDependencies();
      _initialized = true;
      return PythonInitResult(
        success: missing.isEmpty,
        pythonVersion: _resolvedVersion,
        missingPackages: missing,
      );
    } on PythonNotFoundError catch (e) {
      return PythonInitResult(
        success: false,
        error: e.message,
        missingPackages: [],
      );
    } catch (e) {
      return PythonInitResult(
        success: false,
        error: e.toString(),
        missingPackages: [],
      );
    }
  }

  /// التحقق من وجود المكتبات المطلوبة
  Future<List<String>> _checkDependencies() async {
    const checkScript = '''
import sys
missing = []
packages = {
    "cv2": "opencv-python",
    "numpy": "numpy",
    "PIL": "Pillow",
    "skimage": "scikit-image",
    "reportlab": "reportlab",
}
for module, package in packages.items():
    try:
        __import__(module)
    except ImportError:
        missing.append(package)
print(",".join(missing))
''';

    try {
      final python = await resolvePythonCommand();
      final result = await Process.run(python, ['-c', checkScript]);
      final output = (result.stdout as String).trim();
      if (output.isEmpty) return [];
      return output.split(',').where((s) => s.isNotEmpty).toList();
    } catch (_) {
      return []; // لو فشل الفحص — مش مشكلة، نكمل
    }
  }

  /// إرجاع script للتثبيت الفوري
  Future<bool> installMissingDependencies(List<String> packages) async {
    try {
      final python = await resolvePythonCommand();
      final result = await Process.run(
        python,
        ['-m', 'pip', 'install', ...packages],
        runInShell: true,
      );
      return result.exitCode == 0;
    } catch (_) {
      return false;
    }
  }

  /// مسار مجلد scripts البايثون
  /// في Windows Desktop: بجانب الـ executable
  /// في Debug: مجلد المشروع
  Future<String> getPythonScriptsDir() async {
    if (Platform.isWindows && !_isDebugMode()) {
      final exeDir = File(Platform.resolvedExecutable).parent.path;
      return '$exeDir\\python';
    }
    // Debug mode — مجلد المشروع
    return '${Directory.current.path}/python';
  }

  bool _isDebugMode() {
    bool debug = false;
    assert(() {
      debug = true;
      return true;
    }());
    return debug;
  }
}

/// نتيجة التهيئة
class PythonInitResult {
  final bool success;
  final String? pythonVersion;
  final String? error;
  final List<String> missingPackages;

  const PythonInitResult({
    required this.success,
    this.pythonVersion,
    this.error,
    required this.missingPackages,
  });

  bool get hasMissingPackages => missingPackages.isNotEmpty;
}
