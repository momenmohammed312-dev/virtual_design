import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Note: Ensure shared_preferences is added to pubspec.yaml dependencies

/// Provider for managing app settings with persistence.
/// Stores settings using SharedPreferences and notifies listeners on changes.
class SettingsProvider extends GetxController {
  static const String _kDarkMode = 'dark_mode';
  static const String _kHighQualityPreview = 'high_quality_preview';
  static const String _kLanguage = 'language';
  static const String _kDeveloperName = 'developer_name';
  
  // Default values as per requirements
  static const bool defaultDarkMode = true;
  static const bool defaultHighQualityPreview = true;
  static const String defaultLanguage = 'English';
  static const String defaultDeveloperName = 'M02';

  // Current settings
  final RxBool darkMode = defaultDarkMode.obs;
  final RxBool highQualityPreview = defaultHighQualityPreview.obs;
  final RxString language = defaultLanguage.obs;
  final RxString developerName = defaultDeveloperName.obs;

  @override
  void onInit() {
    super.onInit();
    loadSettings();
  }

  /// Load settings from SharedPreferences
  Future<void> loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      darkMode.value = prefs.getBool(_kDarkMode) ?? defaultDarkMode;
      highQualityPreview.value = prefs.getBool(_kHighQualityPreview) ?? defaultHighQualityPreview;
      language.value = prefs.getString(_kLanguage) ?? defaultLanguage;
      developerName.value = prefs.getString(_kDeveloperName) ?? defaultDeveloperName;
    } catch (e) {
      // If loading fails, use defaults
      darkMode.value = defaultDarkMode;
      highQualityPreview.value = defaultHighQualityPreview;
      language.value = defaultLanguage;
      developerName.value = defaultDeveloperName;
    }
  }

  /// Save dark mode setting
  Future<void> setDarkMode(bool value) async {
    darkMode.value = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kDarkMode, value);
  }

  /// Save high quality preview setting
  Future<void> setHighQualityPreview(bool value) async {
    highQualityPreview.value = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kHighQualityPreview, value);
  }

  /// Save language setting
  Future<void> setLanguage(String value) async {
    language.value = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kLanguage, value);
  }

  /// Reset all settings to defaults
  Future<void> resetToDefaults() async {
    darkMode.value = defaultDarkMode;
    highQualityPreview.value = defaultHighQualityPreview;
    language.value = defaultLanguage;
    developerName.value = defaultDeveloperName;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kDarkMode, defaultDarkMode);
    await prefs.setBool(_kHighQualityPreview, defaultHighQualityPreview);
    await prefs.setString(_kLanguage, defaultLanguage);
    await prefs.setString(_kDeveloperName, defaultDeveloperName);
  }
}
