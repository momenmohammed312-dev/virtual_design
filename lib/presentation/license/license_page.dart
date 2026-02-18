/// license_page.dart — License Activation Screen
/// Virtual Design Silk Screen Studio
///
/// شاشة تفعيل الترخيص — كانت موجودة في الـ routes بدون محتوى

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'license_controller.dart';
import '../../app/themes/app_theme.dart';
import '../../core/licensing/license_service.dart';

class LicensePage extends StatelessWidget {
  const LicensePage({super.key});

  @override
  Widget build(BuildContext context) {
    final ctrl = Get.find<LicenseController>();
    return Scaffold(
      backgroundColor: AppColors.surface1,
      appBar: AppBar(
        title: const Text('تفعيل الترخيص'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Get.back(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // ── Header ────────────────────────────────────────────────
                _Header(),
                const SizedBox(height: AppSpacing.xl),

                // ── Current License Card ──────────────────────────────────
                Obx(() => ctrl.hasActiveLicense
                    ? _ActiveLicenseCard(ctrl: ctrl)
                    : const _NoLicenseCard()),
                const SizedBox(height: AppSpacing.xl),

                // ── Activation Form ───────────────────────────────────────
                _ActivationForm(ctrl: ctrl),
                const SizedBox(height: AppSpacing.xl),

                // ── Tier Comparison ───────────────────────────────────────
                _TierComparison(),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Header ──────────────────────────────────────────────────────────────────

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 72, height: 72,
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.15),
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(color: AppColors.primary.withOpacity(0.3)),
          ),
          child: const Icon(Icons.workspace_premium, size: 36, color: AppColors.primary),
        ),
        const SizedBox(height: AppSpacing.md),
        const Text('تفعيل ترخيصك', style: AppTextStyles.headingL),
        const SizedBox(height: 6),
        const Text(
          'أدخل مفتاح الترخيص الذي وصلك على بريدك الإلكتروني',
          style: AppTextStyles.bodyM,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

// ─── Active License Card ──────────────────────────────────────────────────────

class _ActiveLicenseCard extends StatelessWidget {
  final LicenseController ctrl;
  const _ActiveLicenseCard({required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final info = ctrl.licenseInfo.value;
      if (info == null) return const SizedBox.shrink();

      final isExpiringSoon = info.isExpiringSoon;
      final color = isExpiringSoon ? AppColors.warning : AppColors.success;

      return Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(
                isExpiringSoon ? Icons.warning_amber : Icons.verified,
                color: color, size: 18,
              ),
              const SizedBox(width: 8),
              Text(
                isExpiringSoon ? 'الترخيص ينتهي قريباً' : 'ترخيص نشط',
                style: TextStyle(color: color, fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(AppRadius.full),
                ),
                child: Text(
                  info.tier.displayName,
                  style: TextStyle(
                    color: color, fontSize: 11, fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ]),
            const SizedBox(height: AppSpacing.sm),
            _InfoRow(label: 'البريد', value: info.email),
            _InfoRow(
              label: 'تنتهي في',
              value: '${info.daysRemaining} يوم '
                  '(${_formatDate(info.expiryDate)})',
            ),
            _InfoRow(label: 'المشاريع المتبقية',
              value: ctrl.remainingProjects == -1
                  ? 'غير محدود'
                  : '${ctrl.remainingProjects}',
            ),
            const SizedBox(height: AppSpacing.sm),
            TextButton(
              onPressed: () => ctrl.deactivate(),
              child: const Text(
                'إلغاء الترخيص',
                style: TextStyle(color: AppColors.error, fontSize: 12),
              ),
            ),
          ],
        ),
      );
    });
  }

  String _formatDate(DateTime d) => '${d.day}/${d.month}/${d.year}';
}

class _InfoRow extends StatelessWidget {
  final String label, value;
  const _InfoRow({required this.label, required this.value});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(children: [
        Text('$label: ', style: AppTextStyles.bodyS),
        Text(value, style: AppTextStyles.bodyS.copyWith(
          color: AppColors.textSecondary,
        )),
      ]),
    );
  }
}

// ─── No License Card ──────────────────────────────────────────────────────────

class _NoLicenseCard extends StatelessWidget {
  const _NoLicenseCard();
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface3,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(children: [
        const Icon(Icons.info_outline, color: AppColors.textMuted, size: 18),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            'أنت على الـ Free plan — 5 مشاريع/شهر، 2 ألوان فقط.',
            style: AppTextStyles.bodyS,
          ),
        ),
      ]),
    );
  }
}

// ─── Activation Form ──────────────────────────────────────────────────────────

