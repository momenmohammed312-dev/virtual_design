// lib/domain/entities/print_project.dart

import 'processing_settings.dart';

/// Print Project entity - represents a complete printing job
class PrintProject {
  final String id;
  final String name;
  final DateTime createdAt;
  final ProcessingSettings settings;
  final List<String> filmPaths;
  final String originalImagePath;
  final ProjectStatus status;
  final String? outputDirectory;

  const PrintProject({
    required this.id,
    required this.name,
    required this.createdAt,
    required this.settings,
    required this.filmPaths,
    required this.originalImagePath,
    this.status = ProjectStatus.draft,
    this.outputDirectory,
  });

  // Business logic
  bool get isComplete => status == ProjectStatus.completed;
  int get totalFilms => filmPaths.length;

  // Validation
  List<String> validate() {
    final errors = <String>[];
    if (filmPaths.isEmpty) errors.add('No films generated');
    if (name.isEmpty) errors.add('Project name required');
    return errors;
  }

  // Copy with
  PrintProject copyWith({
    String? name,
    ProjectStatus? status,
    List<String>? filmPaths,
    String? outputDirectory,
  }) {
    return PrintProject(
      id: id,
      name: name ?? this.name,
      createdAt: createdAt,
      settings: settings,
      filmPaths: filmPaths ?? this.filmPaths,
      originalImagePath: originalImagePath,
      status: status ?? this.status,
      outputDirectory: outputDirectory ?? this.outputDirectory,
    );
  }
}

enum ProjectStatus { draft, processing, completed, error }
