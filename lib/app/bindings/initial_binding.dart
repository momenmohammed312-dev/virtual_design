// lib/app/bindings/initial_binding.dart

import 'package:get/get.dart';
import 'package:virtual_design/data/datasources/local/hive_service.dart';
import 'package:virtual_design/core/python_bridge/python_processor.dart';
import 'package:virtual_design/core/python_bridge/python_config.dart';
import 'package:virtual_design/core/licensing/license_manager.dart';
import 'package:virtual_design/core/permissions/permission_service.dart';
import 'package:virtual_design/core/mobile_ai/mobile_ai_service.dart';
import 'package:virtual_design/core/server/server_connector.dart';

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

    // ── Mobile AI (TFLite — gracefully degrades if models absent) ──────────
    final mobileAI = MobileAIService();
    Get.put(mobileAI, permanent: true);

    // ── Server Connector (auto-detects PC server every 30 s) ───────────────
    final connector = ServerConnector();
    Get.put(connector, permanent: true);

    // Initialize Hive and Python on app startup, then register PythonProcessor
    Get.putAsync(() async {
      await pythonConfig.initialize();

      final hive = HiveService.instance;
      await hive.init();

      // Start model loading in background after Hive is ready
      mobileAI.initialize();

      // Start pinging for PC server
      connector.startAutoDetect();

      // Register PythonProcessor after PythonConfig has been initialized
      Get.put(PythonProcessor(config: pythonConfig), permanent: true);

      return hive;
    }, permanent: true);
  }
}
