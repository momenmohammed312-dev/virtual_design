// lib/app/routes/app_pages.dart

import 'package:get/get.dart';
import 'package:virtual_design/presentation/splash/splash_screen.dart';
import 'package:virtual_design/presentation/dashboard/dashboard.dart';
import 'package:virtual_design/presentation/upload/upload_page.dart';
import 'package:virtual_design/presentation/setup/setup_page.dart';
import 'package:virtual_design/presentation/preview/preview_page.dart';
import 'package:virtual_design/presentation/print_type/select_print_type_screen.dart';
import 'package:virtual_design/presentation/settings/settings_page.dart';
import 'package:virtual_design/presentation/users/users_page.dart';
import 'package:virtual_design/presentation/files/files_page.dart';
import 'package:virtual_design/presentation/error/error_page.dart';
import 'package:virtual_design/app/bindings/dashboard_binding.dart';
import 'package:virtual_design/app/bindings/upload_binding.dart';
import 'package:virtual_design/app/bindings/setup_binding.dart';
import 'package:virtual_design/app/bindings/preview_binding.dart';
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
    GetPage(
      name: AppRoutes.selectPrintType,
      page: () => const SelectPrintTypeScreen(),
      transition: Transition.rightToLeft,
    ),
    GetPage(
      name: AppRoutes.settings,
      page: () => const SettingsPage(),
      transition: Transition.rightToLeft,
    ),
    GetPage(
      name: AppRoutes.users,
      page: () => const UsersPage(),
      transition: Transition.rightToLeft,
    ),
    GetPage(
      name: AppRoutes.files,
      page: () => const FilesPage(),
      transition: Transition.rightToLeft,
    ),
    GetPage(
      name: AppRoutes.error,
      page: () => const ErrorPage(),
      transition: Transition.fadeIn,
    ),
  ];
}
