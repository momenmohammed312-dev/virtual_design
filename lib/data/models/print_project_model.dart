// lib/data/models/print_project_model.dart

import 'package:hive/hive.dart';
import '../../domain/entities/print_project.dart';
import 'processing_settings_model.dart';

part 'print_project_model.g.dart';

@HiveType(typeId: 1)
class PrintProjectModel extends HiveObject {
  @HiveField(0)
  final String id;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final DateTime createdAt;

  @HiveField(3)
  final ProcessingSettingsModel settings;

  @HiveField(4)
  final List<String> filmPaths;

  @HiveField(5)
  final String originalImagePath;

  @HiveField(6)
  final String status;

  @HiveField(7)
  final String? outputDirectory;

  PrintProjectModel({
    required this.id,
    required this.name,
    required this.createdAt,
    required this.settings,
    required this.filmPaths,
    required this.originalImagePath,
    required this.status,
    this.outputDirectory,
  });

  factory PrintProjectModel.fromEntity(PrintProject entity) {
    return PrintProjectModel(
      id: entity.id,
      name: entity.name,
      createdAt: entity.createdAt,
      settings: ProcessingSettingsModel.fromEntity(entity.settings),
      filmPaths: entity.filmPaths,
      originalImagePath: entity.originalImagePath,
      status: entity.status.name,
      outputDirectory: entity.outputDirectory,
    );
  }

  PrintProject toEntity() {
    final statusEnum = ProjectStatus.values.firstWhere(
      (e) => e.name == status,
      orElse: () => ProjectStatus.draft,
    );

    return PrintProject(
      id: id,
      name: name,
      createdAt: createdAt,
      settings: settings.toEntity(),
      filmPaths: filmPaths,
      originalImagePath: originalImagePath,
      status: statusEnum,
      outputDirectory: outputDirectory,
    );
  }
}
