import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../presentation/upload/upload_controller.dart';
import '../dashboard/dashboard_controller.dart';
import '../../domain/entities/print_project.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final TextEditingController _searchController = TextEditingController();
  late final DashboardController controller;

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
    required double width,
    required double height,
    required Color color,
    required Widget child,
    bool isClickable = true,
    VoidCallback? onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: isClickable ? onTap ?? () {} : null,
        splashColor: primaryBlue.withAlpha((0.2 * 255).round()),
        highlightColor: primaryBlue.withAlpha((0.1 * 255).round()),
        child: Ink(
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withAlpha((0.05 * 255).round()),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: SizedBox(
            width: width,
            height: height,
            child: child,
          ),
        ),
      ),
    );
  }

  // ================= Build =================
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFECECEC),
      body: SafeArea(
        child: Row(
          children: [
            _buildSidebar(),
            Expanded(
              child: Column(
                children: [
                  _buildTopBar(),
                  const SizedBox(height: 20),
                  
                  // ================= Statistics Cards =================
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: SizedBox(
                      height: MediaQuery.of(context).size.height * 0.24,
                      child: Obx(() {
                        if (controller.isLoading.value) {
                          return const Center(child: CircularProgressIndicator());
                        }
                        return ListView(
                          scrollDirection: Axis.horizontal,
                          children: [
                            clickableContainer(
                              width: MediaQuery.of(context).size.width * 0.17,
                              height: MediaQuery.of(context).size.height * 0.24,
                              color: Colors.white,
                              isClickable: false,
                              child: Padding(
                                padding: const EdgeInsets.only(top: 35, left: 22),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 38,
                                      height: 38,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(10),
                                        color: const Color.fromARGB(70, 55, 155, 237),
                                      ),
                                      child: const Icon(
                                        Icons.print_outlined,
                                        size: 23,
                                        color: Color.fromARGB(154, 18, 98, 163),
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    const Text(
                                      'Total Print',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                        color: Color.fromARGB(255, 72, 72, 72),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Obx(() => Text(
                                          controller.totalProjects.value.toString(),
                                          style: const TextStyle(
                                            fontSize: 25,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        )),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 15),
                            clickableContainer(
                              width: MediaQuery.of(context).size.width * 0.17,
                              height: MediaQuery.of(context).size.height * 0.24,
                              color: Colors.white,
                              isClickable: false,
                              child: Padding(
                                padding: const EdgeInsets.only(top: 35, left: 22),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 38,
                                      height: 38,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(10),
                                        color: const Color.fromARGB(70, 237, 182, 55),
                                      ),
                                      child: const Icon(
                                        Icons.pending_actions_outlined,
                                        size: 23,
                                        color: Color.fromARGB(154, 232, 129, 4),
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    const Text(
                                      'Pending Jobs',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                        color: Color.fromARGB(255, 72, 72, 72),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Obx(() => Text(
                                          controller.pendingCount.toString(),
                                          style: const TextStyle(
                                            fontSize: 25,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        )),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 15),
                            clickableContainer(
                              width: MediaQuery.of(context).size.width * 0.17,
                              height: MediaQuery.of(context).size.height * 0.24,
                              color: Colors.white,
                              isClickable: false,
                              child: Padding(
                                padding: const EdgeInsets.only(top: 35, left: 22),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 38,
                                      height: 38,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(10),
                                        color: const Color.fromARGB(70, 55, 237, 83),
                                      ),
                                      child: const Icon(
                                        Icons.check_circle_outline,
                                        size: 23,
                                        color: Color.fromARGB(154, 0, 200, 17),
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    const Text(
                                      'Complete',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                        color: Color.fromARGB(255, 72, 72, 72),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Obx(() => Text(
                                          controller.totalFilms.value.toString(),
                                          style: const TextStyle(
                                            fontSize: 25,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        )),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 15),
                            clickableContainer(
                              width: MediaQuery.of(context).size.width * 0.17,
                              height: MediaQuery.of(context).size.height * 0.24,
                              color: Colors.white,
                              isClickable: false,
                              child: Padding(
                                padding: const EdgeInsets.only(top: 35, left: 22),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 38,
                                      height: 38,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(10),
                                        color: const Color.fromARGB(70, 237, 66, 4),
                                      ),
                                      child: const Icon(
                                        Icons.storage_outlined,
                                        size: 23,
                                        color: Color.fromARGB(154, 232, 129, 4),
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    const Text(
                                      'Storage Used',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                        color: Color.fromARGB(255, 72, 72, 72),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Obx(() => Text(
                                          controller.storageUsed.value,
                                          style: const TextStyle(
                                            fontSize: 20,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        )),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        );
                      }),
                    ),
                  ),

                  const SizedBox(height: 30),

                  // ================= Quick Actions Title =================
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Quick Actions',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 15),

                  // ================= Quick Actions Cards =================
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: SizedBox(
                      height: MediaQuery.of(context).size.height * 0.19,
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        children: [
                          clickableContainer(
                            width: MediaQuery.of(context).size.width * 0.17,
                            height: MediaQuery.of(context).size.height * 0.19,
                            color: Colors.white,
                            onTap: () => Get.toNamed('/upload'),
                            child: Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    width: 48,
                                    height: 48,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(50),
                                      color: const Color.fromARGB(70, 104, 117, 214),
                                    ),
                                    child: const Icon(
                                      Icons.add,
                                      size: 28,
                                      color: Color.fromARGB(200, 69, 135, 249),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  const Text(
                                    'New Print Job',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w500,
                                      color: Colors.black87,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 15),
                          clickableContainer(
                            width: MediaQuery.of(context).size.width * 0.17,
                            height: MediaQuery.of(context).size.height * 0.19,
                            color: Colors.white,
                            onTap: () async {
                              // Get UploadController and directly pick file
                              final uploadController = Get.put(UploadController());
                              await uploadController.pickFile();
                            },
                            child: Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    width: 48,
                                    height: 48,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(50),
                                      color: const Color.fromARGB(70, 104, 117, 214),
                                    ),
                                    child: const Icon(
                                      Icons.cloud_upload_outlined,
                                      size: 28,
                                      color: Color.fromARGB(200, 69, 135, 249),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  const Text(
                                    'Upload File',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w500,
                                      color: Colors.black87,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 30),

                  // ================= Recent Projects =================
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Recent Projects',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 15),
                          Expanded(
                            child: Obx(() {
                              if (controller.isLoading.value) {
                                return Container(
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Center(
                                    child: CircularProgressIndicator(),
                                  ),
                                );
                              }

                              if (controller.recentProjects.isEmpty) {
                                return Container(
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      const Icon(
                                        Icons.folder_open,
                                        size: 64,
                                        color: Colors.grey,
                                      ),
                                      const SizedBox(height: 16),
                                      const Text(
                                        'No recent projects',
                                        style: TextStyle(
                                          color: Colors.grey,
                                          fontSize: 16,
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      ElevatedButton.icon(
                                        onPressed: () => Get.toNamed('/upload'),
                                        icon: const Icon(Icons.add_circle_outline),
                                        label: const Text('Start New Project'),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: const Color(0xFF6C63FF),
                                          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }

                              return Container(
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: GridView.builder(
                                  shrinkWrap: true,
                                  physics: const NeverScrollableScrollPhysics(),
                                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                                    maxCrossAxisExtent: 280,
                                    mainAxisSpacing: 20,
                                    crossAxisSpacing: 20,
                                    childAspectRatio: 0.75,
                                  ),
                                  itemCount: controller.recentProjects.length,
                                  itemBuilder: (context, index) {
                                    final project = controller.recentProjects[index];
                                    return _buildRecentProjectCard(project);
                                  },
                                ),
                              );
                            }),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ================= Sidebar =================
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
              color: sidebarBlue,
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
        icon: Icon(icon, color: isActive ? Colors.white : primaryBlue),
        label: Text(
          text,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: isActive ? Colors.white : primaryBlue,
          ),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: isActive ? primaryBlue : Colors.white,
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

  // ================= Recent Project Card (16:9) =================
  Widget _buildRecentProjectCard(PrintProject project) {
    final statusColor = project.status == ProjectStatus.completed
        ? Colors.green
        : project.status == ProjectStatus.processing
            ? Colors.blue
            : Colors.red;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Thumbnail with 16:9 aspect ratio
          ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: Container(
                color: const Color(0xFFF0F0F0),
                child: const Center(
                  child: Icon(Icons.image, size: 48, color: Colors.grey),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  project.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        project.createdAt.toString().split(' ')[0],
                        style: const TextStyle(
                          color: Colors.white54,
                          fontSize: 11,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: statusColor.withAlpha((0.15 * 255).round()),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        project.status == ProjectStatus.completed
                            ? 'Complete'
                            : project.status == ProjectStatus.processing
                                ? 'Processing'
                                : 'Failed',
                        style: TextStyle(
                          fontSize: 10,
                          color: statusColor,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ================= Top Bar =================
  Widget _buildTopBar() {
    return Container(
      height: 50,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      color: Colors.white,
      child: Row(
        children: [
          const Text(
            'Dashboard Overview',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const Spacer(),
          SizedBox(
            width: 320,
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search...',
                filled: true,
                fillColor: const Color(0xFFECECEC),
                contentPadding:
                    const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                  borderSide: BorderSide.none,
                ),
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: _searchController.clear,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}