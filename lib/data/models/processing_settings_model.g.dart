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
      printType: fields[0] as String,
      colorCount: fields[1] as int,
      detailLevel: fields[2] as String,
      printFinish: fields[3] as String,
      strokeWidthMm: fields[4] as double,
      paperSize: fields[5] as String,
      copies: fields[6] as int,
      dpi: fields[7] as double,
      fabricType: fields[8] as String?,
      autoUpscale: fields[9] as bool,
      removeBackground: fields[10] as bool,
      edgeEnhancement: fields[11] as bool,
      colorCorrection: fields[12] as bool,
      halftoneLpi: fields[13] as int?,
      halftoneDotShape: fields[14] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, ProcessingSettingsModel obj) {
    writer
      ..writeByte(15)
      ..writeByte(0)
      ..write(obj.printType)
      ..writeByte(1)
      ..write(obj.colorCount)
      ..writeByte(2)
      ..write(obj.detailLevel)
      ..writeByte(3)
      ..write(obj.printFinish)
      ..writeByte(4)
      ..write(obj.strokeWidthMm)
      ..writeByte(5)
      ..write(obj.paperSize)
      ..writeByte(6)
      ..write(obj.copies)
      ..writeByte(7)
      ..write(obj.dpi)
      ..writeByte(8)
      ..write(obj.fabricType)
      ..writeByte(9)
      ..write(obj.autoUpscale)
      ..writeByte(10)
      ..write(obj.removeBackground)
      ..writeByte(11)
      ..write(obj.edgeEnhancement)
      ..writeByte(12)
      ..write(obj.colorCorrection)
      ..writeByte(13)
      ..write(obj.halftoneLpi)
      ..writeByte(14)
      ..write(obj.halftoneDotShape);
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
