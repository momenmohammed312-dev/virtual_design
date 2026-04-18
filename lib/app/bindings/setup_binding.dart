// lib/app/bindings/setup_binding.dart

import 'package:get/get.dart';
import 'package:virtual_design/data/repositories/processing_repository_impl.dart';
import 'package:virtual_design/domain/repositories/processing_repository.dart';
import 'package:virtual_design/core/python_bridge/python_processor.dart';
import 'package:virtual_design/presentation/setup/setup_controller.dart';

class SetupBinding extends Bindings {
  @override
  void dependencies() {
    // Repository
    Get.lazyPut<ProcessingRepository>(() => ProcessingRepositoryImpl(
          processor: Get.find<PythonProcessor>(),
        ));

    // Controller - No longer permanent to ensure fresh state on new jobs.
    // Hive already persists settings if needed.
    Get.put(
      SetupController(repository: Get.find<ProcessingRepository>()),
    );
  }
}
