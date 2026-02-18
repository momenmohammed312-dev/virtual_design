import 'package:flutter_test/flutter_test.dart';
import 'package:virtual_design/core/python_bridge/python_processor.dart';
import 'package:virtual_design/core/python_bridge/python_config.dart';

void main() {
  group('PythonProcessor', () {
    late PythonProcessor processor;
    late PythonConfig config;

    setUp(() async {
      config = PythonConfig();
      processor = PythonProcessor(config: config);
    });

    test('PythonProcessor initialization', () {
      expect(processor.config, isNotNull);
      expect(processor, isA<PythonProcessor>());
    });

    test('PythonConfig can be instantiated', () {
      final cfg = PythonConfig();
      expect(cfg, isNotNull);
      expect(cfg.isInitialized, isFalse);
    });

    test('PythonConfig has resolution methods', () {
      final cfg = PythonConfig();
      expect(cfg.resolvePythonCommand, isA<Function>());
      expect(cfg.initialize, isA<Function>());
    });

    test('processImage method exists', () {
      expect(processor.processImage, isA<Function>());
    });
  });
}
