// lib/presentation/files/files_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';

class FilesPage extends StatefulWidget {
  const FilesPage({super.key});

  @override
  State<FilesPage> createState() => _FilesPageState();
}

class _FilesPageState extends State<FilesPage> {
  static const Color primaryBlue = Color(0xFF1564A5);

  // Sample in-memory project data
  final List<Map<String, dynamic>> _projects = [
    {
      'id': 1,
      'name': 'Company Logo Tee',
      'type': 'Screen Printing',
      'filmCount': 4,
      'size': '2.4 MB',
      'date': '2025-02-18',
      'status': 'Complete',
    },
    {
      'id': 2,
      'name': 'Event Banner',
      'type': 'DTF',
      'filmCount': 1,
      'size': '1.1 MB',
      'date': '2025-02-17',
      'status': 'Complete',
    },
    {
      'id': 3,
      'name': 'Team Jerseys',
      'type': 'Sublimation',
      'filmCount': 6,
      'size': '3.8 MB',
      'date': '2025-02-16',
      'status': 'Processing',
    },
    {
      'id': 4,
      'name': 'Promo Stickers',
      'type': 'Flex/Vinyl',
      'filmCount': 2,
      'size': '890 KB',
      'date': '2025-02-15',
      'status': 'Complete',
    },
    {
      'id': 5,
      'name': 'Hoodie Design',
      'type': 'DTG',
      'filmCount': 5,
      'size': '4.2 MB',
      'date': '2025-02-14',
      'status': 'Error',
    },
    {
      'id': 6,
      'name': 'Trade Show Graphics',
      'type': 'Screen Printing',
      'filmCount': 3,
      'size': '2.1 MB',
      'date': '2025-02-13',
      'status': 'Complete',
    },
  ];

  String _searchQuery = '';
  String _statusFilter = 'All';

  List<Map<String, dynamic>> get _filteredProjects {
    return _projects.where((project) {
      final matchesSearch = project['name'].toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesStatus = _statusFilter == 'All' || project['status'] == _statusFilter;
      return matchesSearch && matchesStatus;
    }).toList();
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'Complete':
        return Colors.green;
      case 'Processing':
        return Colors.blue;
      case 'Error':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

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
                          'My Folders / Files',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.black,
                          ),
                        ),
                        const SizedBox(height: 30),

                        _buildStatsCards(),
                        const SizedBox(height: 30),

                        _buildFilterBar(),
                        const SizedBox(height: 20),

                        _buildProjectsGrid(),
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
          _sideButton(Icons.folder_open, 'My Folders', isActive: true),
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
        _sideButton(Icons.settings, 'Settings'),
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
                case 'Users':
                  Get.toNamed('/users');
                  break;
                case 'Settings':
                  Get.toNamed('/settings');
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
            'My Folders / Files',
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

  Widget _buildStatsCards() {
    final totalProjects = _projects.length;
    final completeProjects = _projects.where((p) => p['status'] == 'Complete').length;
    final processingProjects = _projects.where((p) => p['status'] == 'Processing').length;
    final totalFilms = _projects.fold<int>(0, (sum, p) => sum + (p['filmCount'] as int));

    return Row(
      children: [
        Expanded(
          child: _buildStatCard('Total Projects', totalProjects.toString(), Colors.blue),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: _buildStatCard('Complete', completeProjects.toString(), Colors.green),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: _buildStatCard('Processing', processingProjects.toString(), Colors.orange),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: _buildStatCard('Total Films', totalFilms.toString(), Colors.purple),
        ),
      ],
    );
  }

  Widget _buildStatCard(String title, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(20),
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
                  color: color.withAlpha((0.1 * 255).round()),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.folder_outlined,
                  size: 20,
                  color: color,
                ),
              ),
              const Spacer(),
            ],
          ),
          const SizedBox(height: 15),
          Text(
            value,
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: Colors.black,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            title,
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF6B7280),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Row(
      children: [
        Expanded(
          child: TextField(
            onChanged: (value) => setState(() => _searchQuery = value),
            decoration: InputDecoration(
              hintText: 'Search projects...',
              filled: true,
              fillColor: Colors.white,
              contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: Color(0xFFE5E7EB)),
              ),
              prefixIcon: const Icon(Icons.search, size: 20),
            ),
          ),
        ),
        const SizedBox(width: 15),
        Row(
          children: ['All', 'Complete', 'Processing', 'Error'].map((status) {
            final isSelected = _statusFilter == status;
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(status),
                selected: isSelected,
                onSelected: (selected) {
                  if (selected) setState(() => _statusFilter = status);
                },
                selectedColor: primaryBlue,
                labelStyle: TextStyle(
                  color: isSelected ? Colors.white : Colors.grey[700],
                  fontSize: 13,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                  side: const BorderSide(color: Color(0xFFE5E7EB)),
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(width: 15),
        ElevatedButton.icon(
          onPressed: () => Get.toNamed('/upload'),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('New Project'),
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryBlue,
            foregroundColor: Colors.white,
          ),
        ),
      ],
    );
  }

  Widget _buildProjectsGrid() {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 280,
        mainAxisSpacing: 20,
        crossAxisSpacing: 20,
        childAspectRatio: 0.85,
      ),
      itemCount: _filteredProjects.length,
      itemBuilder: (context, index) {
        final project = _filteredProjects[index];
        return _buildProjectCard(project);
      },
    );
  }

  Widget _buildProjectCard(Map<String, dynamic> project) {
    final statusColor = _getStatusColor(project['status']);
    final typeIcon = project['type'] == 'Screen Printing' ? Icons.print :
                     project['type'] == 'DTF' ? Icons.photo_size_select_large :
                     project['type'] == 'Sublimation' ? Icons.auto_awesome :
                     project['type'] == 'Flex/Vinyl' ? Icons.content_cut :
                     project['type'] == 'DTG' ? Icons.brush : Icons.folder;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Colored top bar
          Container(
            height: 6,
            decoration: BoxDecoration(
              color: statusColor,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: statusColor.withAlpha((0.1 * 255).round()),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(typeIcon, size: 24, color: statusColor),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: statusColor.withAlpha((0.1 * 255).round()),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        project['status'],
                        style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  project['name'],
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  project['type'],
                  style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Icon(Icons.movie, size: 14, color: Color(0xFF6B7280)),
                    const SizedBox(width: 4),
                    Text(
                      '${project['filmCount']} films',
                      style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
                    ),
                    const SizedBox(width: 16),
                    const Icon(Icons.insert_drive_file, size: 14, color: Color(0xFF6B7280)),
                    const SizedBox(width: 4),
                    Text(
                      project['size'],
                      style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.calendar_today, size: 14, color: Color(0xFF6B7280)),
                    const SizedBox(width: 4),
                    Text(
                      project['date'],
                      style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
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
}