// lib/data/repositories/project_repository_impl.dart

import '../../domain/repositories/project_repository.dart';
import '../../domain/entities/print_project.dart';
import '../datasources/local/hive_service.dart';
import '../models/print_project_model.dart';

class ProjectRepositoryImpl implements ProjectRepository {
  final HiveService _hiveService;

  ProjectRepositoryImpl({HiveService? hiveService})
    : _hiveService = hiveService ?? HiveService.instance;

  @override
  Future<void> saveProject(PrintProject project) async {
    final model = PrintProjectModel.fromEntity(project);
    await _hiveService.saveProject(model);
  }

  @override
  Future<PrintProject?> loadProject(String id) async {
    final model = _hiveService.loadProject(id);
    return model?.toEntity();
  }

  @override
  Future<List<PrintProject>> getAllProjects() async {
    final models = _hiveService.getAllProjects();
    return models.map((m) => m.toEntity()).toList();
  }

  @override
  Future<void> deleteProject(String id) async {
    await _hiveService.deleteProject(id);
  }

  @override
  Future<List<PrintProject>> searchProjects(String query) async {
    final models = _hiveService.searchProjects(query);
    return models.map((m) => m.toEntity()).toList();
  }
}
