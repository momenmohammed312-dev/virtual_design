// lib/app/bindings/initial_binding.dart

import 'package:get/get.dart';
import '../../data/datasources/local/hive_service.dart';
import '../../core/python_bridge/python_processor.dart';
import '../../core/python_bridge/python_config.dart';
import '../../core/licensing/license_manager.dart';
import '../../core/permissions/permission_service.dart';

class InitialBinding extends Bindings {
  @override
  void dependencies() {
    // Initialize PythonConfig on app startup
    final pythonConfig = PythonConfig();
    Get.put(pythonConfig, permanent: true);

    // Initialize LicenseManager (singleton)
    Get.put(LicenseManager(), permanent: true);

    // Initialize PermissionService (singleton)
    Get.put(PermissionService(), permanent: true);

    // Initialize Hive on app startup
    Get.putAsync(() async {
      await pythonConfig.initialize();
      final hive = HiveService.instance;
      await hive.init();
      return hive;
    }, permanent: true);

    // Python Processor (singleton)
    Get.put(PythonProcessor(config: pythonConfig), permanent: true);
  }
}
