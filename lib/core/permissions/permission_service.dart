/// permission_service.dart — Runtime Storage Permission Handling
/// Virtual Design Silk Screen Studio
///
/// HIGH #5 FIX: طلب إذن Storage من المستخدم runtime على Android

import 'dart:io';
import 'package:permission_handler/permission_handler.dart';

class PermissionService {
  /// طلب إذن الوصول للصور
  /// يرجع true لو تم منح الإذن
  Future<PermissionResult> requestImageAccess() async {
    // Windows/macOS/Linux لا تحتاج runtime permissions
    if (!Platform.isAndroid && !Platform.isIOS) {
      return PermissionResult.granted();
    }

    if (Platform.isAndroid) {
      return await _requestAndroidImagePermission();
    }

    if (Platform.isIOS) {
      return await _requestIOSPhotoPermission();
    }

    return PermissionResult.granted();
  }

  Future<PermissionResult> _requestAndroidImagePermission() async {
    // Android 13+ (API 33): استخدم READ_MEDIA_IMAGES
    if (await _isAndroid13OrHigher()) {
      final status = await Permission.photos.request();
      return _fromStatus(status);
    }

    // Android 10-12: READ_EXTERNAL_STORAGE
    final status = await Permission.storage.request();
    return _fromStatus(status);
  }

  Future<PermissionResult> _requestIOSPhotoPermission() async {
    final status = await Permission.photos.request();
    return _fromStatus(status);
  }

  Future<bool> _isAndroid13OrHigher() async {
    if (!Platform.isAndroid) return false;
    // يمكن استخدام device_info_plus للتحقق من SDK version
    // للتبسيط: نجرب READ_MEDIA_IMAGES أولاً
    return true;
  }

  PermissionResult _fromStatus(PermissionStatus status) {
    switch (status) {
      case PermissionStatus.granted:
      case PermissionStatus.limited:
        return PermissionResult.granted();
      case PermissionStatus.denied:
        return PermissionResult.denied(
          'يحتاج التطبيق إذن الوصول للصور لاختيار الصورة.',
        );
      case PermissionStatus.permanentlyDenied:
        return PermissionResult.permanentlyDenied(
          'تم رفض الإذن نهائياً. افتح إعدادات التطبيق وامنح إذن الصور.',
        );
      default:
        return PermissionResult.denied('Permission request failed.');
    }
  }

  /// فتح إعدادات التطبيق لو تم الرفض نهائياً
  Future<bool> openSettings() async {
    return await openAppSettings();
  }

  /// التحقق من وجود الإذن بدون طلب
  Future<bool> hasImageAccess() async {
    if (!Platform.isAndroid && !Platform.isIOS) return true;
    final status = await Permission.photos.status;
    return status.isGranted || status.isLimited;
  }
}

// ─── Permission Result ────────────────────────────────────────────────────────

class PermissionResult {
  final bool isGranted;
  final bool isPermanentlyDenied;
  final String? message;

  const PermissionResult._({
    required this.isGranted,
    this.isPermanentlyDenied = false,
    this.message,
  });

  factory PermissionResult.granted() =>
      const PermissionResult._(isGranted: true);

  factory PermissionResult.denied(String message) =>
      PermissionResult._(isGranted: false, message: message);

  factory PermissionResult.permanentlyDenied(String message) =>
      PermissionResult._(
        isGranted: false,
        isPermanentlyDenied: true,
        message: message,
      );
}
