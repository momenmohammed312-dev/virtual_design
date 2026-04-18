// lib/core/licensing/license_model.dart

/// License status
enum LicenseStatus {
  active,
  expired,
  invalid,
  notFound,
  notActivated,
  valid,
}

/// License model
class License {
  final String key;
  final LicenseStatus status;
  final DateTime? expiryDate;
  final Map<String, dynamic>? features;
  final String? owner;
  final String? licenseHash;
  final String? deviceId;
  final DateTime? activated;

  License({
    required this.key,
    required this.status,
    this.expiryDate,
    this.features,
    this.owner,
    this.licenseHash,
    this.deviceId,
    this.activated,
  });

  bool get isValid => status == LicenseStatus.active || status == LicenseStatus.valid;
  bool get isExpired => status == LicenseStatus.expired || _isDateExpired;

  bool get _isDateExpired {
    if (expiryDate == null) return false;
    return DateTime.now().isAfter(expiryDate!);
  }

  /// Days remaining until expiration
  int get daysRemaining {
    if (expiryDate == null) return 0;
    if (isExpired) return 0;
    return expiryDate!.difference(DateTime.now()).inDays;
  }

  /// Alias for key to maintain compatibility
  String get activationKey => key;

  /// Alias for expiryDate to maintain compatibility
  DateTime? get expiresAt => expiryDate;

  License copyWith({
    String? key,
    LicenseStatus? status,
    DateTime? expiryDate,
    Map<String, dynamic>? features,
    String? owner,
    String? licenseHash,
    String? deviceId,
    DateTime? activated,
  }) {
    return License(
      key: key ?? this.key,
      status: status ?? this.status,
      expiryDate: expiryDate ?? this.expiryDate,
      features: features ?? this.features,
      owner: owner ?? this.owner,
      licenseHash: licenseHash ?? this.licenseHash,
      deviceId: deviceId ?? this.deviceId,
      activated: activated ?? this.activated,
    );
  }

  factory License.fromJson(Map<String, dynamic> json) {
    return License(
      key: json['key'] as String? ?? json['activationKey'] as String? ?? '',
      status: LicenseStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => LicenseStatus.invalid,
      ),
      expiryDate: json['expiryDate'] != null
          ? DateTime.parse(json['expiryDate'] as String)
          : json['expiresAt'] != null
              ? DateTime.parse(json['expiresAt'] as String)
              : null,
      features: json['features'] as Map<String, dynamic>?,
      owner: json['owner'] as String?,
      licenseHash: json['licenseHash'] as String?,
      deviceId: json['deviceId'] as String?,
      activated: json['activated'] != null
          ? DateTime.parse(json['activated'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'key': key,
      'activationKey': key,
      'status': status.name,
      'expiryDate': expiryDate?.toIso8601String(),
      'expiresAt': expiryDate?.toIso8601String(),
      'features': features,
      'owner': owner,
      'licenseHash': licenseHash,
      'deviceId': deviceId,
      'activated': activated?.toIso8601String(),
    };
  }
}

/// Extension for LicenseStatus descriptions
extension LicenseStatusExtension on LicenseStatus {
  String get description {
    switch (this) {
      case LicenseStatus.active:
        return 'Active';
      case LicenseStatus.valid:
        return 'Valid';
      case LicenseStatus.expired:
        return 'Expired';
      case LicenseStatus.invalid:
        return 'Invalid';
      case LicenseStatus.notFound:
        return 'Not Found';
      case LicenseStatus.notActivated:
        return 'Not Activated';
    }
  }

  bool get requiresActivation => this == LicenseStatus.notActivated;
}
