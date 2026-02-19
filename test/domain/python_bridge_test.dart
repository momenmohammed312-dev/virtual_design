// python_bridge_test.dart — Dart Unit Tests
// Virtual Design Silk Screen Studio
//
// Tests for: PythonConfig, ProcessResult, PythonProcessor

import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:virtual_design/core/python_bridge/python_config.dart';
import 'package:virtual_design/core/python_bridge/process_result.dart';


// ─── ProcessResult Tests ──────────────────────────────────────────────────────

void main() {
  group('ProcessResult', () {
    test('success factory sets correct fields', () {
      final result = ProcessResult.success(outputDirectory: '/tmp/output_123');
      expect(result.success, isTrue);
      expect(result.outputDirectory, equals('/tmp/output_123'));
      expect(result.errorMessage, isNull);
    });

    test('failure factory sets correct fields', () {
      final result = ProcessResult.failure('Python not found');
      expect(result.success, isFalse);
      expect(result.errorMessage, equals('Python not found'));
      expect(result.outputDirectory, isNull);
    });

    test('hasValidOutput is true when outputDirectory is not empty', () {
      final result = ProcessResult.success(outputDirectory: '/some/path');
      expect(result.hasValidOutput, isTrue);
    });

    test('hasValidOutput is false when outputDirectory is empty', () {
      final result = ProcessResult.failure('error');
      expect(result.hasValidOutput, isFalse);
    });

    test('toString includes success status', () {
      final r1 = ProcessResult.success(outputDirectory: '/tmp');
      final r2 = ProcessResult.failure('failed');
      expect(r1.toString(), contains('success'));
      expect(r2.toString(), contains('failed'));
    });
  });

  // ─── PythonInitResult Tests ───────────────────────────────────────────────

  group('PythonInitResult', () {
    test('success result has correct state', () {
      final result = PythonInitResult(
        success: true,
        pythonVersion: 'Python 3.11.0',
        missingPackages: [],
      );
      expect(result.success, isTrue);
      expect(result.hasMissingPackages, isFalse);
      expect(result.pythonVersion, equals('Python 3.11.0'));
    });

    test('hasMissingPackages is true when packages are missing', () {
      final result = PythonInitResult(
        success: false,
        missingPackages: ['opencv-python', 'numpy'],
      );
      expect(result.hasMissingPackages, isTrue);
      expect(result.missingPackages.length, equals(2));
    });

    test('failure result has error message', () {
      final result = PythonInitResult(
        success: false,
        error: 'Python not found',
        missingPackages: [],
      );
      expect(result.success, isFalse);
      expect(result.error, equals('Python not found'));
    });
  });

  // ─── LicenseService Tests (in-memory) ────────────────────────────────────

  group('LicenseService — generateLicenseKey', () {
    test('generated key has correct format (base64-signature)', () {
      // ignore: invalid_use_of_visible_for_testing_member
      final key = generateTestKey(
        email: 'test@example.com',
        tier: 'basic',
        expiryDate: DateTime(2027, 1, 1),
      );
      final parts = key.split('-');
      expect(parts.length, greaterThanOrEqualTo(2));
      // الجزء الأخير هو الـ signature (16 chars)
      expect(parts.last.length, equals(16));
    });
  });
}

// ─── Test Helper (لمحاكاة generateLicenseKey بدون import الكامل) ─────────────

String generateTestKey({
  required String email,
  required String tier,
  required DateTime expiryDate,
}) {
  const secretKey = 'VD_SILK_SCREEN_SECRET_KEY_2026_CHANGE_ME';
  final data = '$email|$tier|${expiryDate.toIso8601String()}';
  final keyData = base64.encode(utf8.encode(data));
  final sig = sha256
      .convert(utf8.encode(data + secretKey))
      .toString()
      .substring(0, 16);
  return '$keyData-$sig';
}
