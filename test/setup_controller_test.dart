// test/setup_controller_test.dart
// Tests for SetupController color complexity and paper size handling

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:get/route_manager.dart';
import 'package:virtual_design/presentation/setup/setup_controller.dart';
import 'package:virtual_design/domain/repositories/processing_repository.dart';
import 'package:virtual_design/domain/entities/processing_settings.dart';
import 'package:virtual_design/core/python_bridge/process_result.dart';

// Simple mock repository to capture last processing settings
class MockProcessingRepository implements ProcessingRepository {
  ProcessingSettings? lastSettingsCaught;
  final bool shouldSucceed;
  final String? outputDir;

  MockProcessingRepository({this.shouldSucceed = true, this.outputDir});

  @override
  Future<ProcessResult> processImage({required String imagePath, required ProcessingSettings settings, String? outputDir, void Function(double, String)? onProgress}) async {
    lastSettingsCaught = settings;
    if (shouldSucceed) {
      return ProcessResult.success(outputDirectory: outputDir ?? this.outputDir ?? '/tmp/output');
    } else {
      return ProcessResult.failure('Mock failure');
    }
  }

  @override
  Future<List<String>> getSavedProjects() async => [];

  @override
  Future<void> deleteProject(String projectId) async {}

  @override
  Future<void> saveSettings(ProcessingSettings settings) async {}

  @override
  Future<ProcessingSettings?> loadLastSettings() async => null;
}

void main() {
  // Initialize Flutter binding for widget tests
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Auto color (0) passes to processing and preserves paper dims', (WidgetTester tester) async {
    final repo = MockProcessingRepository(shouldSucceed: true, outputDir: '/out');
    final ctrl = SetupController(repository: repo);

    ctrl.imagePath.value = '/path/img.png';
    ctrl.selectedColors.value = 0; // Auto
    ctrl.paperWidthCm.value = 20.0;
    ctrl.paperHeightCm.value = 25.0;

    await tester.pumpWidget(GetMaterialApp(
      home: Scaffold(body: SizedBox.shrink()),
      getPages: [
        GetPage(name: '/preview', page: () => Scaffold()),
        GetPage(name: '/upload', page: () => Scaffold()),
      ],
    ));

    await ctrl.startProcessing();
    await tester.pumpAndSettle();

    expect(repo.lastSettingsCaught, isNotNull);
    expect(repo.lastSettingsCaught!.colorCount, equals(0));
    expect(repo.lastSettingsCaught!.paperWidthCm, equals(20.0));
    expect(repo.lastSettingsCaught!.paperHeightCm, equals(25.0));
  });

  testWidgets('Manual color passes non-zero colorCount', (WidgetTester tester) async {
    final repo = MockProcessingRepository(shouldSucceed: true, outputDir: '/out');
    final ctrl = SetupController(repository: repo);

    ctrl.imagePath.value = '/path/img.png';
    ctrl.selectedColors.value = 4; // Manual color count
    ctrl.paperWidthCm.value = 21.0;
    ctrl.paperHeightCm.value = 29.7;

    await tester.pumpWidget(GetMaterialApp(
      home: Scaffold(body: SizedBox.shrink()),
      getPages: [
        GetPage(name: '/preview', page: () => Scaffold()),
        GetPage(name: '/upload', page: () => Scaffold()),
      ],
    ));

    await ctrl.startProcessing();
    await tester.pumpAndSettle();

    expect(repo.lastSettingsCaught, isNotNull);
    expect(repo.lastSettingsCaught!.colorCount, equals(4));
  });
}
