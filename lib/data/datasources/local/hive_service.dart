// lib/data/datasources/local/hive_service.dart

import 'package:hive_flutter/hive_flutter.dart';
import '../../models/processing_settings_model.dart';
import '../../models/print_project_model.dart';

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

    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(PrintProjectModelAdapter());
    }

    await Hive.openBox<PrintProjectModel>(_projectsBox);
    await Hive.openBox<ProcessingSettingsModel>(_settingsBox);

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

  Box<ProcessingSettingsModel> get _settings =>
      Hive.box<ProcessingSettingsModel>(_settingsBox);

  Future<void> saveLastSettings(ProcessingSettingsModel settings) async {
    await _settings.put(_lastSettingsKey, settings);
  }

  ProcessingSettingsModel? loadLastSettings() =>
      _settings.get(_lastSettingsKey);

  Future<void> clearAll() async {
    await _projects.clear();
    await _settings.clear();
  }

  Future<void> close() async {
    await Hive.close();
    _initialized = false;
  }
}
