// lib/core/licensing/license_manager.dart

import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import 'license_model.dart';

class LicenseManager {
  static const String _licenseFileName = 'license.json';

  License? _currentLicense;

  /// Get current license
  License? get currentLicense => _currentLicense;

  /// Check if license is valid
  bool get isValid => _currentLicense?.isValid ?? false;

  /// Load license from local storage
  Future<License?> loadLicense() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/$_licenseFileName');

      if (!await file.exists()) {
        return null;
      }

      final json = jsonDecode(await file.readAsString());
      _currentLicense = License.fromJson(json);
      return _currentLicense;
    } catch (e) {
      debugPrint('[LicenseManager] Error loading license: $e');
      return null;
    }
  }

  /// Save license to local storage
  Future<bool> saveLicense(License license) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/$_licenseFileName');

      await file.writeAsString(jsonEncode(license.toJson()));
      _currentLicense = license;
      return true;
    } catch (e) {
      debugPrint('[LicenseManager] Error saving license: $e');
      return false;
    }
  }

  /// Validate license key
  Future<LicenseStatus> validateLicense(String key) async {
    // TODO: Implement actual license validation
    // For now, accept any non-empty key
    if (key.isNotEmpty) {
      final license = License(
        key: key,
        status: LicenseStatus.active,
        expiryDate: DateTime.now().add(const Duration(days: 365)),
      );
      await saveLicense(license);
      return LicenseStatus.active;
    }
    return LicenseStatus.invalid;
  }

  /// Clear current license
  Future<void> clearLicense() async {
    _currentLicense = null;
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/$_licenseFileName');
      if (await file.exists()) {
        await file.delete();
      }
    } catch (e) {
      debugPrint('[LicenseManager] Error clearing license: $e');
    }
  }
}
