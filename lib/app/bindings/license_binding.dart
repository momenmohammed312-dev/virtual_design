/// license_binding.dart — License Module Bindings
/// Virtual Design Silk Screen Studio

library virtual_design.app.bindings.license_binding;

import 'package:get/get.dart';
import 'package:virtual_design/core/licensing/license_manager.dart';
import 'package:virtual_design/presentation/license/license_activation_controller.dart';

class LicenseBinding extends Bindings {
  @override
  void dependencies() {
    // License Manager (singleton - persistent)
    Get.put<LicenseManager>(
      LicenseManager(),
      permanent: true,
    );

    // License Activation Controller
    Get.lazyPut<LicenseActivationController>(
      () => LicenseActivationController(
        licenseManager: Get.find<LicenseManager>(),
      ),
    );
  }
}
