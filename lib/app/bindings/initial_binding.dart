// lib/app/bindings/initial_binding.dart

import 'package:get/get.dart';
import '../../data/datasources/local/hive_service.dart';
import '../../core/python_bridge/python_processor.dart';

class InitialBinding extends Bindings {
  @override
  void dependencies() {
    // Initialize Hive on app startup
    Get.putAsync(() async {
      final hive = HiveService.instance;
      await hive.init();
      return hive;
    }, permanent: true);

    // Python Processor (singleton)
    Get.put(PythonProcessor(), permanent: true);
  }
}
