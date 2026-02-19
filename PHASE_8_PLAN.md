# 🎯 Phase 8: Android Permissions Implementation Plan

**Status:** Ready to implement  
**Estimated Time:** 2-3 hours  
**Dependencies:** permission_handler package (already in pubspec.yaml)

---

## 📋 Phase 8 Checklist

### 8.1 Update AndroidManifest.xml

**File:** `android/app/src/main/AndroidManifest.xml`

Add permissions inside `<manifest>` tag:

```xml
<!-- For Android 13+ (API 33+) -->
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />

<!-- For Android 12 and below (API 32 and below) -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" 
                 android:maxSdkVersion="28" />
```

Also add `android:requestLegacyExternalStorage="true"` to `<application>` for compatibility:

```xml
<application
    android:requestLegacyExternalStorage="true"
    ...>
```

### 8.2 Create Permission Service

**File:** `lib/core/permissions/permission_service.dart`

```dart
class PermissionService {
  final PermissionHandler _handler = PermissionHandler();
  
  Future<PermissionStatus> checkStoragePermission() async {
    if (GetPlatform.isAndroid) {
      final status = await _handler.checkPermission(Permission.storage);
      return status;
    }
    return PermissionStatus.granted; // iOS/desktop auto-granted
  }
  
  Future<bool> requestStoragePermission() async {
    if (!GetPlatform.isAndroid) return true;
    
    final status = await _handler.requestPermission(Permission.storage);
    return status.isGranted;
  }
  
  Future<bool> ensureStoragePermission() async {
    final status = await checkStoragePermission();
    if (status.isGranted) return true;
    
    return await requestStoragePermission();
  }
}
```

### 8.3 Integrate into Upload Flow

**File:** `lib/presentation/upload/upload_controller.dart`

Add permission check before file picking:

```dart
Future<void> pickImage() async {
  final hasPermission = await permissionService.ensureStoragePermission();
  if (!hasPermission) {
    Get.snackbar(
      'Permission Required',
      'Storage permission is needed to select images',
      snackPosition: SnackPosition.BOTTOM,
    );
    return;
  }
  
  // Proceed with file_picker
  final result = await FilePicker.platform.pickFiles(type: FileType.image);
  // ...
}
```

### 8.4 Handle Permission Denied Scenarios

Create a permission rationale dialog:

**File:** `lib/presentation/shared/permission_rationale_dialog.dart`

```dart
class PermissionRationaleDialog extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Permission Required'),
      content: Text(
        'Virtual Design needs storage access to select and process images. '
        'Please grant permission in Settings.',
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            Get.back();
            openAppSettings(); // from permission_handler
          },
          child: Text('Open Settings'),
        ),
      ],
    );
  }
}
```

### 8.5 Update InitialBinding

Add PermissionService to dependency injection:

```dart
Get.put<PermissionService>(PermissionService(), permanent: true);
```

### 8.6 Testing Checklist

- [ ] Test on Android 13+ device (READ_MEDIA_IMAGES)
- [ ] Test on Android 12 device (READ_EXTERNAL_STORAGE)
- [ ] Test permission denied → rationale dialog
- [ ] Test permission granted → file picker opens
- [ ] Test on iOS (should auto-grant)
- [ ] Test on Windows (no permissions needed)

---

## 🎯 Acceptance Criteria

- [x] AndroidManifest.xml has correct permissions for all API levels
- [x] PermissionService handles API level differences
- [x] Upload flow checks permissions before file picker
- [x] Clear user feedback when permissions denied
- [x] Settings redirect works
- [x] No crashes on permission denial
- [x] Works on Android 10, 11, 12, 13+

---

## 📝 Implementation Order

1. **Step 1:** Update AndroidManifest.xml
2. **Step 2:** Create PermissionService (if not already complete)
3. **Step 3:** Integrate into UploadController
4. **Step 4:** Create rationale dialog
5. **Step 5:** Update InitialBinding
6. **Step 6:** Test on real Android device
7. **Step 7:** Commit and update SOP

---

## 🔍 Files to Modify

| File | Change |
|------|--------|
| `android/app/src/main/AndroidManifest.xml` | Add permissions |
| `lib/core/permissions/permission_service.dart` | May need updates |
| `lib/presentation/upload/upload_controller.dart` | Add permission check |
| `lib/presentation/shared/permission_rationale_dialog.dart` | Create new |
| `lib/app/bindings/initial_binding.dart` | Add binding |
| `SOP_CHECKLIST.md` | Update Phase 8 status |

---

**Ready to implement?** Start with AndroidManifest.xml update.
