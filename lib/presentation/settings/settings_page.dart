// lib/presentation/settings/settings_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  static const Color primaryBlue = Color(0xFF1564A5);

  // Settings state (in-memory only for now)
  bool darkMode = false;
  bool notifications = true;
  bool autoSave = true;
  bool highQualityPreview = false;

  String outputFormat = 'PNG';
  String dpi = '300';
  String language = 'English';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      body: Row(
        children: [
          _buildSidebar(),
          Expanded(
            child: Column(
              children: [
                _buildTopBar(),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(30),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Settings',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.black,
                          ),
                        ),
                        const SizedBox(height: 30),

                        _buildGeneralSection(),
                        const SizedBox(height: 30),

                        _buildProcessingDefaultsSection(),
                        const SizedBox(height: 30),

                        _buildStorageSection(),
                        const SizedBox(height: 30),

                        _buildAboutSection(),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSidebar() {
    return Container(
      width: 250,
      color: Colors.white,
      child: Column(
        children: [
          _buildLogo(),
          const Divider(),
          const SizedBox(height: 10),
          _sideButton(Icons.dashboard, 'Dashboard'),
          _sideButton(Icons.folder_open, 'My Folders'),
          const Spacer(),
          const Divider(),
          _systemSection(),
          const Divider(),
          _buildProfile(),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return const SizedBox(
      height: 50,
      child: Row(
        children: [
          SizedBox(width: 8),
          DecoratedBox(
            decoration: BoxDecoration(
              color: Color(0xFF0E3182),
              borderRadius: BorderRadius.all(Radius.circular(8)),
            ),
            child: SizedBox(
              height: 35,
              width: 35,
              child: Icon(Icons.print_outlined, color: Colors.white),
            ),
          ),
          SizedBox(width: 8),
          Text(
            'Virtual Designer',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _systemSection() {
    return Column(
      children: [
        const SizedBox(height: 8),
        const Text(
          'SYSTEM',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: Colors.grey,
          ),
        ),
        const SizedBox(height: 8),
        _sideButton(Icons.person_2_rounded, 'Users'),
        _sideButton(Icons.settings, 'Settings', isActive: true),
      ],
    );
  }

  Widget _buildProfile() {
    return Padding(
      padding: const EdgeInsets.all(10),
      child: Row(
        children: [
          const Icon(Icons.person_outlined, size: 28, color: Colors.grey),
          const SizedBox(width: 8),
          const Text(
            'Administrator',
            style: TextStyle(fontWeight: FontWeight.w600),
          ),
          const Spacer(),
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.logout, size: 20, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  Widget _sideButton(IconData icon, String text, {bool isActive = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Container(
        decoration: BoxDecoration(
          color: isActive ? const Color(0xFFE3F2FD) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: ListTile(
          leading: Icon(icon, color: isActive ? primaryBlue : Colors.grey, size: 20),
          title: Text(
            text,
            style: TextStyle(
              fontWeight: FontWeight.w600,
              color: isActive ? primaryBlue : Colors.black87,
              fontSize: 14,
            ),
          ),
          dense: true,
          onTap: () {
            if (!isActive) {
              switch (text) {
                case 'Dashboard':
                  Get.toNamed('/dashboard');
                  break;
                case 'My Folders':
                  Get.toNamed('/files');
                  break;
                case 'Users':
                  Get.toNamed('/users');
                  break;
              }
            }
          },
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 30),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha((0.05 * 255).round()),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          const Text(
            'Settings',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const Spacer(),
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.notifications_none_outlined),
            color: Colors.grey,
          ),
          const SizedBox(width: 10),
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.help_outline),
            color: Colors.grey,
          ),
        ],
      ),
    );
  }

  Widget _buildGeneralSection() {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFE3F2FD),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.tune, color: Color(0xFF1976D2), size: 20),
              ),
              const SizedBox(width: 12),
              const Text(
                'General',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 25),
          _buildSwitchOption('Dark Mode', darkMode, (val) => setState(() => darkMode = val)),
          const Divider(),
          _buildSwitchOption('Notifications', notifications, (val) => setState(() => notifications = val)),
          const Divider(),
          _buildSwitchOption('Auto Save', autoSave, (val) => setState(() => autoSave = val)),
          const Divider(),
          _buildSwitchOption('High Quality Preview', highQualityPreview, (val) => setState(() => highQualityPreview = val)),
        ],
      ),
    );
  }

  Widget _buildProcessingDefaultsSection() {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFDCFCE7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.settings_outlined, color: Color(0xFF16A34A), size: 20),
              ),
              const SizedBox(width: 12),
              const Text(
                'Processing Defaults',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 25),
          _buildDropdownOption('Output Format', outputFormat, ['PNG', 'PDF', 'SVG', 'ZIP'], (val) => setState(() => outputFormat = val)),
          const Divider(),
          _buildDropdownOption('DPI', dpi, ['150', '300', '450', '600'], (val) => setState(() => dpi = val)),
          const Divider(),
          _buildDropdownOption('Language', language, ['English', 'Spanish', 'French', 'German'], (val) => setState(() => language = val)),
        ],
      ),
    );
  }

  Widget _buildStorageSection() {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.storage, color: Color(0xFFF59E0B), size: 20),
              ),
              const SizedBox(width: 12),
              const Text(
                'Storage',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 25),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Output Directory', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              Text(
                '/Documents/silk_screen_output',
                style: TextStyle(fontSize: 13, color: Colors.grey[600]),
              ),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _showClearCacheDialog(),
              icon: const Icon(Icons.delete_outline, size: 18),
              label: const Text('Clear Cache'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.red,
                side: const BorderSide(color: Colors.red),
              ),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _showResetSettingsDialog(),
              icon: const Icon(Icons.restore, size: 18),
              label: const Text('Reset All Settings'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.grey,
                side: const BorderSide(color: Colors.grey),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAboutSection() {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFF3E8FF),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.info_outline, color: Color(0xFF9333EA), size: 20),
              ),
              const SizedBox(width: 12),
              const Text(
                'About',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 25),
          const Text('App Version', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('Virtual Designer v1.1.0', style: TextStyle(fontSize: 13, color: Colors.grey)),
          const SizedBox(height: 20),
          const Text('Developer', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('Silk Screen Studio', style: TextStyle(fontSize: 13, color: Colors.grey)),
          const SizedBox(height: 20),
          const Text('License', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('Commercial License', style: TextStyle(fontSize: 13, color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _buildSwitchOption(String title, bool value, Function(bool) onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: primaryBlue,
          ),
        ],
      ),
    );
  }

  Widget _buildDropdownOption(String title, String value, List<String> options, Function(String) onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 15),
            decoration: BoxDecoration(
              color: const Color(0xFFF9FAFB),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFE5E7EB)),
            ),
            child: DropdownButton<String>(
              value: value,
              isExpanded: true,
              underline: const SizedBox(),
              items: options.map((String option) {
                return DropdownMenuItem<String>(
                  value: option,
                  child: Text(option, style: const TextStyle(fontSize: 14)),
                );
              }).toList(),
              onChanged: (String? newValue) {
                if (newValue != null) onChanged(newValue);
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showClearCacheDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Cache'),
        content: const Text('Are you sure you want to clear the cache? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Get.back();
              Get.snackbar(
                'Cache Cleared',
                'Cache has been successfully cleared.',
                snackPosition: SnackPosition.BOTTOM,
                backgroundColor: Colors.green.withAlpha((0.1 * 255).round()),
                colorText: Colors.green,
              );
            },
            child: const Text('Clear', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  void _showResetSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reset All Settings'),
        content: const Text('Are you sure you want to reset all settings to their default values?'),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Get.back();
              setState(() {
                darkMode = false;
                notifications = true;
                autoSave = true;
                highQualityPreview = false;
                outputFormat = 'PNG';
                dpi = '300';
                language = 'English';
              });
              Get.snackbar(
                'Settings Reset',
                'All settings have been restored to defaults.',
                snackPosition: SnackPosition.BOTTOM,
                backgroundColor: Colors.green.withAlpha((0.1 * 255).round()),
                colorText: Colors.green,
              );
            },
            child: const Text('Reset', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}