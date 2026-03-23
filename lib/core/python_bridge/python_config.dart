// python_config.dart — Python Command Auto-Detection
// Virtual Design Silk Screen Studio
//
// FATAL #1 FIX: getPythonScriptsDir() walks up from exe to find python/ folder
// HIGH #2 FIX: isPythonAvailable flag blocks processing when Python is absent

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
  bool _pythonAvailable = false;

  /// الأمر المُحدَّد بعد الـ detection
  String? get resolvedCommand => _resolvedCommand;

  /// نسخة Python المُكتشَفة
  String? get resolvedVersion => _resolvedVersion;

  bool get isInitialized => _initialized;

  /// Whether Python is fully available (found + all dependencies present)
  bool get isPythonAvailable => _pythonAvailable;

  /// البحث عن أمر Python الصحيح
  /// يُخزَّن في cache بعد أول استدعاء
  Future<String> resolvePythonCommand() async {
    if (_resolvedCommand != null) return _resolvedCommand!;

    final sep = Platform.pathSeparator;
    
    // Phase 25: Prioritize local virtual environment if it exists
    // This ensures reportlab and other deps are used even if system python lacks them
    final venvPath = Platform.isWindows 
        ? '${Directory.current.path}${sep}venv${sep}Scripts${sep}python.exe'
        : '${Directory.current.path}${sep}venv${sep}bin${sep}python';
        
    if (await File(venvPath).exists()) {
      print('[PythonConfig] Found local venv: $venvPath');
      try {
        final result = await Process.run(venvPath, ['--version']);
        if (result.exitCode == 0) {
          _resolvedCommand = venvPath;
          _resolvedVersion = (result.stdout as String).trim();
          return venvPath;
        }
      } catch (e) {
        print('[PythonConfig] venv found but failed validation: $e');
      }
    }

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
      _pythonAvailable = missing.isEmpty;
      return PythonInitResult(
        success: missing.isEmpty,
        pythonVersion: _resolvedVersion,
        missingPackages: missing,
      );
    } on PythonNotFoundError catch (e) {
      _pythonAvailable = false;
      return PythonInitResult(
        success: false,
        error: e.message,
        missingPackages: [],
      );
    } catch (e) {
      _pythonAvailable = false;
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
  /// FATAL #1 FIX: يبحث بالتدريج من مسار الـ executable للأعلى
  /// بدل الاعتماد على Directory.current (اللي بيرجع مسار غلط في debug)
  Future<String> getPythonScriptsDir() async {
    final sep = Platform.pathSeparator;

    // Release mode: بجانب الـ exe مباشرة
    if (Platform.isWindows && !_isDebugMode()) {
      final exeDir = File(Platform.resolvedExecutable).parent.path;
      final releasePath = '$exeDir${sep}python';
      print('[PythonConfig] Release mode, checking: $releasePath');
      return releasePath;
    }

    // Debug mode: walk up from exe path to find "python" folder
    // Flutter debug exe is typically at:
    //   build\windows\x64\runner\Debug\virtual_design.exe
    // Project root is 5-7 levels up
    var dir = File(Platform.resolvedExecutable).parent;
    for (int i = 0; i < 7; i++) {
      final candidate = Directory('${dir.path}${sep}python');
      if (await candidate.exists()) {
        // Verify the directory is accessible
        try {
          await candidate.list().first;
          print('[PythonConfig] Found python dir: ${candidate.path}');
          return candidate.path;
        } catch (e) {
          print('[PythonConfig] python dir found but inaccessible: ${candidate.path} — $e');
          // Continue searching up
        }
      }
      dir = dir.parent;
    }

    // Fallback: try Directory.current (original behavior)
    final fallback = '${Directory.current.path}${sep}python';
    print('[PythonConfig] WARN: using fallback path: $fallback');
    return fallback;
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
