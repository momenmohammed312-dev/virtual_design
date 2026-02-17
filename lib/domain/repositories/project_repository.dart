// lib/domain/repositories/project_repository.dart

import '../entities/print_project.dart';

/// Repository interface for project management
abstract class ProjectRepository {
  /// Save a project to local storage
  Future<void> saveProject(PrintProject project);

  /// Load a project by ID
  Future<PrintProject?> loadProject(String id);

  /// Get all saved projects
  Future<List<PrintProject>> getAllProjects();

  /// Delete a project
  Future<void> deleteProject(String id);

  /// Search projects by name
  Future<List<PrintProject>> searchProjects(String query);
}
