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

    // Initialize Hive and Python on app startup, then register PythonProcessor
    Get.putAsync(() async {
      final initResult = await pythonConfig.initialize();

      final hive = HiveService.instance;
      await hive.init();

      // Register PythonProcessor after PythonConfig has been initialized
      // (allows UI to react to python availability via pythonConfig.initialize())
      Get.put(PythonProcessor(config: pythonConfig), permanent: true);

      return hive;
    }, permanent: true);
  }
}
