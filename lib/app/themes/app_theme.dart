/// app_theme.dart — Single source of truth for all theming
/// Virtual Design Silk Screen Studio
///
/// MED #4 FIX: كانت قيم الـ theme معرّفة في مكانين (هنا + app_constants.dart)
/// الحل: app_theme.dart هو المصدر الوحيد — احذف من app_constants.dart أي
///       static const lightTheme أو darkTheme موجود هناك.

import 'package:flutter/material.dart';

// ─── Color Palette ────────────────────────────────────────────────────────────

class AppColors {
  AppColors._();

  // Primary
  static const Color primary        = Color(0xFF4F46E5); // Indigo
  static const Color primaryLight   = Color(0xFF6366F1);
  static const Color primaryDark    = Color(0xFF4338CA);

  // Accent
  static const Color accent         = Color(0xFF06B6D4); // Cyan
  static const Color accentLight    = Color(0xFF22D3EE);

  // Semantic
  static const Color success        = Color(0xFF4ADE80);
  static const Color warning        = Color(0xFFFACC15);
  static const Color error          = Color(0xFFF87171);
  static const Color info           = Color(0xFF60A5FA);

  // Dark Surface Hierarchy
  static const Color surface0       = Color(0xFF0A0D14); // أعمق خلفية
  static const Color surface1       = Color(0xFF0F1117); // الخلفية الرئيسية
  static const Color surface2       = Color(0xFF141929); // Cards
  static const Color surface3       = Color(0xFF1A1F2E); // Elevated cards
  static const Color surface4       = Color(0xFF1E2436); // Hover / selected

  // Borders
  static const Color border         = Color(0xFF2D3748);
  static const Color borderLight    = Color(0xFF3D4A5E);

  // Text
  static const Color textPrimary    = Color(0xFFF8FAFC);
  static const Color textSecondary  = Color(0xFFCBD5E1);
  static const Color textMuted      = Color(0xFF64748B);
  static const Color textDisabled   = Color(0xFF475569);

  // Light theme surfaces (for future light mode)
  static const Color lightBackground = Color(0xFFF8FAFC);
  static const Color lightSurface    = Color(0xFFFFFFFF);
  static const Color lightBorder     = Color(0xFFE2E8F0);
}

// ─── Typography ───────────────────────────────────────────────────────────────

class AppTextStyles {
  AppTextStyles._();

  static const TextStyle headingXL = TextStyle(
    fontSize: 28, fontWeight: FontWeight.w800, color: AppColors.textPrimary, height: 1.2,
  );
  static const TextStyle headingL = TextStyle(
    fontSize: 22, fontWeight: FontWeight.w700, color: AppColors.textPrimary, height: 1.3,
  );
  static const TextStyle headingM = TextStyle(
    fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
  );
  static const TextStyle headingS = TextStyle(
    fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
  );

  static const TextStyle bodyL = TextStyle(
    fontSize: 15, color: AppColors.textSecondary, height: 1.7,
  );
  static const TextStyle bodyM = TextStyle(
    fontSize: 14, color: AppColors.textSecondary, height: 1.65,
  );
  static const TextStyle bodyS = TextStyle(
    fontSize: 12, color: AppColors.textMuted, height: 1.6,
  );

  static const TextStyle caption = TextStyle(
    fontSize: 11, color: AppColors.textMuted,
    letterSpacing: 0.5, fontWeight: FontWeight.w500,
  );
  static const TextStyle label = TextStyle(
    fontSize: 11, color: AppColors.textMuted,
    letterSpacing: 1.2, fontWeight: FontWeight.w700,
    textBaseline: TextBaseline.alphabetic,
  );

  static const TextStyle mono = TextStyle(
    fontFamily: 'monospace', fontSize: 12.5,
    color: AppColors.textSecondary, height: 1.6,
  );
}

// ─── Border Radius ────────────────────────────────────────────────────────────

class AppRadius {
  AppRadius._();
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double full = 999;
}

// ─── Spacing ──────────────────────────────────────────────────────────────────

class AppSpacing {
  AppSpacing._();
  static const double xs  = 4;
  static const double sm  = 8;
  static const double md  = 16;
  static const double lg  = 24;
  static const double xl  = 32;
  static const double xxl = 48;
}

// ─── Theme ────────────────────────────────────────────────────────────────────

class AppTheme {
  AppTheme._();

