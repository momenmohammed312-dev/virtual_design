// license_service.dart — Offline Licensing System
// Virtual Design Silk Screen Studio
//
// HIGH #4 FIX: نظام ترخيص offline كامل كان غائب تماماً
// يستخدم SHA-256 + Base64 لـ key generation/validation بدون cloud

import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:hive/hive.dart';

// ─── Enums ───────────────────────────────────────────────────────────────────

enum SubscriptionTier { free, basic, professional }

extension SubscriptionTierExt on SubscriptionTier {
  String get displayName {
    switch (this) {
      case SubscriptionTier.free:         return 'Free';
      case SubscriptionTier.basic:        return 'Basic';
      case SubscriptionTier.professional: return 'Professional';
    }
  }

  String get description {
    switch (this) {
      case SubscriptionTier.free:         return '5 projects/month · 2 colors';
      case SubscriptionTier.basic:        return '50 projects/month · 4 colors · Halftone';
      case SubscriptionTier.professional: return 'Unlimited · 10 colors · Batch processing';
    }
  }
}

// ─── License Info ─────────────────────────────────────────────────────────────

class LicenseInfo {
  final String email;
  final SubscriptionTier tier;
  final DateTime expiryDate;
  final DateTime activatedAt;

  const LicenseInfo({
    required this.email,
    required this.tier,
    required this.expiryDate,
    required this.activatedAt,
  });

  bool get isExpired => expiryDate.isBefore(DateTime.now());

  int get daysRemaining {
    final diff = expiryDate.difference(DateTime.now()).inDays;
    return diff < 0 ? 0 : diff;
  }

  bool get isExpiringSoon => daysRemaining <= 7;

  Map<String, dynamic> toJson() => {
        'email': email,
        'tier': tier.name,
        'expiryDate': expiryDate.toIso8601String(),
        'activatedAt': activatedAt.toIso8601String(),
      };

  factory LicenseInfo.fromJson(Map<String, dynamic> json) => LicenseInfo(
        email: json['email'] as String,
        tier: SubscriptionTier.values.firstWhere(
          (t) => t.name == json['tier'],
          orElse: () => SubscriptionTier.free,
        ),
        expiryDate: DateTime.parse(json['expiryDate'] as String),
        activatedAt: DateTime.parse(json['activatedAt'] as String),
      );
}

// ─── Tier Limits ──────────────────────────────────────────────────────────────

class TierLimits {
  static const Map<SubscriptionTier, Map<String, dynamic>> _limits = {
    SubscriptionTier.free: {
      'projectsPerMonth': 5,
      'maxColors': 2,
      'halftone': false,
      'batchProcessing': false,
      'svgExport': false,
      'pdfExport': false,
    },
    SubscriptionTier.basic: {
      'projectsPerMonth': 50,
      'maxColors': 4,
      'halftone': true,
      'batchProcessing': false,
      'svgExport': true,
      'pdfExport': true,
    },
    SubscriptionTier.professional: {
      'projectsPerMonth': -1,   // unlimited
      'maxColors': 10,
      'halftone': true,
      'batchProcessing': true,
      'svgExport': true,
      'pdfExport': true,
    },
  };

  static dynamic get(SubscriptionTier tier, String feature) =>
      _limits[tier]?[feature];

  static bool canUseFeature(SubscriptionTier tier, String feature) {
    final val = _limits[tier]?[feature];
    if (val is bool) return val;
    if (val is int) return val != 0;
    return false;
  }

  static int getMaxColors(SubscriptionTier tier) =>
      (_limits[tier]?['maxColors'] as int?) ?? 2;

  static int getProjectsPerMonth(SubscriptionTier tier) =>
      (_limits[tier]?['projectsPerMonth'] as int?) ?? 5;
}

// ─── License Service ──────────────────────────────────────────────────────────

class LicenseService {
  // ⚠ يجب تغيير هذا في production قبل رفع التطبيق
  // يجب أن يكون نفس الـ secret_key في admin tool لتوليد المفاتيح
  static const String _secretKey = 'VD_SILK_SCREEN_SECRET_KEY_2026_CHANGE_ME';

  static const String _boxName = 'license_box';
  static const String _licenseKey = 'current_license';
  static const String _projectCountKey = 'project_count_month';
  static const String _projectMonthKey = 'project_count_year_month';

  Box? _box;

  Future<void> initialize() async {
    _box = await Hive.openBox(_boxName);
  }

  // ─── Key Validation ──────────────────────────────────────────────────────

