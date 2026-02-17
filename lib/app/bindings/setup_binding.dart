// lib/app/bindings/setup_binding.dart

import 'package:get/get.dart';
import '../../data/repositories/processing_repository_impl.dart';
import '../../domain/repositories/processing_repository.dart';
import '../../presentation/setup/setup_controller.dart';

class SetupBinding extends Bindings {
  @override
  void dependencies() {
    // Repository
    Get.lazyPut<ProcessingRepository>(() => ProcessingRepositoryImpl());

    // Controller
    Get.lazyPut(
      () => SetupController(repository: Get.find<ProcessingRepository>()),
    );
  }
}
