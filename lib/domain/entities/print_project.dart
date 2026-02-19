// print_project.dart — Domain Entity
// Virtual Design Silk Screen Studio
//
// تمثيل مشروع الطباعة بجميع بيانات وحالاته

import 'package:virtual_design/domain/entities/processing_settings.dart';

// ─── Enum: Project Status ─────────────────────────────────────────────────────

enum ProjectStatus { draft, processing, completed, failed, archived }

// ─── Class: PrintProject ──────────────────────────────────────────────────────

class PrintProject {
  final String id;
  final String name;
  final String? imagePath;
  final ProcessingSettings settings;
  final ProjectStatus status;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final String? errorMessage;
  final int? progress; // 0-100
  final List<String> filmPaths;
  final String? outputDirectory;

  const PrintProject({
    required this.id,
    required this.name,
    this.imagePath,
    required this.settings,
    this.status = ProjectStatus.draft,
    required this.createdAt,
    this.updatedAt,
    this.errorMessage,
    this.progress,
    this.filmPaths = const [],
    this.outputDirectory,
  });

  PrintProject copyWith({
    String? id,
    String? name,
    String? imagePath,
    ProcessingSettings? settings,
    ProjectStatus? status,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? errorMessage,
    int? progress,
    List<String>? filmPaths,
    String? outputDirectory,
  }) =>
      PrintProject(
        id: id ?? this.id,
        name: name ?? this.name,
        imagePath: imagePath ?? this.imagePath,
        settings: settings ?? this.settings,
        status: status ?? this.status,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
        errorMessage: errorMessage ?? this.errorMessage,
        progress: progress ?? this.progress,
        filmPaths: filmPaths ?? this.filmPaths,
        outputDirectory: outputDirectory ?? this.outputDirectory,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'imagePath': imagePath,
        'settings': settings,
        'status': status.toString(),
        'createdAt': createdAt.toIso8601String(),
        'updatedAt': updatedAt?.toIso8601String(),
        'errorMessage': errorMessage,
        'progress': progress,
        'filmPaths': filmPaths,
        'outputDirectory': outputDirectory,
      };

  factory PrintProject.fromJson(Map<String, dynamic> json) => PrintProject(
        id: json['id'] as String,
        name: json['name'] as String,
        imagePath: json['imagePath'] as String?,
        settings: json['settings'] as ProcessingSettings,
        status: _statusFromString(json['status'] as String? ?? 'draft'),
        createdAt: DateTime.parse(json['createdAt'] as String),
        updatedAt: json['updatedAt'] != null
            ? DateTime.parse(json['updatedAt'] as String)
            : null,
        errorMessage: json['errorMessage'] as String?,
        progress: json['progress'] as int?,
        filmPaths: List<String>.from(json['filmPaths'] as List? ?? []),
        outputDirectory: json['outputDirectory'] as String?,
      );

  static ProjectStatus _statusFromString(String status) {
    switch (status) {
      case 'ProjectStatus.draft':
        return ProjectStatus.draft;
      case 'ProjectStatus.processing':
        return ProjectStatus.processing;
      case 'ProjectStatus.completed':
        return ProjectStatus.completed;
      case 'ProjectStatus.failed':
        return ProjectStatus.failed;
      case 'ProjectStatus.archived':
        return ProjectStatus.archived;
      default:
        return ProjectStatus.draft;
    }
  }
}
