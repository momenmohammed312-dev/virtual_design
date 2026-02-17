class ProcessResultModel {
  final bool success;
  final String stdout;
  final String stderr;

  ProcessResultModel({required this.success, this.stdout = '', this.stderr = ''});
}
