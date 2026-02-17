import 'dart:convert';
import 'dart:io';

import 'python_config.dart';
import 'process_result.dart';

class PythonProcessor {
  final PythonConfig config;

  PythonProcessor({this.config = const PythonConfig()});

  Future<ProcessResultModel> runScript(List<String> args,
      {String? workingDirectory}) async {
    try {
      final result = await Process.run(config.pythonCommand, args,
          workingDirectory: workingDirectory, runInShell: true);

      final out = result.stdout is String
          ? result.stdout as String
          : const Utf8Decoder().convert(result.stdout as List<int>);

      final err = result.stderr is String
          ? result.stderr as String
          : const Utf8Decoder().convert(result.stderr as List<int>);

      return ProcessResultModel(
        success: result.exitCode == 0,
        stdout: out,
        stderr: err,
      );
    } catch (e) {
      return ProcessResultModel(success: false, stderr: e.toString());
    }
  }
}
