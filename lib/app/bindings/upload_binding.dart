// lib/app/bindings/upload_binding.dart

import 'package:get/get.dart';
import '../../data/repositories/processing_repository_impl.dart';
import '../../domain/repositories/processing_repository.dart';
import '../../presentation/upload/upload_controller.dart';

class UploadBinding extends Bindings {
  @override
  void dependencies() {
    // Repository
    Get.lazyPut<ProcessingRepository>(() => ProcessingRepositoryImpl());

    // Controller
    Get.lazyPut(() => UploadController());
  }
}
