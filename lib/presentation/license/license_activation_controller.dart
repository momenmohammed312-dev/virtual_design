/// license_activation_controller.dart — License Activation Control
/// Virtual Design Silk Screen Studio — Phase 7

library virtual_design.licensing.license_activation_controller;

import 'package:get/get.dart';
import 'package:path_provider/path_provider.dart';
import '../../core/licensing/license_manager.dart';
import '../../core/licensing/license_model.dart';

class LicenseActivationController extends GetxController {
  final LicenseManager licenseManager;
  
  // Observable state
  final activationKey = ''.obs;
  final isLoading = false.obs;
  final currentLicense = Rx<License?>(null);
  final licenseStatus = Rx<LicenseStatus>(LicenseStatus.notActivated);
  final statusMessage = ''.obs;
  
  // Device ID
  String? _deviceId;
  
  LicenseActivationController({
    required this.licenseManager,
  });
  
  @override
  void onInit() {
    super.onInit();
    _initializeDevice();
    _loadLicense();
  }
  
  /// Initialize device ID
  Future<void> _initializeDevice() async {
    try {
      _deviceId = await _getDeviceId();
    } catch (e) {
      print('❌ Failed to get device ID: $e');
      _deviceId = 'unknown_device';
    }
  }
  
  /// Get unique device ID (fallback implementation)
  /// TODO: Integrate device_info_plus for proper device identification
  Future<String> _getDeviceId() async {
    try {
      // For now, use a simple device identifier
      // In production, use device_info_plus package
      final appDir = await getApplicationDocumentsDirectory();
      // Simple hash of app directory path as device identifier
      return appDir.path.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '_');
    } catch (e) {
      throw Exception('Cannot determine device ID: $e');
    }
  }
  
  /// Load existing license
  Future<void> _loadLicense() async {
    try {
      final license = await licenseManager.loadLicense();
      currentLicense.value = license;
      
      if (license != null && _deviceId != null) {
        final (valid, message) = await licenseManager.validateLicense(
          license,
          _deviceId!,
        );
        
        if (valid) {
          licenseStatus.value = LicenseStatus.valid;
          statusMessage.value = 'License is valid and active ✅';
        } else if (license.isExpired) {
          licenseStatus.value = LicenseStatus.expired;
          statusMessage.value = 'License has expired ⚠️';
        } else {
          licenseStatus.value = LicenseStatus.invalid;
          statusMessage.value = message;
        }
      } else {
        licenseStatus.value = LicenseStatus.notActivated;
        statusMessage.value = 'No active license found';
      }
    } catch (e) {
      print('❌ Failed to load license: $e');
      licenseStatus.value = LicenseStatus.invalid;
      statusMessage.value = 'Error loading license';
    }
  }
  
  /// Attempt to activate license with entered key
  Future<bool> activateLicense() async {
    if (activationKey.value.isEmpty) {
      statusMessage.value = 'Please enter an activation key';
      return false;
    }
    
    if (_deviceId == null) {
      statusMessage.value = 'Unable to determine device ID';
      return false;
    }
    
    isLoading.value = true;
    statusMessage.value = 'Activating license...';
    
    try {
      final (success, message, license) = 
        await licenseManager.activateLicense(
          activationKey: activationKey.value,
          deviceId: _deviceId!,
        );
      
      if (success && license != null) {
        currentLicense.value = license;
        licenseStatus.value = LicenseStatus.valid;
        statusMessage.value = 'License activated successfully! ✅';
        activationKey.value = ''; // Clear input
        
        isLoading.value = false;
        return true;
      } else {
        licenseStatus.value = LicenseStatus.invalid;
        statusMessage.value = message;
        isLoading.value = false;
        return false;
      }
    } catch (e) {
      licenseStatus.value = LicenseStatus.invalid;
      statusMessage.value = 'Activation failed: $e';
      isLoading.value = false;
      return false;
    }
  }
  
  /// Deactivate current license
  Future<bool> deactivateLicense() async {
    isLoading.value = true;
    
    try {
      final success = await licenseManager.deactivateLicense();
      
      if (success) {
        currentLicense.value = null;
        licenseStatus.value = LicenseStatus.notActivated;
        statusMessage.value = 'License deactivated';
        isLoading.value = false;
        return true;
      } else {
        statusMessage.value = 'Failed to deactivate license';
        isLoading.value = false;
        return false;
      }
    } catch (e) {
      statusMessage.value = 'Error: $e';
      isLoading.value = false;
      return false;
    }
  }
  
  /// Get license info text
  String getLicenseInfo() {
    final license = currentLicense.value;
    if (license == null) return 'No license active';
    
    return '''
Key: ${license.activationKey.substring(0, 8)}...
Device: ${license.deviceId}
Activated: ${license.activated.toString().split('.')[0]}
Expires: ${license.expiresAt.toString().split('.')[0]}
Days Remaining: ${license.daysRemaining}
    ''';
  }
  
  /// Check if can proceed (has valid license)
  bool get canProceed => licenseStatus.value == LicenseStatus.valid;
  
  /// Get status color
  String getStatusColor() {
    switch (licenseStatus.value) {
      case LicenseStatus.valid:
        return '#4CAF50'; // Green
      case LicenseStatus.expired:
        return '#F44336'; // Red
      case LicenseStatus.notActivated:
        return '#FF9800'; // Orange
      case LicenseStatus.invalid:
        return '#F44336'; // Red
    }
  }
}
