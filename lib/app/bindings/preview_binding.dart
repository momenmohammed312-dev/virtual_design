// lib/app/bindings/preview_binding.dart

import 'package:get/get.dart';
import '../../domain/repositories/processing_repository.dart';
import '../../presentation/preview/preview_controller.dart';

class PreviewBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut(() => PreviewController(repository: Get.find<ProcessingRepository>()));
  }
}
