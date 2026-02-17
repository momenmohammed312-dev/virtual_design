// lib/app/bindings/dashboard_binding.dart

import 'package:get/get.dart';
import '../../data/repositories/project_repository_impl.dart';
import '../../domain/repositories/project_repository.dart';
import '../../presentation/dashboard/dashboard_controller.dart';

class DashboardBinding extends Bindings {
  @override
  void dependencies() {
    // Repository
    Get.lazyPut<ProjectRepository>(() => ProjectRepositoryImpl());

    // Controller
    Get.lazyPut(
      () =>
          DashboardController(projectRepository: Get.find<ProjectRepository>()),
    );
  }
}
