// sound_manager.dart — Play notification sounds on process completion
// Uses system sounds as fallback, can be extended with custom audio files

import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

class SoundManager {
  static final SoundManager _instance = SoundManager._internal();
  factory SoundManager() => _instance;
  SoundManager._internal();

  bool _enabled = true;

  bool get enabled => _enabled;
  set enabled(bool value) => _enabled = value;

  /// Play a success/completion notification sound
  Future<void> playDone() async {
    if (!_enabled) return;
    try {
      // System notification sound — works on all platforms without needing audio files
      SystemSound.play(SystemSoundType.alert);
    } catch (e) {
      debugPrint('[SoundManager] Could not play done sound: $e');
    }
  }

  /// Play an error notification sound
  Future<void> playError() async {
    if (!_enabled) return;
    try {
      SystemSound.play(SystemSoundType.alert);
    } catch (e) {
      debugPrint('[SoundManager] Could not play error sound: $e');
    }
  }

  /// Play a click/tap feedback sound
  Future<void> playClick() async {
    if (!_enabled) return;
    try {
      SystemSound.play(SystemSoundType.click);
    } catch (e) {
      debugPrint('[SoundManager] Could not play click sound: $e');
    }
  }
}