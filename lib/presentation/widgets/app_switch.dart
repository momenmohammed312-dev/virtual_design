// setup_page_switch_fix.dart
// Virtual Design Silk Screen Studio
//
// MED #3 FIX: activeThumbColor deprecated في Flutter 3.x
//
// هذا الملف يحتوي على:
// 1. الـ AppSwitch widget الصحيح (استبدل كل Switch في setup_page.dart به)
// 2. تعليمات find & replace لـ setup_page.dart
//
// ─────────────────────────────────────────────────────────────────────────
// FIND & REPLACE في setup_page.dart:
//
//   ❌ ابحث عن:
//       Switch(
//         value: ...,
//         onChanged: ...,
//         activeThumbColor: ...,
//         activeColor: ...,
//       )
//
//   ✅ استبدل بـ:
//       AppSwitch(
//         value: ...,
//         onChanged: ...,
//       )
//
// ─────────────────────────────────────────────────────────────────────────

import 'package:flutter/material.dart';
import '../../app/themes/app_theme.dart';

/// Switch موحّد يستخدم thumbColor + trackColor (Flutter 3.x compatible)
/// بدل activeThumbColor المنتهية الصلاحية
class AppSwitch extends StatelessWidget {
  final bool value;
  final ValueChanged<bool>? onChanged;
  final Color? activeColor;
  final bool isDisabled;

  const AppSwitch({
    super.key,
    required this.value,
    required this.onChanged,
    this.activeColor,
    this.isDisabled = false,
  });

  @override
  Widget build(BuildContext context) {
    final primary = activeColor ?? AppColors.primary;

    return Switch(
      value: value,
      onChanged: isDisabled ? null : onChanged,

      // ✅ thumbColor بدل activeThumbColor (Flutter 3.x)
      thumbColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.disabled)) return AppColors.textDisabled;
        if (states.contains(WidgetState.selected)) return primary;
        return AppColors.textMuted;
      }),

      // ✅ trackColor يشمل الحالة المختارة وغير المختارة
      trackColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.disabled)) {
          return AppColors.surface4.withAlpha((0.5 * 255).round());
        }
        if (states.contains(WidgetState.selected)) {
          return primary.withAlpha((0.4 * 255).round());
        }
        return AppColors.surface4;
      }),

      // إزالة الـ border الافتراضي
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
    );
  }
}

/// Row جاهز للاستخدام في setup_page — label + switch
class SettingsSwitchRow extends StatelessWidget {
  final String label;
  final String? subtitle;
  final bool value;
  final ValueChanged<bool>? onChanged;
  final bool isDisabled;
  final String? disabledHint; // رسالة لو disabled (مثلاً: "يتطلب Basic plan")

  const SettingsSwitchRow({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
    this.subtitle,
    this.isDisabled = false,
    this.disabledHint,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: AppTextStyles.bodyM.copyWith(
                    color: isDisabled
                        ? AppColors.textDisabled
                        : AppColors.textSecondary,
                  ),
                ),
                if (subtitle != null)
                  Text(subtitle!, style: AppTextStyles.bodyS),
                if (isDisabled && disabledHint != null)
                  Text(
                    disabledHint!,
                    style: AppTextStyles.bodyS.copyWith(
                      color: AppColors.warning,
                      fontSize: 11,
                    ),
                  ),
              ],
            ),
          ),
          AppSwitch(
            value: value,
            onChanged: onChanged,
            isDisabled: isDisabled,
          ),
        ],
      ),
    );
  }
}