  /// التحقق من مفتاح الترخيص وتفعيله
  Future<LicenseActivationResult> activateLicense(String rawKey) async {
    final key = rawKey.trim();
    if (key.isEmpty) {
      return LicenseActivationResult.invalid('License key cannot be empty.');
    }

    final parts = key.split('-');
    if (parts.length < 2) {
      return LicenseActivationResult.invalid('Invalid key format.');
    }

    try {
      // فصل الـ keyData عن الـ signature
      final signature = parts.last;
      final keyData = parts.sublist(0, parts.length - 1).join('-');

      // فك تشفير الـ base64
      final decodedBytes = base64.decode(keyData);
      final decodedData = utf8.decode(decodedBytes);

      // التحقق من الـ signature
      final expectedSig = _computeSignature(decodedData);
      if (signature != expectedSig) {
        return LicenseActivationResult.invalid('Invalid license key signature.');
      }

      // استخراج البيانات: email|tier|expiryDate
      final dataParts = decodedData.split('|');
      if (dataParts.length != 3) {
        return LicenseActivationResult.invalid('Malformed license data.');
      }

      final email = dataParts[0];
      final tierName = dataParts[1];
      final expiryDate = DateTime.parse(dataParts[2]);

      // التحقق من الصلاحية
      if (expiryDate.isBefore(DateTime.now())) {
        return LicenseActivationResult.expired(
          'License expired on ${_formatDate(expiryDate)}.',
        );
      }

      // تحديد الـ tier
      final tier = SubscriptionTier.values.firstWhere(
        (t) => t.name == tierName,
        orElse: () => SubscriptionTier.free,
      );

      // حفظ الترخيص
      final info = LicenseInfo(
        email: email,
        tier: tier,
        expiryDate: expiryDate,
        activatedAt: DateTime.now(),
      );
      await _saveLicense(info);

      return LicenseActivationResult.success(info);
    } on FormatException catch (_) {
      return LicenseActivationResult.invalid('Invalid license key encoding.');
    } catch (e) {
      return LicenseActivationResult.invalid('Activation error: $e');
    }
  }

  String _computeSignature(String data) {
    final bytes = utf8.encode(data + _secretKey);
    final digest = sha256.convert(bytes);
    return digest.toString().substring(0, 16);
  }

  // ─── Current License ─────────────────────────────────────────────────────

  LicenseInfo? getCurrentLicense() {
    final json = _box?.get(_licenseKey) as Map?;
    if (json == null) return null;
    try {
      final info = LicenseInfo.fromJson(Map<String, dynamic>.from(json));
      if (info.isExpired) return null; // منتهي الصلاحية
      return info;
    } catch (_) {
      return null;
    }
  }

  SubscriptionTier getCurrentTier() {
    return getCurrentLicense()?.tier ?? SubscriptionTier.free;
  }

  bool isFeatureEnabled(String feature) =>
      TierLimits.canUseFeature(getCurrentTier(), feature);

  int getMaxColors() => TierLimits.getMaxColors(getCurrentTier());

  // ─── Project Count Tracking ───────────────────────────────────────────────

  bool canCreateProject() {
    final max = TierLimits.getProjectsPerMonth(getCurrentTier());
    if (max == -1) return true; // unlimited
    return _getMonthlyProjectCount() < max;
  }

  void incrementProjectCount() {
    final currentMonth = _currentYearMonth();
    final savedMonth = _box?.get(_projectMonthKey) as String?;

    if (savedMonth != currentMonth) {
      // شهر جديد — إعادة العداد
      _box?.put(_projectMonthKey, currentMonth);
      _box?.put(_projectCountKey, 1);
    } else {
      final current = (_box?.get(_projectCountKey) as int?) ?? 0;
      _box?.put(_projectCountKey, current + 1);
    }
  }

  int getRemainingProjects() {
    final max = TierLimits.getProjectsPerMonth(getCurrentTier());
    if (max == -1) return -1; // unlimited
    return max - _getMonthlyProjectCount();
  }

  int _getMonthlyProjectCount() {
    final currentMonth = _currentYearMonth();
    final savedMonth = _box?.get(_projectMonthKey) as String?;
    if (savedMonth != currentMonth) return 0;
    return (_box?.get(_projectCountKey) as int?) ?? 0;
  }

  String _currentYearMonth() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}';
  }

  // ─── Storage ─────────────────────────────────────────────────────────────

  Future<void> _saveLicense(LicenseInfo info) async {
    await _box?.put(_licenseKey, info.toJson());
  }

  Future<void> deactivateLicense() async {
    await _box?.delete(_licenseKey);
  }

  // ─── Admin: Key Generation (للاستخدام في admin tool فقط) ────────────────

  /// توليد مفتاح ترخيص — يُستخدم في admin dashboard فقط
  /// لا تضع هذا في production build
  static String generateLicenseKey({
    required String email,
    required SubscriptionTier tier,
    required DateTime expiryDate,
  }) {
    final data = '$email|${tier.name}|${expiryDate.toIso8601String()}';
    final keyData = base64.encode(utf8.encode(data));
    final sig = sha256
        .convert(utf8.encode(data + _secretKey))
        .toString()
        .substring(0, 16);
    return '$keyData-$sig';
  }

  String _formatDate(DateTime date) =>
      '${date.day}/${date.month}/${date.year}';
}

// ─── Activation Result ────────────────────────────────────────────────────────

class LicenseActivationResult {
  final bool success;
  final LicenseInfo? license;
  final String? errorMessage;
  final bool isExpired;

  const LicenseActivationResult._({
    required this.success,
    this.license,
    this.errorMessage,
    this.isExpired = false,
  });

  factory LicenseActivationResult.success(LicenseInfo info) =>
      LicenseActivationResult._(success: true, license: info);

  factory LicenseActivationResult.invalid(String message) =>
      LicenseActivationResult._(success: false, errorMessage: message);

  factory LicenseActivationResult.expired(String message) =>
      LicenseActivationResult._(
        success: false,
        errorMessage: message,
        isExpired: true,
      );
}
