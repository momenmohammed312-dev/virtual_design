import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:virtual_design/core/utils/responsive.dart';
import 'package:virtual_design/presentation/dashboard/dashboard_controller.dart';
import 'package:virtual_design/domain/entities/print_project.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final TextEditingController _searchController = TextEditingController();
  late final DashboardController controller;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color sidebarBlue = Color(0xFF0E3182);

  @override
  void initState() {
    super.initState();
    controller = Get.find<DashboardController>();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  // ================= Clickable Container =================
  Widget clickableContainer({
    required Widget child,
    double? width,
    double? height,
    Color color = Colors.white,
    bool isClickable = true,
    VoidCallback? onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: isClickable ? onTap ?? () {} : null,
        child: Ink(
          width: width,
          height: height,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withAlpha(12),
                blurRadius: 8,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }

  // ================= Build =================
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: const Color(0xFFF5F7FB),
      drawer: context.isDesktop ? null : Drawer(child: _buildSidebar()),
      body: SafeArea(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (context.isDesktop) _buildSidebar(),
            Expanded(
              child: Column(
                children: [
                  _buildTopBar(),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 24, vertical: 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildStatisticsGrid(),
                          const SizedBox(height: 32),
                          const Text(
                            'Quick Actions',
                            style: TextStyle(
                                fontSize: 20, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 16),
                          _buildQuickActions(),
                          const SizedBox(height: 32),
                          const Text(
                            'Recent Projects',
                            style: TextStyle(
                                fontSize: 20, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 16),
                          _buildProjectsGrid(),
                          const SizedBox(height: 40),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Color(0xFFEEEEEE))),
      ),
      child: Row(
        children: [
          if (!context.isDesktop)
            IconButton(
              icon: const Icon(Icons.menu),
              onPressed: () => _scaffoldKey.currentState?.openDrawer(),
            ),
          const SizedBox(width: 8),
          const Text(
            'Dashboard',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const Spacer(),
          Flexible(
            child: SizedBox(
              width: context.isMobile ? 150 : 300,
              child: TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  hintText: 'Search projects...',
                  prefixIcon: const Icon(Icons.search, size: 20),
                  contentPadding: const EdgeInsets.symmetric(vertical: 0),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide.none,
                  ),
                  filled: true,
                  fillColor: const Color(0xFFF0F2F5),
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          IconButton(
            icon: const Icon(Icons.notifications_none_outlined),
            onPressed: () {},
          ),
        ],
      ),
    );
  }

  Widget _buildStatisticsGrid() {
    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(child: CircularProgressIndicator());
      }
      // Adaptive grid layout: 1 column on small mobile, 2 on tablet, 4 on desktop
      int crossAxisCount =
          context.screenWidth < 600 ? 2 : (context.screenWidth < 1000 ? 2 : 4);
      double aspectRatio = context.screenWidth < 600 ? 2.0 : 1.6;

      return GridView.count(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisCount: crossAxisCount,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: aspectRatio,
        children: [
          _statCard('Total Jobs', controller.totalProjects.value.toString(),
              Icons.print_outlined, Colors.blue),
          _statCard('Pending', controller.pendingCount.toString(),
              Icons.pending_actions_outlined, Colors.orange),
          _statCard('Complete', controller.totalFilms.value.toString(),
              Icons.check_circle_outline, Colors.green),
          _statCard('Storage', controller.storageUsed.value,
              Icons.storage_outlined, Colors.purple),
        ],
      );
    });
  }

  Widget _statCard(String title, String value, IconData icon, Color color) {
    return clickableContainer(
      isClickable: false,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 6),
            Text(title,
                style: const TextStyle(fontSize: 11, color: Colors.black54),
                overflow: TextOverflow.ellipsis),
            Text(value,
                style:
                    const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActions() {
    return Wrap(
      spacing: 16,
      runSpacing: 16,
      children: [
        _actionButton('New Project', Icons.add, () => Get.toNamed('/upload')),
        _actionButton('Import URL', Icons.link, () {
          _showImportUrlDialog();
        }),
      ],
    );
  }

  Widget _actionButton(String label, IconData icon, VoidCallback onTap) {
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icon),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: primaryBlue,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  Widget _buildProjectsGrid() {
    return Obx(() {
      if (controller.recentProjects.isEmpty) {
        return const Center(
            child: Padding(
          padding: EdgeInsets.all(40),
          child: Text('No projects found'),
        ));
      }
      return GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
          maxCrossAxisExtent: 300,
          mainAxisSpacing: 20,
          crossAxisSpacing: 20,
          childAspectRatio: 0.8,
        ),
        itemCount: controller.recentProjects.length,
        itemBuilder: (context, index) =>
            _buildRecentProjectCard(controller.recentProjects[index]),
      );
    });
  }

  Widget _buildRecentProjectCard(PrintProject project) {
    return clickableContainer(
      onTap: () => Get.toNamed('/project-details', arguments: project),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFFF0F2F5),
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(12)),
              ),
              child: const Icon(Icons.image, color: Colors.grey, size: 40),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(project.name,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 4),
                Text('Status: ${project.status.name}',
                    style:
                        const TextStyle(fontSize: 12, color: Colors.black54)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSidebar() {
    return Container(
      width: 260,
      height: double.infinity,
      color: Colors.white,
      child: Column(
        children: [
          _buildLogo(),
          const Divider(height: 1),
          const SizedBox(height: 20),
          _sideButton(Icons.dashboard_rounded, 'Dashboard', () {}),
          _sideButton(
              Icons.folder_rounded, 'My Projects', () => Get.toNamed('/files')),
          _sideButton(Icons.settings_rounded, 'Settings',
              () => Get.toNamed('/settings')),
          const Spacer(),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text('MO2 CAPITAL',
                style: TextStyle(
                    color: Colors.grey.shade400,
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 1.5)),
          ),
          _buildProfile(),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                  colors: [Color(0xFF1564A5), Color(0xFF0E3182)]),
              borderRadius: BorderRadius.circular(8),
            ),
            child:
                const Icon(Icons.print_rounded, color: Colors.white, size: 24),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text('Virtual Designer',
                style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    color: sidebarBlue)),
          ),
        ],
      ),
    );
  }

  Widget _buildProfile() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          const CircleAvatar(
            backgroundColor: Color(0xFFE3F2FD),
            child: Icon(Icons.admin_panel_settings,
                color: Color(0xFF1564A5), size: 22),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Admin',
                    style:
                        TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                Text('admin@virtualdesigner.app',
                    style: TextStyle(fontSize: 11, color: Colors.grey)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sideButton(IconData icon, String title, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        onTap: onTap,
        leading: Icon(icon, color: Colors.black54),
        title: Text(title, style: const TextStyle(color: Colors.black87)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  void _showImportUrlDialog() {
    final urlController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.link, color: Color(0xFF1564A5)),
            SizedBox(width: 10),
            Text('Import from URL'),
          ],
        ),
        content: SizedBox(
          width: 400,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Enter the URL of the image you want to import for processing.',
                style: TextStyle(fontSize: 13, color: Colors.black54),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: urlController,
                decoration: InputDecoration(
                  hintText: 'https://example.com/design.png',
                  prefixIcon: const Icon(Icons.language, size: 20),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                  filled: true,
                  fillColor: const Color(0xFFF5F7FB),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              final url = urlController.text.trim();
              if (url.isNotEmpty) {
                Navigator.of(ctx).pop();
                // Navigate to upload page with the URL
                Get.toNamed(
                  '/upload',
                  arguments: {'importUrl': url},
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: primaryBlue,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8)),
            ),
            child: const Text('Import'),
          ),
        ],
      ),
    );
  }
}