class _ActivationForm extends StatelessWidget {
  final LicenseController ctrl;
  const _ActivationForm({required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.surface3,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('تفعيل مفتاح جديد', style: AppTextStyles.headingS),
          const SizedBox(height: AppSpacing.md),

          // Input
          TextField(
            controller: ctrl.keyController,
            style: AppTextStyles.mono.copyWith(fontSize: 13),
            textDirection: TextDirection.ltr,
            decoration: const InputDecoration(
              hintText: 'xxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx',
              prefixIcon: Icon(Icons.key_outlined, size: 18, color: AppColors.textMuted),
            ),
            onChanged: (_) => ctrl.clearError(),
          ),

          // Error
          Obx(() => ctrl.errorMessage.value.isNotEmpty
              ? Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Row(children: [
                    const Icon(Icons.error_outline, size: 14, color: AppColors.error),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        ctrl.errorMessage.value,
                        style: AppTextStyles.bodyS.copyWith(color: AppColors.error),
                      ),
                    ),
                  ]),
                )
              : const SizedBox.shrink()),

          // Success
          Obx(() => ctrl.successMessage.value.isNotEmpty
              ? Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Row(children: [
                    const Icon(Icons.check_circle_outline, size: 14, color: AppColors.success),
                    const SizedBox(width: 6),
                    Text(
                      ctrl.successMessage.value,
                      style: AppTextStyles.bodyS.copyWith(color: AppColors.success),
                    ),
                  ]),
                )
              : const SizedBox.shrink()),

          const SizedBox(height: AppSpacing.md),

          // Button
          Obx(() => ElevatedButton(
            onPressed: ctrl.isLoading.value ? null : ctrl.activate,
            child: ctrl.isLoading.value
                ? const SizedBox(
                    height: 18, width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Text('تفعيل الترخيص'),
          )),

          const SizedBox(height: AppSpacing.sm),
          Center(
            child: TextButton(
              onPressed: () => _showHelpDialog(context),
              child: const Text(
                'كيف أحصل على مفتاح ترخيص؟',
                style: TextStyle(fontSize: 12, color: AppColors.textMuted),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showHelpDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('الحصول على ترخيص'),
        content: const Text(
          'يمكنك شراء ترخيص من موقعنا الرسمي.\n'
          'بعد الشراء ستصلك مفتاح الترخيص على بريدك الإلكتروني.\n\n'
          'إذا فقدت المفتاح تواصل معنا على support@virtualdesign.app',
        ),
        actions: [
          TextButton(onPressed: () => Get.back(), child: const Text('حسناً')),
        ],
      ),
    );
  }
}

// ─── Tier Comparison ──────────────────────────────────────────────────────────

class _TierComparison extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('مقارنة الخطط', style: AppTextStyles.headingS),
        const SizedBox(height: AppSpacing.md),
        Row(children: const [
          Expanded(child: _TierCard(
            name: 'Free',
            price: '\$0',
            color: AppColors.textMuted,
            features: ['5 مشاريع/شهر', 'حتى 2 ألوان', 'تصدير PNG فقط'],
          )),
          SizedBox(width: 12),
          Expanded(child: _TierCard(
            name: 'Basic',
            price: '\$9.99',
            color: AppColors.accent,
            features: ['50 مشروع/شهر', 'حتى 4 ألوان', 'Halftone', 'PDF + SVG'],
            highlighted: true,
          )),
          SizedBox(width: 12),
          Expanded(child: _TierCard(
            name: 'Pro',
            price: '\$29.99',
            color: AppColors.primary,
            features: ['غير محدود', 'حتى 10 ألوان', 'Batch processing', 'كل الصيغ'],
          )),
        ]),
      ],
    );
  }
}

class _TierCard extends StatelessWidget {
  final String name, price;
  final Color color;
  final List<String> features;
  final bool highlighted;

  const _TierCard({
    required this.name,
    required this.price,
    required this.color,
    required this.features,
    this.highlighted = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: highlighted ? color.withOpacity(0.08) : AppColors.surface3,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(
          color: highlighted ? color.withOpacity(0.5) : AppColors.border,
          width: highlighted ? 1.5 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(name, style: TextStyle(
            color: color, fontSize: 13, fontWeight: FontWeight.w700,
          )),
          const SizedBox(height: 4),
          Text(price, style: AppTextStyles.headingS),
          const SizedBox(height: 8),
          ...features.map((f) => Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Row(children: [
              Icon(Icons.check, size: 12, color: color),
              const SizedBox(width: 4),
              Expanded(child: Text(f, style: AppTextStyles.bodyS)),
            ]),
          )),
        ],
      ),
    );
  }
}
