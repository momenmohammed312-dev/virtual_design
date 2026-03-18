// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'processing_settings_model.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class ProcessingSettingsModelAdapter
    extends TypeAdapter<ProcessingSettingsModel> {
  @override
  final int typeId = 0;

  @override
  ProcessingSettingsModel read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return ProcessingSettingsModel(
      colorCount: fields[0] as int,
      printFinish: fields[1] as String,
      detailLevel: fields[2] as String,
      dpi: fields[3] as double,
      strokeWidthMm: fields[4] as double,
      meshCount: fields[5] as int,
      edgeEnhancement: fields[6] as String,
      halftoneLpi: fields[7] as int?,
      halftoneDotShape: fields[8] as String?,
      halftoneAngle: fields[9] as double?,
    );
  }

  @override
  void write(BinaryWriter writer, ProcessingSettingsModel obj) {
    writer
      ..writeByte(10)
      ..writeByte(0)
      ..write(obj.colorCount)
      ..writeByte(1)
      ..write(obj.printFinish)
      ..writeByte(2)
      ..write(obj.detailLevel)
      ..writeByte(3)
      ..write(obj.dpi)
      ..writeByte(4)
      ..write(obj.strokeWidthMm)
      ..writeByte(5)
      ..write(obj.meshCount)
      ..writeByte(6)
      ..write(obj.edgeEnhancement)
      ..writeByte(7)
      ..write(obj.halftoneLpi)
      ..writeByte(8)
      ..write(obj.halftoneDotShape)
      ..writeByte(9)
      ..write(obj.halftoneAngle);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ProcessingSettingsModelAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
