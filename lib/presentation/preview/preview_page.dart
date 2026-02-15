// lib/presentation/preview/preview_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';

class PreviewPage extends StatelessWidget {
  const PreviewPage({super.key});

  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color sidebarBlue = Color(0xFF0E3182);

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
                  child: Padding(
                    padding: const EdgeInsets.all(30),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildProgressSteps(),
                        const SizedBox(height: 30),
                        
                        const Text(
                          'Print Preview',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.black,
                          ),
                        ),
                        const SizedBox(height: 10),
                        
                        const Text(
                          'Review your color separations and films before exporting.',
                          style: TextStyle(fontSize: 16, color: Color(0xFF6B7280)),
                        ),
                        const SizedBox(height: 30),
                        
                        Expanded(
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Main Preview Area
                              Expanded(
                                flex: 7,
                                child: _buildPreviewArea(),
                              ),
                              const SizedBox(width: 20),
                              
                              // Sidebar with layers
                              SizedBox(
                                width: 300,
                                child: _buildLayersPanel(),
                              ),
                            ],
                          ),
                        ),
                        
                        const SizedBox(height: 20),
                        _buildBottomActions(),
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

  Widget _buildPreviewArea() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        children: [
          // Preview Header
          Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFFE5E7EB))),
            ),
            child: Row(
              children: [
                const Text(
                  'Preview',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                IconButton(
                  onPressed: () {},
                  icon: const Icon(Icons.zoom_in),
                  tooltip: 'Zoom In',
                ),
                IconButton(
                  onPressed: () {},
                  icon: const Icon(Icons.zoom_out),
                  tooltip: 'Zoom Out',
                ),
                IconButton(
                  onPressed: () {},
                  icon: const Icon(Icons.fit_screen),
                  tooltip: 'Fit to Screen',
                ),
              ],
            ),
          ),
          
          // Preview Canvas
          Expanded(
            child: Container(
              margin: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFFF9FAFB),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE5E7EB)),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 200,
                      height: 200,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.1),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Icon(
                          Icons.image_outlined,
                          size: 64,
                          color: Color(0xFF9CA3AF),
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    const Text(
                      'Preview will appear here',
                      style: TextStyle(
                        fontSize: 16,
                        color: Color(0xFF6B7280),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text(
                        '28 × 35 cm @ 300 DPI',
                        style: TextStyle(
                          fontSize: 14,
                          color: Color(0xFF1E40AF),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLayersPanel() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFFE5E7EB))),
            ),
            child: Row(
              children: const [
                Icon(Icons.layers, size: 20, color: Color(0xFF6B7280)),
                SizedBox(width: 10),
                Text(
                  'Color Layers',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(15),
              children: [
                _buildLayerItem('Black', Colors.black, true),
                const SizedBox(height: 10),
                _buildLayerItem('Cyan', const Color(0xFF00BCD4), true),
                const SizedBox(height: 10),
                _buildLayerItem('Magenta', const Color(0xFFE91E63), true),
                const SizedBox(height: 10),
                _buildLayerItem('Yellow', const Color(0xFFFFC107), true),
              ],
            ),
          ),
          
          Container(
            padding: const EdgeInsets.all(15),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: Color(0xFFE5E7EB))),
            ),
            child: Column(
              children: [
                Row(
                  children: const [
                    Icon(Icons.info_outline, size: 18, color: Color(0xFF6B7280)),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '4 colors detected',
                        style: TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {},
                    icon: const Icon(Icons.download, size: 18),
                    label: const Text('Export All'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: primaryBlue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
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

  Widget _buildLayerItem(String name, Color color, bool isVisible) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAFB),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Row(
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              name,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          IconButton(
            onPressed: () {},
            icon: Icon(
              isVisible ? Icons.visibility : Icons.visibility_off,
              size: 20,
              color: const Color(0xFF6B7280),
            ),
            constraints: const BoxConstraints(),
            padding: EdgeInsets.zero,
          ),
        ],
      ),
    );
  }

  Widget _buildBottomActions() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Row(
        children: [
          OutlinedButton.icon(
            onPressed: () => Get.back(),
            icon: const Icon(Icons.arrow_back, size: 18),
            label: const Text('Back to Setup'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.grey,
              side: const BorderSide(color: Color(0xFFE5E7EB)),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
            ),
          ),
          const Spacer(),
          OutlinedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.download, size: 18),
            label: const Text('Export Films'),
            style: OutlinedButton.styleFrom(
              foregroundColor: primaryBlue,
              side: const BorderSide(color: primaryBlue),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
            ),
          ),
          const SizedBox(width: 15),
          ElevatedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.print, size: 18),
            label: const Text('Send to Print'),
            style: ElevatedButton.styleFrom(
              backgroundColor: primaryBlue,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressSteps() {
    return Row(
      children: [
        _buildStep(1, 'Upload File', true, false),
        _buildProgressLine(true),
        _buildStep(2, 'System Setup', true, false),
        _buildProgressLine(true),
        _buildStep(3, 'Print Preview', false, true),
      ],
    );
  }

  Widget _buildStep(int number, String label, bool isComplete, bool isActive) {
    return Column(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isComplete ? Colors.green : isActive ? primaryBlue : const Color(0xFFE5E7EB),
          ),
          child: Center(
            child: isComplete
                ? const Icon(Icons.check, color: Colors.white, size: 20)
                : Text(
                    '$number',
                    style: TextStyle(
                      color: isActive ? Colors.white : Colors.grey,
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
            color: isActive ? primaryBlue : Colors.grey,
          ),
        ),
      ],
    );
  }

  Widget _buildProgressLine(bool isComplete) {
    return Expanded(
      child: Container(
        height: 2,
        margin: const EdgeInsets.only(bottom: 30),
        color: isComplete ? Colors.green : const Color(0xFFE5E7EB),
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
          _sideButton(Icons.dashboard, 'Dashboard', isActive: false),
          _sideButton(Icons.tune, 'System Setup', isActive: false),
          _sideButton(Icons.preview, 'Preview', isActive: true),
          const Spacer(),
          const Divider(),
          _buildProfile(),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return const SizedBox(
      height: 60,
      child: Row(
        children: [
          SizedBox(width: 15),
          DecoratedBox(
            decoration: BoxDecoration(
              color: sidebarBlue,
              borderRadius: BorderRadius.all(Radius.circular(8)),
            ),
            child: SizedBox(
              height: 35,
              width: 35,
              child: Icon(Icons.print_outlined, color: Colors.white, size: 20),
            ),
          ),
          SizedBox(width: 10),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('PrintManager', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              Text('v2.4.0 (Desktop)', style: TextStyle(fontSize: 10, color: Colors.grey)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProfile() {
    return Padding(
      padding: const EdgeInsets.all(15),
      child: Row(
        children: [
          CircleAvatar(
            radius: 20,
            backgroundColor: const Color(0xFFFFE4E1),
            child: const Text('JD', style: TextStyle(color: Color(0xFFFF6B6B), fontWeight: FontWeight.bold)),
          ),
          const SizedBox(width: 10),
          const Text('Jane Doe', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _sideButton(IconData icon, String text, {required bool isActive}) {
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
          onTap: () {},
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
            color: Colors.black.withOpacity(0.05),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          const Text(
            'Print Preview',
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
}