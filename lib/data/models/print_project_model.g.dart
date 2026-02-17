// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'print_project_model.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class PrintProjectModelAdapter extends TypeAdapter<PrintProjectModel> {
  @override
  final int typeId = 1;

  @override
  PrintProjectModel read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return PrintProjectModel(
      id: fields[0] as String,
      name: fields[1] as String,
      createdAt: fields[2] as DateTime,
      settings: fields[3] as ProcessingSettingsModel,
      filmPaths: (fields[4] as List).cast<String>(),
      originalImagePath: fields[5] as String,
      status: fields[6] as String,
      outputDirectory: fields[7] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, PrintProjectModel obj) {
    writer
      ..writeByte(8)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.createdAt)
      ..writeByte(3)
      ..write(obj.settings)
      ..writeByte(4)
      ..write(obj.filmPaths)
      ..writeByte(5)
      ..write(obj.originalImagePath)
      ..writeByte(6)
      ..write(obj.status)
      ..writeByte(7)
      ..write(obj.outputDirectory);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PrintProjectModelAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
