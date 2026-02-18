/// license_controller.dart — GetX Controller for License Page
/// Virtual Design Silk Screen Studio

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../core/licensing/license_service.dart';

class LicenseController extends GetxController {
  final LicenseService licenseService;

  LicenseController({required this.licenseService});

  final TextEditingController keyController = TextEditingController();

  final RxBool isLoading       = false.obs;
  final RxString errorMessage  = ''.obs;
  final RxString successMessage = ''.obs;
  final Rx<LicenseInfo?> licenseInfo = Rx<LicenseInfo?>(null);

  @override
  void onInit() {
    super.onInit();
    _loadCurrentLicense();
  }

  @override
  void onClose() {
    keyController.dispose();
    super.onClose();
  }

  void _loadCurrentLicense() {
    licenseInfo.value = licenseService.getCurrentLicense();
  }

  bool get hasActiveLicense => licenseInfo.value != null;

  int get remainingProjects => licenseService.getRemainingProjects();

  SubscriptionTier get currentTier => licenseService.getCurrentTier();

  void clearError() {
    if (errorMessage.value.isNotEmpty) errorMessage.value = '';
    if (successMessage.value.isNotEmpty) successMessage.value = '';
  }

  Future<void> activate() async {
    final key = keyController.text.trim();
    if (key.isEmpty) {
      errorMessage.value = 'أدخل مفتاح الترخيص أولاً.';
      return;
    }

    isLoading.value = true;
    errorMessage.value = '';
    successMessage.value = '';

    final result = await licenseService.activateLicense(key);
    isLoading.value = false;

    if (result.success && result.license != null) {
      licenseInfo.value = result.license;
      keyController.clear();
      successMessage.value =
          'تم التفعيل! مرحباً ${result.license!.tier.displayName} 🎉';
    } else if (result.isExpired) {
      errorMessage.value = result.errorMessage ?? 'الترخيص منتهي الصلاحية.';
    } else {
      errorMessage.value = result.errorMessage ?? 'مفتاح ترخيص غير صالح.';
    }
  }

  Future<void> deactivate() async {
    final confirmed = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('إلغاء الترخيص'),
        content: const Text('هل تريد إلغاء الترخيص الحالي؟\nستتحول للـ Free plan.'),
        actions: [
          TextButton(onPressed: () => Get.back(result: false), child: const Text('لا')),
          ElevatedButton(
            onPressed: () => Get.back(result: true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('نعم، إلغاء'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await licenseService.deactivateLicense();
      licenseInfo.value = null;
      successMessage.value = 'تم إلغاء الترخيص.';
    }
  }
}