  // ── Dark Theme (الأساسي) ────────────────────────────────────────────────────
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary:          AppColors.primary,
        onPrimary:        Colors.white,
        secondary:        AppColors.accent,
        onSecondary:      Colors.white,
        error:            AppColors.error,
        surface:          AppColors.surface1,
        onSurface:        AppColors.textPrimary,
      ),
      scaffoldBackgroundColor: AppColors.surface1,
      fontFamily: 'Cairo',

      // ── AppBar ──────────────────────────────────────────────────────────────
      appBarTheme: const AppBarTheme(
        backgroundColor:  AppColors.surface2,
        foregroundColor:  AppColors.textPrimary,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        titleTextStyle: AppTextStyles.headingM,
        iconTheme: IconThemeData(color: AppColors.textSecondary),
      ),

      // ── Card ────────────────────────────────────────────────────────────────
      cardTheme: CardThemeData(
        color:        AppColors.surface3,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          side: const BorderSide(color: AppColors.border),
        ),
        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      ),

      // ── ElevatedButton ──────────────────────────────────────────────────────
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor:  AppColors.primary,
          foregroundColor:  Colors.white,
          disabledBackgroundColor: AppColors.border,
          disabledForegroundColor: AppColors.textDisabled,
          elevation: 0,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg, vertical: AppSpacing.md,
          ),
          textStyle: const TextStyle(
            fontSize: 14, fontWeight: FontWeight.w600, fontFamily: 'Cairo',
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
        ),
      ),

      // ── OutlinedButton ──────────────────────────────────────────────────────
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.textSecondary,
          side: const BorderSide(color: AppColors.border),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg, vertical: AppSpacing.md,
          ),
          textStyle: const TextStyle(
            fontSize: 14, fontWeight: FontWeight.w500, fontFamily: 'Cairo',
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
        ),
      ),

      // ── TextButton ──────────────────────────────────────────────────────────
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          textStyle: const TextStyle(
            fontSize: 14, fontWeight: FontWeight.w500, fontFamily: 'Cairo',
          ),
        ),
      ),

      // ── InputDecoration ─────────────────────────────────────────────────────
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface2,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md, vertical: AppSpacing.sm + 4,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        hintStyle: AppTextStyles.bodyM.copyWith(color: AppColors.textDisabled),
        labelStyle: AppTextStyles.bodyS,
        errorStyle: AppTextStyles.bodyS.copyWith(color: AppColors.error),
      ),

      // ── Switch (MED #3 FIX: thumbColor بدل activeThumbColor deprecated) ────
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return AppColors.primary;
          return AppColors.textMuted;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary.withOpacity(0.4);
          }
          return AppColors.surface4;
        }),
        trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
      ),

      // ── Slider ──────────────────────────────────────────────────────────────
      sliderTheme: SliderThemeData(
        activeTrackColor:   AppColors.primary,
        inactiveTrackColor: AppColors.surface4,
        thumbColor:         AppColors.primary,
        overlayColor:       AppColors.primary.withOpacity(0.15),
        valueIndicatorColor: AppColors.surface3,
        valueIndicatorTextStyle: AppTextStyles.bodyS.copyWith(
          color: AppColors.textPrimary,
        ),
      ),

      // ── Chip ────────────────────────────────────────────────────────────────
      chipTheme: ChipThemeData(
        backgroundColor:       AppColors.surface3,
        selectedColor:         AppColors.primary.withOpacity(0.2),
        disabledColor:         AppColors.surface2,
        labelStyle:            AppTextStyles.bodyS,
        side:                  const BorderSide(color: AppColors.border),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.full),
        ),
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
      ),

      // ── Divider ─────────────────────────────────────────────────────────────
      dividerTheme: const DividerThemeData(
        color: AppColors.border, thickness: 1, space: 1,
      ),

      // ── ProgressIndicator ───────────────────────────────────────────────────
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.primary,
        linearTrackColor: AppColors.surface4,
      ),

      // ── SnackBar ────────────────────────────────────────────────────────────
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.surface3,
        contentTextStyle: AppTextStyles.bodyM,
        actionTextColor: AppColors.primary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        behavior: SnackBarBehavior.floating,
      ),

      // ── Dialog ──────────────────────────────────────────────────────────────
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surface3,
        surfaceTintColor: Colors.transparent,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
        titleTextStyle: AppTextStyles.headingM,
        contentTextStyle: AppTextStyles.bodyM,
      ),

      // ── Bottom Sheet ────────────────────────────────────────────────────────
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.surface3,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadius.xl),
          ),
        ),
      ),

      // ── Tooltip ─────────────────────────────────────────────────────────────
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: AppColors.surface4,
          borderRadius: BorderRadius.circular(AppRadius.xs),
          border: Border.all(color: AppColors.border),
        ),
        textStyle: AppTextStyles.bodyS,
      ),
    );
  }

  // ── Light Theme (Optional — للمستقبل) ───────────────────────────────────────
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: ColorScheme.light(
        primary:   AppColors.primary,
        secondary: AppColors.accent,
        surface:   AppColors.lightBackground,
        error:     AppColors.error,
      ),
      scaffoldBackgroundColor: AppColors.lightBackground,
      fontFamily: 'Cairo',
      cardTheme: CardThemeData(
        color: AppColors.lightSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          side: const BorderSide(color: AppColors.lightBorder),
        ),
      ),
      // ── Switch (نفس الإصلاح في Light Mode) ─────────────────────────────────
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return AppColors.primary;
          return Colors.grey.shade400;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppColors.primary.withOpacity(0.3);
          }
          return Colors.grey.shade300;
        }),
        trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
      ),
    );
  }
}
