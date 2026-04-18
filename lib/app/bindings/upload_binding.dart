// lib/app/bindings/upload_binding.dart

import 'package:get/get.dart';
import 'package:virtual_design/data/repositories/processing_repository_impl.dart';
import 'package:virtual_design/domain/repositories/processing_repository.dart';
import 'package:virtual_design/core/python_bridge/python_processor.dart';
import 'package:virtual_design/presentation/upload/upload_controller.dart';

class UploadBinding extends Bindings {
  @override
  void dependencies() {
    // Repository
    Get.lazyPut<ProcessingRepository>(() => ProcessingRepositoryImpl(
          processor: Get.find<PythonProcessor>(),
        ));

    // Controller
    Get.lazyPut(() => UploadController());
  }
}
