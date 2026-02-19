// license_model.dart — License Data Model
// Virtual Design Silk Screen Studio

class License {
  final String activationKey;
  final String licenseHash;
  final String deviceId;
  final DateTime activated;
  final DateTime expiresAt;

  const License({
    required this.activationKey,
    required this.licenseHash,
    required this.deviceId,
    required this.activated,
    required this.expiresAt,
  });

  /// Check if license has expired
  bool get isExpired => DateTime.now().isAfter(expiresAt);

  /// Get remaining days
  int get daysRemaining {
    final remaining = expiresAt.difference(DateTime.now()).inDays;
    return remaining > 0 ? remaining : 0;
  }

  /// Get expiration percentage (0-100)
  double get expirationPercentage {
    final total = expiresAt.difference(activated).inDays;
    final remaining = daysRemaining;
    if (total == 0) return 100;
    return ((total - remaining) / total) * 100;
  }

  /// Convert to JSON for storage
  Map<String, dynamic> toJson() => {
    'activationKey': activationKey,
    'licenseHash': licenseHash,
    'deviceId': deviceId,
    'activated': activated.toIso8601String(),
    'expiresAt': expiresAt.toIso8601String(),
  };

  /// Create License from JSON
  factory License.fromJson(Map<String, dynamic> json) {
    return License(
      activationKey: json['activationKey'] as String,
      licenseHash: json['licenseHash'] as String,
      deviceId: json['deviceId'] as String,
      activated: DateTime.parse(json['activated'] as String),
      expiresAt: DateTime.parse(json['expiresAt'] as String),
    );
  }

  /// Create a copy with modified fields
  License copyWith({
    String? activationKey,
    String? licenseHash,
    String? deviceId,
    DateTime? activated,
    DateTime? expiresAt,
  }) {
    return License(
      activationKey: activationKey ?? this.activationKey,
      licenseHash: licenseHash ?? this.licenseHash,
      deviceId: deviceId ?? this.deviceId,
      activated: activated ?? this.activated,
      expiresAt: expiresAt ?? this.expiresAt,
    );
  }

  @override
  String toString() => '''
License(
  activated: $activated,
  expiresAt: $expiresAt,
  daysRemaining: $daysRemaining,
  isExpired: $isExpired
)''';
}
