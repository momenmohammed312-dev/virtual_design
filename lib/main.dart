// lib/main.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'package:virtual_design/presentation/splash/splash_screen.dart';
import 'package:virtual_design/presentation/dashboard/dashboard.dart';
import 'package:virtual_design/presentation/upload/upload_page.dart';
import 'package:virtual_design/presentation/setup/setup_page.dart';
import 'package:virtual_design/presentation/preview/preview_page.dart';

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
      title: 'Virtual Design – Silk Screen Studio',

      // ── Theme ──────────────────────────────────────────
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1564A5),
          brightness: Brightness.light,
        ),
        fontFamily: 'Roboto',
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0E3182),
          foregroundColor: Colors.white,
          elevation: 0,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF1564A5),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
      ),

      // ── Start with Splash ───────────────────────────────
      initialRoute: '/splash',

      // ── Routes ─────────────────────────────────────────
      getPages: [
        GetPage(
          name: '/splash',
          page: () => const SplashScreen(),
          transition: Transition.fadeIn,
        ),
        GetPage(
          name: '/dashboard',
          page: () => DashboardScreen(),
          transition: Transition.fadeIn,
          transitionDuration: const Duration(milliseconds: 500),
        ),
        GetPage(
          name: '/upload',
          page: () => const UploadPage(),
          transition: Transition.rightToLeft,
        ),
        GetPage(
          name: '/setup',
          page: () => const SetupPage(),
          transition: Transition.rightToLeft,
        ),
        GetPage(
          name: '/preview',
          page: () => const PreviewPage(),
          transition: Transition.rightToLeft,
        ),
      ],
    );
  }
}
