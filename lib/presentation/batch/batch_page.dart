/// batch_page.dart — Batch Processing Screen
/// Virtual Design Silk Screen Studio
///
/// MED #5 FIX: الـ use case كان موجوداً لكن الـ UI غائب

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'batch_controller.dart';
import '../../app/themes/app_theme.dart';
import '../../domain/entities/processing_settings.dart';

class BatchPage extends StatelessWidget {
  const BatchPage({super.key});

  @override
  Widget build(BuildContext context) {
    final ctrl = Get.find<BatchController>();
    return Scaffold(
      backgroundColor: AppColors.surface1,
      appBar: AppBar(
        title: const Text('معالجة دفعية'),
        actions: [
          Obx(() => ctrl.isProcessing.value
              ? TextButton.icon(
                  onPressed: ctrl.cancel,
                  icon: const Icon(Icons.stop, size: 16, color: AppColors.error),
                  label: const Text('إيقاف', style: TextStyle(color: AppColors.error)),
                )
              : const SizedBox.shrink()),
        ],
      ),
      body: Obx(() {
        if (ctrl.isProcessing.value || ctrl.isFinished.value) {
          return _ProcessingView(ctrl: ctrl);
        }
        return _SetupView(ctrl: ctrl);
      }),
    );
  }
}

// ─── Setup View ───────────────────────────────────────────────────────────────

class _SetupView extends StatelessWidget {
  final BatchController ctrl;
  const _SetupView({required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Images List ──────────────────────────────────────────────────
          _SectionHeader(
            icon: Icons.photo_library_outlined,
            title: 'الصور المختارة',
            action: TextButton.icon(
              onPressed: ctrl.pickImages,
              icon: const Icon(Icons.add_photo_alternate_outlined, size: 16),
              label: const Text('إضافة صور'),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),

          Obx(() => ctrl.imagePaths.isEmpty
              ? _EmptyImages(onPick: ctrl.pickImages)
              : _ImageGrid(ctrl: ctrl)),

          const SizedBox(height: AppSpacing.lg),

          // ── Settings ─────────────────────────────────────────────────────
          _SectionHeader(
            icon: Icons.tune_outlined,
            title: 'إعدادات المعالجة',
          ),
          const SizedBox(height: AppSpacing.sm),
          _SettingsPanel(ctrl: ctrl),

          const SizedBox(height: AppSpacing.xl),

          // ── Start Button ─────────────────────────────────────────────────
          Obx(() => ElevatedButton.icon(
            onPressed: ctrl.imagePaths.isEmpty ? null : ctrl.startProcessing,
            icon: const Icon(Icons.play_arrow_rounded),
            label: Text(
              ctrl.imagePaths.isEmpty
                  ? 'اختر صوراً أولاً'
                  : 'بدء معالجة ${ctrl.imagePaths.length} صورة',
            ),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          )),
        ],
      ),
    );
  }
}

// ─── Processing View ──────────────────────────────────────────────────────────

class _ProcessingView extends StatelessWidget {
  final BatchController ctrl;
  const _ProcessingView({required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final progress = ctrl.batchProgress.value;
      final total = ctrl.imagePaths.length;

      return Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Overall Progress ─────────────────────────────────────────
            _ProgressCard(
              title: ctrl.isFinished.value ? 'اكتملت المعالجة' : 'جاري المعالجة...',
              progress: progress?.overallProgress ?? 0,
              message: progress?.displayText ?? '',
              isFinished: ctrl.isFinished.value,
            ),
            const SizedBox(height: AppSpacing.lg),

            // ── Results List ──────────────────────────────────────────────
            _SectionHeader(
              icon: Icons.list_alt_outlined,
              title: 'نتائج المعالجة',
              action: ctrl.isFinished.value
                  ? TextButton.icon(
                      onPressed: ctrl.openOutputFolder,
                      icon: const Icon(Icons.folder_open, size: 16),
                      label: const Text('فتح المجلد'),
                    )
                  : null,
            ),
            const SizedBox(height: AppSpacing.sm),

            Expanded(
              child: ListView.separated(
                itemCount: total,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) {
                  final completed = progress?.completed ?? [];
                  final result = i < completed.length ? completed[i] : null;
                  final isCurrent = i == (progress?.currentIndex ?? -1);
                  final isPending = i > (progress?.currentIndex ?? -1) &&
                      !ctrl.isFinished.value;

                  return _ResultRow(
                    path: ctrl.imagePaths[i],
                    result: result,
                    isCurrent: isCurrent,
                    isPending: isPending,
                  );
                },
              ),
            ),

            if (ctrl.isFinished.value) ...[
              const SizedBox(height: AppSpacing.lg),
              Row(children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: ctrl.reset,
                    child: const Text('معالجة دفعة أخرى'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => Get.back(),
                    child: const Text('إغلاق'),
                  ),
                ),
              ]),
            ],
          ],
        ),
      );
    });
  }
}

