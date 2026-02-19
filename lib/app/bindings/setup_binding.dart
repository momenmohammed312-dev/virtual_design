// lib/app/bindings/setup_binding.dart

import 'package:get/get.dart';
import '../../data/repositories/processing_repository_impl.dart';
import '../../domain/repositories/processing_repository.dart';
import '../../core/python_bridge/python_processor.dart';
import '../../presentation/setup/setup_controller.dart';

class SetupBinding extends Bindings {
  @override
  void dependencies() {
    // Repository
    Get.lazyPut<ProcessingRepository>(() => ProcessingRepositoryImpl(
      processor: Get.find<PythonProcessor>(),
    ));

    // Controller
    Get.lazyPut(
      () => SetupController(repository: Get.find<ProcessingRepository>()),
    );
  }
}
