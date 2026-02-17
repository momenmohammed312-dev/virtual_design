// lib/main.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'core/constants/app_constants.dart';
import 'presentation/splash/splash_screen.dart';
import 'presentation/dashboard/dashboard.dart';
import 'presentation/upload/upload_page.dart';
import 'presentation/setup/setup_page.dart';
import 'presentation/preview/preview_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      debugShowCheckedModeBanner: false,
      title: AppConstants.appTitle,
      theme: AppConstants.lightTheme,
      initialRoute: '/splash',
      getPages: [
        GetPage(name: '/splash', page: () => const SplashScreen()),
        GetPage(name: '/dashboard', page: () => const DashboardScreen()),
        GetPage(name: '/upload', page: () => const UploadPage()),
        GetPage(name: '/setup', page: () => const SetupPage()),
        GetPage(name: '/preview', page: () => const PreviewPage()),
      ],
    );
  }
}
