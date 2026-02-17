// lib/app/bindings/preview_binding.dart

import 'package:get/get.dart';
import '../../presentation/preview/preview_controller.dart';

class PreviewBinding extends Bindings {
  @override
  void dependencies() {
    // Preview Controller (no repository needed - receives result from args)
    Get.lazyPut(() => PreviewController());
  }
}
