// app_theme.dart - Single source of truth for all theming
// Virtual Designer - Screen Printing Studio
//
// MED #4 FIX: Theme values were defined in two places (here + app_constants.dart)
// Solution: app_theme.dart is the single source - remove from app_constants.dart

import 'package:flutter/material.dart';

// --- Color Palette -----------------------------------------------------------

class AppColors {
  AppColors._();

  // Primary
  static const Color primary = Color(0xFF1564A5);
  static const Color primaryDark = Color(0xFF0E3182);
  static const Color primaryLight = Color(0xFF4A90D9);

  // Surfaces
  static const Color background = Color(0xFF0F172A);
  static const Color surface1 = Color(0xFF1E293B);
  static const Color surface2 = Color(0xFF334155);
  static const Color surface3 = Color(0xFF475569);
  static const Color surface4 = Color(0xFF64748B);

  // Text
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFFCBD5E1);
  static const Color textMuted = Color(0xFF64748B);
  static const Color textDisabled = Color(0xFF475569);

  // Light theme surfaces (for future light mode)
  static const Color lightBackground = Color(0xFFF8FAFC);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightBorder = Color(0xFFE2E8F0);

  static const Color border = Color(0xFF334155);
}

// --- Typography --------------------------------------------------------------

class AppTextStyles {
  AppTextStyles._();

  static const TextStyle headingXL = TextStyle(
    fontSize: 32,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
  );

  static const TextStyle headingL = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
  );

  static const TextStyle headingM = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  static const TextStyle headingS = TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  static const TextStyle bodyL = TextStyle(
    fontSize: 16,
    color: AppColors.textPrimary,
  );

  static const TextStyle bodyM = TextStyle(
    fontSize: 14,
    color: AppColors.textSecondary,
  );

  static const TextStyle bodyS = TextStyle(
    fontSize: 12,
    color: AppColors.textMuted,
  );

  static const TextStyle caption = TextStyle(
    fontSize: 11,
    color: AppColors.textMuted,
    letterSpacing: 0.5,
  );
}

// --- Border Radius -----------------------------------------------------------

class AppRadius {
  AppRadius._();
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;
}

// --- Spacing -----------------------------------------------------------------

class AppSpacing {
  AppSpacing._();
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;
}

// --- Theme -------------------------------------------------------------------

class AppTheme {
  AppTheme._();

  // --- Dark Theme (Primary) --------------------------------------------------
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.primary,
        secondary: AppColors.primaryLight,
        surface: AppColors.surface1,
        onPrimary: Colors.white,
        onSurface: AppColors.textPrimary,
      ),
      scaffoldBackgroundColor: AppColors.background,
      fontFamily: 'Cairo',

      // --- AppBar --------------------------------------------------------------
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.surface2,
        foregroundColor: AppColors.textPrimary,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        titleTextStyle: AppTextStyles.headingM,
        iconTheme: IconThemeData(color: AppColors.textSecondary),
      ),

      // --- Card ----------------------------------------------------------------
      cardTheme: CardThemeData(
        color: AppColors.surface3,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          side: const BorderSide(color: AppColors.border),
        ),
      ),

      // --- ElevatedButton ------------------------------------------------------
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
        ),
      ),

      // --- OutlinedButton ------------------------------------------------------
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.textSecondary,
          side: const BorderSide(color: AppColors.border),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
        ),
      ),

      // --- TextButton ----------------------------------------------------------
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      // --- InputDecoration -----------------------------------------------------
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface2,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: Colors.red, width: 1),
        ),
        hintStyle: TextStyle(color: AppColors.textMuted.withAlpha(128)),
      ),

      // --- Switch (MED #3 FIX: thumbColor instead of deprecated activeThumbColor)
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return AppColors.primary;
          return AppColors.textMuted;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary.withAlpha(77);
          }
          return AppColors.surface3;
        }),
      ),

      // --- Slider --------------------------------------------------------------
      sliderTheme: SliderThemeData(
        activeTrackColor: AppColors.primary,
        inactiveTrackColor: AppColors.surface4,
        thumbColor: AppColors.primary,
        overlayColor: AppColors.primary.withAlpha(26),
        valueIndicatorColor: AppColors.primary,
      ),

      // --- Chip ----------------------------------------------------------------
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surface3,
        selectedColor: AppColors.primary.withAlpha(51),
        disabledColor: AppColors.surface2,
        labelStyle: AppTextStyles.bodyM,
        secondaryLabelStyle: AppTextStyles.bodyS,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
      ),

      // --- Divider -------------------------------------------------------------
      dividerTheme: const DividerThemeData(
        color: AppColors.border,
        thickness: 1,
        space: 1,
      ),

      // --- ProgressIndicator ---------------------------------------------------
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.primary,
        linearTrackColor: AppColors.surface4,
      ),

      // --- SnackBar ------------------------------------------------------------
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.surface3,
        contentTextStyle: AppTextStyles.bodyM,
        actionTextColor: AppColors.primary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        behavior: SnackBarBehavior.floating,
      ),

      // --- Dialog --------------------------------------------------------------
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surface2,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
      ),

      // --- BottomSheet ---------------------------------------------------------
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: AppColors.surface2,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius:
              BorderRadius.vertical(top: Radius.circular(AppRadius.lg)),
        ),
      ),
    );
  }

  // --- Light Theme -----------------------------------------------------------
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: const ColorScheme.light(
        primary: AppColors.primary,
        secondary: AppColors.primaryLight,
        surface: AppColors.lightSurface,
        onPrimary: Colors.white,
        onSurface: Colors.black,
      ),
      scaffoldBackgroundColor: AppColors.lightBackground,
      fontFamily: 'Cairo',
    );
  }
}
