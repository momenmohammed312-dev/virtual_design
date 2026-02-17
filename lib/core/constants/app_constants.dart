import 'package:flutter/material.dart';

class AppColors {
  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color darkBlue = Color(0xFF0E3182);
  static const Color accentBlue = Color(0xFF4587F9);
  static const Color lightBlue = Color(0xFFEFF6FF);
  static const Color sidebarBg = Color(0xFF0E3182);
  static const Color pageBg = Color(0xFFECECEC);
  static const Color white = Colors.white;
  static const Color textDark = Color(0xFF1F2937);
  static const Color textMedium = Color(0xFF6B7280);
  static const Color textLight = Color(0xFF9CA3AF);
  static const Color border = Color(0xFFE5E7EB);
  static const Color success = Color(0xFF10B981);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFEF4444);
  static const Color cardBg = Colors.white;
}

class AppText {
  static const String appName = 'Virtual Design';
  static const String appSubtitle = 'Silk Screen Studio';
  static const String developer = 'MO2';
  static const String version = 'v1.0.0';
}

class AppDimens {
  static const double sidebarWidth = 220;
  static const double topBarHeight = 60;
  static const double borderRadius = 8;
  static const double cardPadding = 20;
}

class AppConstants {
  static const String appTitle = 'Virtual Design – Silk Screen Studio';

  static final ThemeData lightTheme = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: AppColors.primaryBlue),
    fontFamily: 'Roboto',
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.darkBlue,
      foregroundColor: Colors.white,
      elevation: 0,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primaryBlue,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDimens.borderRadius),
        ),
      ),
    ),
  );
}

