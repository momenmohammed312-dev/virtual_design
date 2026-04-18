// lib/core/permissions/permission_service.dart

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';

class PermissionService {
  /// Request storage permissions
  Future<bool> requestStoragePermission() async {
    if (!Platform.isAndroid && !Platform.isIOS) {
      // Desktop platforms don't need explicit storage permission
      return true;
    }

    try {
      if (Platform.isAndroid) {
        // For Android 13+ (API 33+)
        final photos = await Permission.photos.request();
        final mediaLocation = await Permission.accessMediaLocation.request();

        if (photos.isGranted && mediaLocation.isGranted) {
          return true;
        }

        // Fallback for older Android versions
        final storage = await Permission.storage.request();
        return storage.isGranted;
      } else if (Platform.isIOS) {
        final photos = await Permission.photos.request();
        return photos.isGranted;
      }

      return false;
    } catch (e) {
      debugPrint('[PermissionService] Error requesting storage: $e');
      return false;
    }
  }

  /// Check if storage permission is granted
  Future<bool> hasStoragePermission() async {
    if (!Platform.isAndroid && !Platform.isIOS) {
      return true;
    }

    try {
      if (Platform.isAndroid) {
        final photos = await Permission.photos.status;
        final mediaLocation = await Permission.accessMediaLocation.status;

        if (photos.isGranted && mediaLocation.isGranted) {
          return true;
        }

        final storage = await Permission.storage.status;
        return storage.isGranted;
      } else if (Platform.isIOS) {
        final photos = await Permission.photos.status;
        return photos.isGranted;
      }

      return false;
    } catch (e) {
      debugPrint('[PermissionService] Error checking storage: $e');
      return false;
    }
  }

  /// Request all required permissions at once
  Future<Map<Permission, PermissionStatus>> requestAllPermissions() async {
    if (!Platform.isAndroid && !Platform.isIOS) {
      return {};
    }

    final permissions = <Permission>[
      Permission.photos,
      Permission.accessMediaLocation,
      if (Platform.isAndroid) Permission.storage,
    ];

    return await permissions.request();
  }

  /// Ensure image access permission (convenience method for upload flow)
  Future<bool> ensureImageAccess() async {
    return await requestStoragePermission();
  }
}
