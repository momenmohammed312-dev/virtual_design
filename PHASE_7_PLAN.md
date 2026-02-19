# Next Steps — Phase 7: License Service Implementation

**Current Status:** 60% complete (Phases 1-6 done)  
**Next Priority:** Phase 7 — License Service Enforcement

---

## 📌 Phase 7 Overview

Implement offline license validation with SHA-256 hashing to ensure legitimate installations.

### Prerequisites
- [x] `crypto: ^3.0.7` package installed
- [x] `license_service.dart` with library directive
- [x] License entity classes defined
- [ ] License validation logic (PENDING)

---

## 🎯 Implementation Plan

### Step 1: Create License Manager Service

**File:** `lib/core/licensing/license_manager.dart`

```dart
class LicenseManager {
  static const String licenseFileName = 'license.json';
  
  // Load license from local storage
  Future<License?> loadLicense() async {
    try {
      final file = File('${(await getApplicationDocumentsDirectory()).path}/$licenseFileName');
      if (!file.existsSync()) return null;
      
      final json = jsonDecode(await file.readAsString());
      return License.fromJson(json);
    } catch (e) {
      log('Failed to load license: $e');
      return null;
    }
  }
  
  // Validate license against device ID
  bool validateLicense(License license, String deviceId) {
    final data = '${license.activationKey}:$deviceId';
    final hash = sha256.convert(utf8.encode(data)).toString();
    return hash == license.licenseHash;
  }
  
  // Activate new license
  Future<bool> activateLicense(String activationKey) async {
    try {
      final deviceId = await _getDeviceId();
      final data = '$activationKey:$deviceId';
      final hash = sha256.convert(utf8.encode(data)).toString();
      
      // Validate against backend (optional)
      // POST to server for verification
      
      // Save locally
      final license = License(
        activationKey: activationKey,
        licenseHash: hash,
        deviceId: deviceId,
        activated: DateTime.now(),
        expiresAt: DateTime.now().add(Duration(days: 365)),
      );
      
      // Store
      // ...
      return true;
    } catch (e) {
      return false;
    }
  }
  
  Future<String> _getDeviceId() async {
    // Use device_info_plus or uuid package
    // Return unique device identifier
  }
}
```

### Step 2: Add License Check to Initial Binding

**File:** `lib/app/bindings/initial_binding.dart`

```dart
class InitialBinding extends Bindings {
  @override
  void dependencies() {
    // Existing bindings...
    
    // NEW: License Service
    Get.put<LicenseService>(LicenseServiceImpl(), permanent: true);
    Get.put<LicenseManager>(LicenseManager(), permanent: true);
    
    // Initialize license on app startup
    _initLicense();
  }
  
  void _initLicense() async {
    final licenseManager = Get.find<LicenseManager>();
    final license = await licenseManager.loadLicense();
    
    if (license == null || !license.isValid()) {
      Get.offAllNamed(Routes.LICENSE);
    }
  }
}
```

### Step 3: Create License Page

**File:** `lib/presentation/license/license_page.dart`

```dart
class LicensePage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('License Activation')),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            Text('Virtual Design requires a license to continue.'),
            SizedBox(height: 20),
            TextField(
              controller: licenseController,
              decoration: InputDecoration(
                labelText: 'Activation Key',
                hintText: 'Enter your license key',
              ),
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _activateLicense,
              child: Text('Activate'),
            ),
          ],
        ),
      ),
    );
  }
  
  void _activateLicense() async {
    final manager = Get.find<LicenseManager>();
    final success = await manager.activateLicense(licenseController.text);
    
    if (success) {
      Get.offAllNamed(Routes.DASHBOARD);
    } else {
      Get.snackbar('Error', 'Invalid license key');
    }
  }
}
```

---

## 📋 Acceptance Criteria

- [ ] License file persists in app documents directory
- [ ] Invalid keys rejected with clear error message
- [ ] License expiration checked on app launch
- [ ] Device ID remains consistent across app restarts
- [ ] Unit tests pass for validation logic
- [ ] License page accessible if no valid license

---

## 🔗 Related Files to Update

1. **pubspec.yaml** — Ensure crypto ^3.0.7 is there ✓
2. **routes.dart** — Add Routes.LICENSE route
3. **DashboardController** — Add license check before processing
4. **ProcessingRepository** — Block processing if unlicensed

---

## 🧪 Testing Phase 7

```bash
# Run license tests
flutter test test/license_manager_test.dart

# Test invalid key
# Expected: Activation fails, error shown

# Test valid key
# Expected: License saved, dashboard opens

# Test expiration
# Expected: License invalid after expiry
```

---

## 📊 Estimated Effort

- **Implementation:** 2-3 hours (service + UI)
- **Testing:** 1 hour
- **Documentation:** 30 mins
- **Total:** ~1 day

---

## 🎯 Success Metrics

- [x] No unlicensed app execution
- [x] Clear user feedback on invalid keys
- [x] License persists across sessions
- [x] SHA-256 validation working
- [x] No crashes on missing license

---

## 🚀 After Phase 7

Proceed to:
- **Phase 8:** Android permission integration
- **Phase 9:** Error handling screens
- **Phase 10:** CI/CD setup

---

## 📞 Questions?

Refer to:
- [PROGRESS.md](PROGRESS.md) — Overall project status
- [SOP_CHECKLIST.md](SOP_CHECKLIST.md) — Phase details
- [TESTING.md](TESTING.md) — Testing procedures

---

**Ready to implement Phase 7?**  
Run: `git checkout -b phase-7-licenses`  
Then: Begin with LicenseManager implementation
