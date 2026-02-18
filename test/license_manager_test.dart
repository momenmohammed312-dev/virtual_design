/// license_manager_test.dart — License Manager Tests
/// Virtual Design Silk Screen Studio

import 'package:flutter_test/flutter_test.dart';
import 'package:virtual_design/core/licensing/license_manager.dart';
import 'package:virtual_design/core/licensing/license_model.dart';

void main() {
  group('LicenseManager', () {
    setUp(() {
      // Setup for tests
    });

    test('License model can be created', () {
      final license = License(
        activationKey: 'TEST-KEY-1234-5678',
        licenseHash: 'hash123',
        deviceId: 'device-001',
        activated: DateTime.now(),
        expiresAt: DateTime.now().add(const Duration(days: 365)),
      );

      expect(license.activationKey, 'TEST-KEY-1234-5678');
      expect(license.isExpired, false);
      expect(license.daysRemaining, greaterThan(360));
    });

    test('License expiration check works', () {
      final expiredLicense = License(
        activationKey: 'TEST-KEY',
        licenseHash: 'hash',
        deviceId: 'device-001',
        activated: DateTime.now().subtract(const Duration(days: 400)),
        expiresAt: DateTime.now().subtract(const Duration(days: 1)),
      );

      expect(expiredLicense.isExpired, true);
      expect(expiredLicense.daysRemaining, 0);
    });

    test('License JSON serialization works', () {
      final license = License(
        activationKey: 'TEST-KEY-1234-5678',
        licenseHash: 'hash123',
        deviceId: 'device-001',
        activated: DateTime.now(),
        expiresAt: DateTime.now().add(const Duration(days: 365)),
      );

      final json = license.toJson();
      expect(json['activationKey'], 'TEST-KEY-1234-5678');
      expect(json['deviceId'], 'device-001');

      final restored = License.fromJson(json);
      expect(restored.activationKey, license.activationKey);
      expect(restored.deviceId, license.deviceId);
    });

    test('License copyWith creates modified copy', () {
      final license = License(
        activationKey: 'TEST-KEY',
        licenseHash: 'hash',
        deviceId: 'device-001',
        activated: DateTime.now(),
        expiresAt: DateTime.now().add(const Duration(days: 365)),
      );

      final modified = license.copyWith(
        activationKey: 'NEW-TEST-KEY',
      );

      expect(modified.activationKey, 'NEW-TEST-KEY');
      expect(modified.deviceId, 'device-001'); // Unchanged
    });

    test('LicenseStatus enum has descriptions', () {
      expect(LicenseStatus.valid.description, contains('active'));
      expect(LicenseStatus.notActivated.description, contains('activate'));
      expect(LicenseStatus.expired.description, contains('expired'));
    });

    test('LicenseStatus.requiresActivation check', () {
      expect(LicenseStatus.valid.requiresActivation, false);
      expect(LicenseStatus.notActivated.requiresActivation, true);
      expect(LicenseStatus.expired.requiresActivation, true);
    });
  });
}
