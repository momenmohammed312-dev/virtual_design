import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:virtual_design/presentation/setup/setup_page.dart';

class UploadPage extends StatelessWidget {
  const UploadPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFE8E8E8),
      body: Column(
        children: [
          // Top Navigation Bar
          _buildTopNavigationBar(),
          
          // Main Content
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Main Content Area (80%)
                Expanded(
                  flex: 8,
                  child: _buildMainContent(context),
                ),
                
                const SizedBox(width: 10),
                
                // Sidebar Configuration (20%)
                Expanded(
                  flex: 2,
                  child: _buildSidebarConfiguration(context),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Top Navigation Bar
  Widget _buildTopNavigationBar() {
    return Container(
      width: double.infinity,
      height: 60,
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: [
          // Logo
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: const Color(0xFF4587F9),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.print_outlined,
              color: Colors.white,
              size: 24,
            ),
          ),
          const SizedBox(width: 12),
          const Text(
            'Virtua Designer',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.black,
            ),
          ),
          
          const Spacer(),
          
          // Navigation Links
          TextButton(
            onPressed: () => Get.back(),
            child: const Text(
              'Dashboard',
              style: TextStyle(
                fontSize: 16,
                color: Colors.black87,
              ),
            ),
          ),
          const SizedBox(width: 20),
          TextButton(
            onPressed: () {},
            child: const Text(
              'Jobs',
              style: TextStyle(
                fontSize: 16,
                color: Colors.black87,
              ),
            ),
          ),
          const SizedBox(width: 20),
          TextButton(
            onPressed: () {},
            child: const Text(
              'Clients',
              style: TextStyle(
                fontSize: 16,
                color: Colors.black87,
              ),
            ),
          ),
          const SizedBox(width: 20),
          TextButton(
            onPressed: () {},
            child: const Text(
              'Reports',
              style: TextStyle(
                fontSize: 16,
                color: Colors.black87,
              ),
            ),
          ),
          
          const SizedBox(width: 20),
          
          // Notifications
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.notifications_outlined),
            color: Colors.black87,
          ),
          
          const SizedBox(width: 10),
          
          // User Avatar
          const CircleAvatar(
            radius: 18,
            backgroundColor: Color(0xFFE0E0E0),
            child: Icon(Icons.person, size: 20, color: Colors.black54),
          ),
        ],
      ),
    );
  }

  /// Main Content Area
  Widget _buildMainContent(BuildContext context) {
    return Container(
      color: const Color(0xFFE8E8E8),
      padding: const EdgeInsets.all(30),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Breadcrumb
          Row(
            children: [
              TextButton(
                onPressed: () => Get.back(),
                style: TextButton.styleFrom(
                  padding: EdgeInsets.zero,
                  minimumSize: const Size(0, 0),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: const Text(
                  'Dashboard',
                  style: TextStyle(
                    fontSize: 14,
                    color: Color(0xFF6B7280),
                  ),
                ),
              ),
              const Text(
                ' / ',
                style: TextStyle(
                  fontSize: 14,
                  color: Color(0xFF6B7280),
                ),
              ),
              const Text(
                'Upload Files',
                style: TextStyle(
                  fontSize: 14,
                  color: Color(0xFF6B7280),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 20),
          
          // Title
          const Text(
            'Upload Files Center',
            style: TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: Colors.black,
            ),
          ),
          
          const SizedBox(height: 8),
          
          // Subtitle
          const Text(
            'Manage and upload your print assets securely and efficiently.',
            style: TextStyle(
              fontSize: 16,
              color: Color(0xFF6B7280),
            ),
          ),
          
          const SizedBox(height: 30),
          
          // Drag & Drop Area
          _buildDragDropArea(),
          
          const SizedBox(height: 30),
          
          // Ready to Upload Section
          const Text(
            'Ready to Upload (3 files)',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.black,
            ),
          ),
          
          const SizedBox(height: 20),
          
          // File List
          Expanded(
            child: _buildFileList(),
          ),
        ],
      ),
    );
  }

  /// Drag & Drop Area
  Widget _buildDragDropArea() {
    return Container(
      height: 300,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: const Color(0xFFE5E7EB),
          width: 2,
          style: BorderStyle.solid,
        ),
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Cloud Icon
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: const Color(0xFFEBF5FF),
                borderRadius: BorderRadius.circular(32),
              ),
              child: const Icon(
                Icons.cloud_upload_outlined,
                size: 32,
                color: Color(0xFF4587F9),
              ),
            ),
            
            const SizedBox(height: 20),
            
            // Title
            const Text(
              'Drag & Drop files here',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.black,
              ),
            ),
            
            const SizedBox(height: 10),
            
            // Subtitle
            const Text(
              'Support for PDF, DOCX, PNG. Max file size 500MB.',
              style: TextStyle(
                fontSize: 14,
                color: Color(0xFF6B7280),
              ),
            ),
            
            const SizedBox(height: 20),
            
            // Browse Files Button
            ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4587F9),
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: const Text(
                'Browse Files',
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// File List
  Widget _buildFileList() {
    return ListView(
      children: [
        _buildFileItem(
          icon: Icons.picture_as_pdf,
          iconColor: const Color(0xFFEF4444),
          fileName: 'Q3_Financial_Report.pdf',
          fileSize: '2.4 MB • PDF Document',
          progress: 0.65,
          status: '65%',
          isUploading: true,
        ),
        const SizedBox(height: 15),
        _buildFileItem(
          icon: Icons.description,
          iconColor: const Color(0xFF3B82F6),
          fileName: 'Marketing_Brief_v2.docx',
          fileSize: '450 KB • Word Document',
          progress: 1.0,
          status: 'Ready',
          isCompleted: true,
        ),
        const SizedBox(height: 15),
        _buildFileItem(
          icon: Icons.image,
          iconColor: const Color(0xFF8B5CF6),
          fileName: 'Banner_Print_Large.png',
          fileSize: '12 MB • PNG Image',
          progress: 0.0,
          status: 'Waiting...',
          isWaiting: true,
        ),
      ],
    );
  }

  /// Individual File Item
  Widget _buildFileItem({
    required IconData icon,
    required Color iconColor,
    required String fileName,
    required String fileSize,
    required double progress,
    required String status,
    bool isUploading = false,
    bool isCompleted = false,
    bool isWaiting = false,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          // File Icon
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: iconColor.withAlpha((0.1 * 255).round()),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              icon,
              color: iconColor,
              size: 24,
            ),
          ),
          
          const SizedBox(width: 16),
          
          // File Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  fileName,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.black,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  fileSize,
                  style: const TextStyle(
                    fontSize: 14,
                    color: Color(0xFF6B7280),
                  ),
                ),
                if (isUploading || isWaiting) ...[
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: progress,
                    backgroundColor: const Color(0xFFE5E7EB),
                    valueColor: AlwaysStoppedAnimation<Color>(
                      isUploading ? const Color(0xFF4587F9) : const Color(0xFFE5E7EB),
                    ),
                  ),
                ],
              ],
            ),
          ),
          
          const SizedBox(width: 16),
          
          // Status
          if (isCompleted)
            Row(
              children: const [
                Icon(Icons.check_circle, color: Color(0xFF10B981), size: 20),
                SizedBox(width: 8),
                Text(
                  'Ready',
                  style: TextStyle(
                    fontSize: 14,
                    color: Color(0xFF10B981),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            )
          else
            Text(
              status,
              style: TextStyle(
                fontSize: 14,
                color: isWaiting ? const Color(0xFF6B7280) : const Color(0xFF4587F9),
                fontWeight: FontWeight.w600,
              ),
            ),
          
          const SizedBox(width: 16),
          
          // Delete Button
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.close, size: 20),
            color: const Color(0xFF6B7280),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }

  /// Sidebar Configuration
  Widget _buildSidebarConfiguration(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.all(20),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
          // Header
          Row(
            children: const [
              Icon(Icons.tune, size: 20, color: Colors.black),
              SizedBox(width: 8),
              Text(
                'Upload Configuration',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.black,
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 8),
          
          const Text(
            'Set destinations and processing rules.',
            style: TextStyle(
              fontSize: 14,
              color: Color(0xFF6B7280),
            ),
          ),
          
          const SizedBox(height: 20),
          
          const Divider(thickness: 1, color: Color(0xFFE5E7EB)),
          
          const SizedBox(height: 20),
          
          // Destination Folder
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Destination Folder',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.black,
                ),
              ),
              TextButton(
                onPressed: () {},
                style: TextButton.styleFrom(
                  padding: EdgeInsets.zero,
                  minimumSize: const Size(0, 0),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: const Text(
                  'Change',
                  style: TextStyle(
                    fontSize: 14,
                    color: Color(0xFF4587F9),
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 10),
          
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFF3F4F6),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: const [
                Icon(Icons.folder_outlined, size: 20, color: Color(0xFF6B7280)),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '/Production/Q4_Prints/',
                    style: TextStyle(
                      fontSize: 14,
                      color: Color(0xFF374151),
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 25),
          
          // Color Mode
          const Text(
            'Color Mode',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.black,
            ),
          ),
          
          const SizedBox(height: 12),
          
          Row(
            children: [
              Expanded(
                child: _buildColorModeButton('CMYK', 'For Print', isSelected: true),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildColorModeButton('RGB', 'Digital', isSelected: false),
              ),
            ],
          ),
          
          const SizedBox(height: 25),
          
          // Print Type Selection
          const Text(
            'Print Type',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.black,
            ),
          ),
          
          const SizedBox(height: 12),
          
          _buildPrintTypeOption('Silk Screen', isActive: true),
          const SizedBox(height: 10),
          _buildPrintTypeOption('DTF', isComingSoon: true),
          const SizedBox(height: 10),
          _buildPrintTypeOption('Offset Printing', isComingSoon: true),
          const SizedBox(height: 10),
          _buildPrintTypeOption('Digital Printing', isComingSoon: true),
          
          const SizedBox(height: 25),
          
          // Processing Options
          const Text(
            'Processing Options',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.black,
            ),
          ),
          
          const SizedBox(height: 15),
          
          _buildToggleOption(
            'Auto-Convert to PDF',
            'Ensure compatibility',
            true,
          ),
          
          const SizedBox(height: 15),
          
          const Spacer(),
          
          // Info Box
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: const [
                Icon(Icons.info_outline, size: 20, color: Color(0xFF3B82F6)),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Files will be automatically scanned for print margins before processing.',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF1E40AF),
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 20),
          
          // Start Upload Button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                Get.to(() => const SetupPage());
              },
              icon: const Icon(Icons.rocket_launch, size: 20),
              label: const Text(
                'Start All Uploads',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4587F9),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Color Mode Button
  Widget _buildColorModeButton(String title, String subtitle, {required bool isSelected}) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isSelected ? const Color(0xFFEFF6FF) : Colors.white,
        border: Border.all(
          color: isSelected ? const Color(0xFF4587F9) : const Color(0xFFE5E7EB),
          width: 2,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: isSelected ? const Color(0xFF4587F9) : Colors.black,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: TextStyle(
              fontSize: 12,
              color: isSelected ? const Color(0xFF4587F9) : const Color(0xFF6B7280),
            ),
          ),
        ],
      ),
    );
  }

  /// Print Type Option
  Widget _buildPrintTypeOption(String title, {bool isActive = false, bool isComingSoon = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: isActive ? const Color(0xFFEFF6FF) : const Color(0xFFF9FAFB),
        border: Border.all(
          color: isActive ? const Color(0xFF4587F9) : const Color(0xFFE5E7EB),
          width: isActive ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            isActive ? Icons.check_circle : Icons.radio_button_unchecked,
            size: 20,
            color: isActive ? const Color(0xFF4587F9) : const Color(0xFF9CA3AF),
          ),
          const SizedBox(width: 10),
          Text(
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
              color: isActive ? const Color(0xFF4587F9) : Colors.black,
            ),
          ),
          if (isComingSoon) ...[
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF3C7),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'Coming Soon',
                style: TextStyle(
                  fontSize: 10,
                  color: Color(0xFF92400E),
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// Toggle Option
  Widget _buildToggleOption(String title, String subtitle, bool isEnabled) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.black,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF6B7280),
                ),
              ),
            ],
          ),
        ),
        Switch(
          value: isEnabled,
          onChanged: (value) {},
          activeThumbColor: const Color(0xFF4587F9),
        ),
      ],
    );
  }
}