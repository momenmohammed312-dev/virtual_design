// lib/main.dart

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:get/get.dart';
import 'package:virtual_design/app/routes/app_pages.dart';
import 'package:virtual_design/app/routes/app_routes.dart';
import 'package:virtual_design/app/themes/app_theme.dart';
import 'package:virtual_design/app/bindings/initial_binding.dart';
import 'package:virtual_design/l10n/app_localizations.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize app-wide dependencies
  InitialBinding().dependencies();

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Virtual Designer',
      theme: AppTheme.lightTheme,
      initialRoute: AppRoutes.splash,
      getPages: AppPages.routes,
      // Localization support
      localizationsDelegates: [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      // Fallback locale
      fallbackLocale: const Locale('en'),
    );
  }
}
