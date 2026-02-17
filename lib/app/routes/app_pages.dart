// lib/app/routes/app_pages.dart

import 'package:get/get.dart';
import '../../presentation/splash/splash_screen.dart';
import '../../presentation/dashboard/dashboard.dart';
import '../../presentation/upload/upload_page.dart';
import '../../presentation/setup/setup_page.dart';
import '../../presentation/preview/preview_page.dart';
import '../bindings/dashboard_binding.dart';
import '../bindings/upload_binding.dart';
import '../bindings/setup_binding.dart';
import '../bindings/preview_binding.dart';
import 'app_routes.dart';

class AppPages {
  static final routes = [
    GetPage(
      name: AppRoutes.splash,
      page: () => const SplashScreen(),
      transition: Transition.fadeIn,
    ),
    GetPage(
      name: AppRoutes.dashboard,
      page: () => const DashboardScreen(),
      binding: DashboardBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 500),
    ),
    GetPage(
      name: AppRoutes.upload,
      page: () => const UploadPage(),
      binding: UploadBinding(),
      transition: Transition.rightToLeft,
    ),
    GetPage(
      name: AppRoutes.setup,
      page: () => const SetupPage(),
      binding: SetupBinding(),
      transition: Transition.rightToLeft,
    ),
    GetPage(
      name: AppRoutes.preview,
      page: () => const PreviewPage(),
      binding: PreviewBinding(),
      transition: Transition.rightToLeft,
    ),
  ];
}
