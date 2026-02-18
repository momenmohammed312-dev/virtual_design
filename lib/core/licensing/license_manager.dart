/// license_manager.dart — License Management & Validation
/// Virtual Design Silk Screen Studio
/// Phase 7: Offline license validation with SHA-256

library virtual_design.licensing.license_manager;

import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:path_provider/path_provider.dart';
import 'license_model.dart';

class LicenseManager {
  static const String _licenseFileName = 'license.json';
  
  /// Load license from local storage
  Future<License?> loadLicense() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/$_licenseFileName');
      
      if (!file.existsSync()) {
        return null;
      }
      
      final jsonStr = await file.readAsString();
      final json = jsonDecode(jsonStr) as Map<String, dynamic>;
      return License.fromJson(json);
    } catch (e) {
      print('❌ Failed to load license: $e');
      return null;
    }
  }
  
  /// Save license to local storage
  Future<bool> saveLicense(License license) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/$_licenseFileName');
      
      final json = license.toJson();
      await file.writeAsString(jsonEncode(json));
      
      print('✅ License saved successfully');
      return true;
    } catch (e) {
      print('❌ Failed to save license: $e');
      return false;
    }
  }
  
  /// Validate license against device ID
  /// Returns: (valid, message)
  Future<(bool, String)> validateLicense(
    License license,
    String deviceId,
  ) async {
    try {
      // Check expiration
      if (license.isExpired) {
        return (false, 'License has expired on ${license.expiresAt}');
      }
      
      // Check device ID
      if (license.deviceId != deviceId) {
        return (false, 'License is not valid for this device');
      }
      
      // Validate hash
      final expectedHash = _computeHash(license.activationKey, deviceId);
      if (license.licenseHash != expectedHash) {
        return (false, 'License signature is invalid');
      }
      
      return (true, 'License is valid');
    } catch (e) {
      return (false, 'Validation error: $e');
    }
  }
  
  /// Activate new license with activation key
  Future<(bool, String, License?)> activateLicense({
    required String activationKey,
    required String deviceId,
  }) async {
    try {
      // Validate activation key format (basic check)
      if (activationKey.isEmpty || activationKey.length < 16) {
        return (false, 'Invalid activation key format', null);
      }
      
      // Compute hash
      final hash = _computeHash(activationKey, deviceId);
      
      // Create license
      final license = License(
        activationKey: activationKey,
        licenseHash: hash,
        deviceId: deviceId,
        activated: DateTime.now(),
        expiresAt: DateTime.now().add(const Duration(days: 365)),
      );
      
      // Save to storage
      final saved = await saveLicense(license);
      if (!saved) {
        return (false, 'Failed to save license', null);
      }
      
      return (true, 'License activated successfully', license);
    } catch (e) {
      return (false, 'Activation failed: $e', null);
    }
  }
  
  /// Deactivate (remove) license
  Future<bool> deactivateLicense() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/$_licenseFileName');
      
      if (file.existsSync()) {
        await file.delete();
        print('✅ License deactivated');
        return true;
      }
      return true;
    } catch (e) {
      print('❌ Failed to deactivate license: $e');
      return false;
    }
  }
  
  /// Check license status
  Future<LicenseStatus> checkLicenseStatus() async {
    final license = await loadLicense();
    
    if (license == null) {
      return LicenseStatus.notActivated;
    }
    
    if (license.isExpired) {
      return LicenseStatus.expired;
    }
    
    return LicenseStatus.valid;
  }
  
  /// Compute license hash from activation key and device ID
  String _computeHash(String activationKey, String deviceId) {
    final data = '$activationKey:$deviceId';
    return sha256.convert(utf8.encode(data)).toString();
  }
}

enum LicenseStatus {
  valid,
  notActivated,
  expired,
  invalid,
}

extension LicenseStatusExt on LicenseStatus {
  String get description {
    switch (this) {
      case LicenseStatus.valid:
        return 'Your license is active and valid';
      case LicenseStatus.notActivated:
        return 'Please activate your license to continue';
      case LicenseStatus.expired:
        return 'Your license has expired';
      case LicenseStatus.invalid:
        return 'Your license is invalid';
    }
  }
  
  bool get requiresActivation => 
    this == LicenseStatus.notActivated || this == LicenseStatus.expired;
}