// ─── Supporting Widgets ───────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  final Widget? action;

  const _SectionHeader({
    required this.icon, required this.title, this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Icon(icon, size: 16, color: AppColors.primary),
      const SizedBox(width: 8),
      Text(title, style: AppTextStyles.headingS),
      if (action != null) ...[const Spacer(), action!],
    ]);
  }
}

class _EmptyImages extends StatelessWidget {
  final VoidCallback onPick;
  const _EmptyImages({required this.onPick});
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPick,
      child: Container(
        height: 140,
        decoration: BoxDecoration(
          color: AppColors.surface3,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(
            color: AppColors.border,
            style: BorderStyle.solid,
          ),
        ),
        child: const Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.add_photo_alternate_outlined,
                size: 36, color: AppColors.textMuted),
            SizedBox(height: 8),
            Text('اضغط لاختيار الصور', style: AppTextStyles.bodyM),
            Text('يمكنك اختيار عدة صور دفعة واحدة',
                style: AppTextStyles.bodyS),
          ],
        ),
      ),
    );
  }
}

class _ImageGrid extends StatelessWidget {
  final BatchController ctrl;
  const _ImageGrid({required this.ctrl});
  @override
  Widget build(BuildContext context) {
    return Obx(() => Wrap(
      spacing: 8, runSpacing: 8,
      children: [
        ...ctrl.imagePaths.asMap().entries.map((e) =>
          _ImageChip(
            path: e.value,
            onRemove: () => ctrl.removeImage(e.key),
          )),
        _AddMoreChip(onTap: ctrl.pickImages),
      ],
    ));
  }
}

class _ImageChip extends StatelessWidget {
  final String path;
  final VoidCallback onRemove;
  const _ImageChip({required this.path, required this.onRemove});
  @override
  Widget build(BuildContext context) {
    final name = path.split('/').last.split('\\').last;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surface3,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.image_outlined, size: 14, color: AppColors.primary),
        const SizedBox(width: 6),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 120),
          child: Text(
            name, style: AppTextStyles.bodyS,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 4),
        GestureDetector(
          onTap: onRemove,
          child: const Icon(Icons.close, size: 14, color: AppColors.textMuted),
        ),
      ]),
    );
  }
}

class _AddMoreChip extends StatelessWidget {
  final VoidCallback onTap;
  const _AddMoreChip({required this.onTap});
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.primary.withOpacity(0.1),
          borderRadius: BorderRadius.circular(AppRadius.full),
          border: Border.all(color: AppColors.primary.withOpacity(0.3)),
        ),
        child: const Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.add, size: 14, color: AppColors.primary),
          SizedBox(width: 4),
          Text('إضافة', style: TextStyle(color: AppColors.primary, fontSize: 12)),
        ]),
      ),
    );
  }
}

