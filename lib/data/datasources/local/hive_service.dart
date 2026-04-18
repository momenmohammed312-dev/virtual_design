// lib/data/datasources/local/hive_service.dart

import 'package:hive_flutter/hive_flutter.dart';
import 'package:virtual_design/data/models/processing_settings_model.dart';
import 'package:virtual_design/data/models/print_project_model.dart';

class HiveService {
  static const String _projectsBox = 'projects';
  static const String _settingsBox = 'settings';
  static const String _lastSettingsKey = 'last_settings';

  static HiveService? _instance;
  static HiveService get instance => _instance ??= HiveService._();

  HiveService._();

  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;

    await Hive.initFlutter();

    // Register adapters
    if (!Hive.isAdapterRegistered(0)) {
      Hive.registerAdapter(ProcessingSettingsModelAdapter());
    }
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(PrintProjectModelAdapter());
    }

    try {
      await Hive.openBox<PrintProjectModel>(_projectsBox);
    } catch (e) {
      print('[HiveService] Corrupt projects box, rebuilding: $e');
      await Hive.deleteBoxFromDisk(_projectsBox);
      await Hive.openBox<PrintProjectModel>(_projectsBox);
    }

    try {
      await Hive.openBox(_settingsBox);
    } catch (e) {
      print('[HiveService] Corrupt settings box, rebuilding: $e');
      await Hive.deleteBoxFromDisk(_settingsBox);
      await Hive.openBox(_settingsBox);
    }

    _initialized = true;
  }

  Box<PrintProjectModel> get _projects =>
      Hive.box<PrintProjectModel>(_projectsBox);

  Future<void> saveProject(PrintProjectModel project) async {
    await _projects.put(project.id, project);
  }

  PrintProjectModel? loadProject(String id) => _projects.get(id);

  List<PrintProjectModel> getAllProjects() {
    return _projects.values.toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  }

  Future<void> deleteProject(String id) async => await _projects.delete(id);

  List<PrintProjectModel> searchProjects(String query) {
    final lowerQuery = query.toLowerCase();
    return _projects.values
        .where((p) => p.name.toLowerCase().contains(lowerQuery))
        .toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  }

  // For JSON storage (untyped box)
  Box<dynamic> get _settingsDynamic => Hive.box(_settingsBox);

  Future<void> saveLastSettings(ProcessingSettingsModel settings) async {
    await _settingsDynamic.put(_lastSettingsKey, settings);
  }

  ProcessingSettingsModel? loadLastSettings() =>
      _settingsDynamic.get(_lastSettingsKey);

  // New method for JSON storage
  Future<Box<dynamic>> getSettingsBox() async {
    await Hive.openBox(_settingsBox);
    return Hive.box(_settingsBox);
  }

  Future<void> clearAll() async {
    await _projects.clear();
    await _settingsDynamic.clear();
  }

  Future<void> close() async {
    await Hive.close();
    _initialized = false;
  }
}
