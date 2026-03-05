import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../preview/preview_controller.dart';
import '../../core/enums/app_enums.dart';

class SelectPrintTypeScreen extends StatelessWidget {
  const SelectPrintTypeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<PreviewController>();

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
                          'Select Print Type',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.black,
                          ),
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          'Choose the printing method that best suits your project.',
                          style: TextStyle(fontSize: 16, color: Color(0xFF6B7280)),
                        ),
                        const SizedBox(height: 30),
                        _buildPrintTypeGrid(controller),
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
          _sideButton(Icons.dashboard, 'Dashboard', () => Get.toNamed('/dashboard')),
          _sideButton(Icons.folder_open, 'My Folders', () => Get.toNamed('/files')),
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
        _sideButton(Icons.person_2_rounded, 'Users', () => Get.toNamed('/users')),
        _sideButton(Icons.settings, 'Settings', () => Get.toNamed('/settings')),
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

  Widget _sideButton(IconData icon, String text, VoidCallback? onTap) {
    final isActive = Get.currentRoute == _getRouteForText(text);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ElevatedButton.icon(
        onPressed: onTap,
        icon: Icon(icon, color: isActive ? Colors.white : const Color(0xFF1564A5)),
        label: Text(
          text,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: isActive ? Colors.white : const Color(0xFF1564A5),
          ),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: isActive ? const Color(0xFF1564A5) : Colors.white,
          elevation: 0,
          alignment: Alignment.centerLeft,
          minimumSize: const Size(double.infinity, 45),
        ),
      ),
    );
  }

  String _getRouteForText(String text) {
    switch (text) {
      case 'Dashboard':
        return '/dashboard';
      case 'My Folders':
        return '/files';
      case 'Users':
        return '/users';
      case 'Settings':
        return '/settings';
      default:
        return '';
    }
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
            'Select Print Type',
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

  Widget _buildPrintTypeGrid(PreviewController controller) {
    final printTypes = PrintType.values;
    
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 200,
        mainAxisSpacing: 20,
        crossAxisSpacing: 20,
        childAspectRatio: 0.9,
      ),
      itemCount: printTypes.length,
      itemBuilder: (context, index) {
        final type = printTypes[index];
        final isSelected = controller.selectedPrintType.value == type;
        
        return GestureDetector(
          onTap: () {
            controller.setPrintType(type);
            Get.toNamed('/export');
          },
          child: Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isSelected ? const Color(0xFF6C63FF) : const Color(0xFFE5E7EB),
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    color: isSelected 
                        ? const Color(0xFF6C63FF).withAlpha((0.1 * 255).round())
                        : const Color(0xFFF3F4F6),
                    borderRadius: BorderRadius.circular(30),
                  ),
                  child: Icon(
                    _getPrintTypeIcon(type),
                    size: 30,
                    color: isSelected ? const Color(0xFF6C63FF) : const Color(0xFF6B7280),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  _getPrintTypeName(type),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? const Color(0xFF6C63FF) : Colors.black87,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 4),
                Text(
                  _getPrintTypeDescription(type),
                  style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFF6B7280),
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  IconData _getPrintTypeIcon(PrintType type) {
    switch (type) {
      case PrintType.screenPrinting:
        return Icons.print;
      case PrintType.dtf:
        return Icons.photo_size_select_large;
      case PrintType.sublimation:
        return Icons.auto_awesome;
      case PrintType.flexVinyl:
        return Icons.content_cut;
      case PrintType.dtg:
        return Icons.brush;
    }
    // unreachable but required by analyzer
    return Icons.print;
  }

  String _getPrintTypeName(PrintType type) {
    switch (type) {
      case PrintType.screenPrinting:
        return 'Screen Printing';
      case PrintType.dtf:
        return 'DTF';
      case PrintType.sublimation:
        return 'Sublimation';
      case PrintType.flexVinyl:
        return 'Flex/Vinyl';
      case PrintType.dtg:
        return 'DTG';
    }
    // unreachable but required by analyzer
    return 'Unknown';
  }

  String _getPrintTypeDescription(PrintType type) {
    switch (type) {
      case PrintType.screenPrinting:
        return 'Traditional mesh-based printing';
      case PrintType.dtf:
        return 'Direct-to-film transfers';
      case PrintType.sublimation:
        return 'Ink into fabric fibers';
      case PrintType.flexVinyl:
        return 'Vinyl cutting & heat press';
      case PrintType.dtg:
        return 'Direct-to-garment printing';
    }
    // unreachable but required by analyzer
    return '';
  }
}