class _SettingsPanel extends StatelessWidget {
  final BatchController ctrl;
  const _SettingsPanel({required this.ctrl});
  @override
  Widget build(BuildContext context) {
    return Obx(() => Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface3,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          // Color Count
          Row(children: [
            const Expanded(child: Text('عدد الألوان', style: AppTextStyles.bodyM)),
            DropdownButton<int>(
              value: ctrl.colorCount.value,
              dropdownColor: AppColors.surface3,
              underline: const SizedBox.shrink(),
              items: [1, 2, 3, 4].map((n) => DropdownMenuItem(
                value: n,
                child: Text('$n ألوان', style: AppTextStyles.bodyM),
              )).toList(),
              onChanged: (v) => ctrl.colorCount.value = v ?? 2,
            ),
          ]),
          const Divider(),
          // Print Type
          Row(children: [
            const Expanded(child: Text('نوع الطباعة', style: AppTextStyles.bodyM)),
            DropdownButton<PrintFinish>(
              value: ctrl.printFinish.value,
              dropdownColor: AppColors.surface3,
              underline: const SizedBox.shrink(),
              items: PrintFinish.values.map((f) => DropdownMenuItem(
                value: f,
                child: Text(f == PrintFinish.solid ? 'Solid' : 'Halftone',
                    style: AppTextStyles.bodyM),
              )).toList(),
              onChanged: (v) => ctrl.printFinish.value = v ?? PrintFinish.solid,
            ),
          ]),
          const Divider(),
          // DPI
          Row(children: [
            const Expanded(child: Text('الدقة (DPI)', style: AppTextStyles.bodyM)),
            DropdownButton<int>(
              value: ctrl.dpi.value,
              dropdownColor: AppColors.surface3,
              underline: const SizedBox.shrink(),
              items: [150, 300, 600].map((d) => DropdownMenuItem(
                value: d,
                child: Text('$d DPI', style: AppTextStyles.bodyM),
              )).toList(),
              onChanged: (v) => ctrl.dpi.value = v ?? 300,
            ),
          ]),
        ],
      ),
    ));
  }
}

class _ProgressCard extends StatelessWidget {
  final String title, message;
  final double progress;
  final bool isFinished;

  const _ProgressCard({
    required this.title, required this.progress,
    required this.message, required this.isFinished,
  });

  @override
  Widget build(BuildContext context) {
    final color = isFinished ? AppColors.success : AppColors.primary;
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
            isFinished
                ? const Icon(Icons.check_circle, color: AppColors.success, size: 20)
                : SizedBox(
                    width: 18, height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2, color: color,
                      value: progress > 0 ? progress : null,
                    ),
                  ),
            const SizedBox(width: 10),
            Text(title, style: AppTextStyles.headingS.copyWith(color: color)),
            const Spacer(),
            Text('${(progress * 100).toInt()}%',
                style: TextStyle(color: color, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 10),
          LinearProgressIndicator(
            value: progress,
            backgroundColor: AppColors.surface4,
            color: color,
            minHeight: 4,
            borderRadius: BorderRadius.circular(2),
          ),
          if (message.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(message, style: AppTextStyles.bodyS),
          ],
        ],
      ),
    );
  }
}

class _ResultRow extends StatelessWidget {
  final String path;
  final dynamic result; // BatchImageResult?
  final bool isCurrent, isPending;

  const _ResultRow({
    required this.path,
    this.result,
    this.isCurrent = false,
    this.isPending = false,
  });

  @override
  Widget build(BuildContext context) {
    final name = path.split('/').last.split('\\').last;
    Color? statusColor;
    IconData? statusIcon;
    String statusText = '';

    if (isCurrent) {
      statusColor = AppColors.accent;
      statusIcon  = Icons.autorenew;
      statusText  = 'جاري...';
    } else if (isPending) {
      statusColor = AppColors.textMuted;
      statusIcon  = Icons.hourglass_empty;
      statusText  = 'في الانتظار';
    } else if (result != null) {
      if (result.success) {
        statusColor = AppColors.success;
        statusIcon  = Icons.check_circle_outline;
        statusText  = 'تم ✓';
      } else {
        statusColor = AppColors.error;
        statusIcon  = Icons.error_outline;
        statusText  = 'فشل';
      }
    }

    return ListTile(
      dense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 0, vertical: 2),
      leading: const Icon(Icons.image_outlined, size: 18, color: AppColors.textMuted),
      title: Text(name, style: AppTextStyles.bodyM, overflow: TextOverflow.ellipsis),
      subtitle: result?.errorMessage != null
          ? Text(result!.errorMessage!, style: AppTextStyles.bodyS.copyWith(color: AppColors.error))
          : null,
      trailing: statusIcon != null ? Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(statusText, style: TextStyle(color: statusColor, fontSize: 12)),
          const SizedBox(width: 4),
          isCurrent
              ? SizedBox(
                  width: 14, height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 1.5, color: statusColor,
                  ),
                )
              : Icon(statusIcon, size: 16, color: statusColor),
        ],
      ) : null,
    );
  }
}
