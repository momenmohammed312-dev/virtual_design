// lib/app/bindings/preview_binding.dart

import 'package:get/get.dart';
import 'package:virtual_design/data/repositories/processing_repository_impl.dart';
import 'package:virtual_design/domain/repositories/processing_repository.dart';
import 'package:virtual_design/core/python_bridge/python_processor.dart';
import 'package:virtual_design/presentation/preview/preview_controller.dart';

class PreviewBinding extends Bindings {
  @override
  void dependencies() {
    // Ensure repository is registered (in case user navigates directly to preview)
    if (!Get.isRegistered<ProcessingRepository>()) {
      Get.lazyPut<ProcessingRepository>(() => ProcessingRepositoryImpl(
            processor: Get.find<PythonProcessor>(),
          ));
    }

    Get.lazyPut(
        () => PreviewController(repository: Get.find<ProcessingRepository>()));
  }
}
