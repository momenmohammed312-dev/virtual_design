// lib/presentation/users/users_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';

class UsersPage extends StatefulWidget {
  const UsersPage({super.key});

  @override
  State<UsersPage> createState() => _UsersPageState();
}

class _UsersPageState extends State<UsersPage> {
  static const Color primaryBlue = Color(0xFF1564A5);

  // Sample in-memory data
  final List<Map<String, dynamic>> _users = [
    {'id': 1, 'name': 'John Smith', 'email': 'john@example.com', 'role': 'Admin', 'lastLogin': '2025-02-18 14:30', 'status': 'Active'},
    {'id': 2, 'name': 'Sarah Johnson', 'email': 'sarah@example.com', 'role': 'Designer', 'lastLogin': '2025-02-17 09:15', 'status': 'Active'},
    {'id': 3, 'name': 'Mike Wilson', 'email': 'mike@example.com', 'role': 'Designer', 'lastLogin': '2025-02-16 16:45', 'status': 'Inactive'},
    {'id': 4, 'name': 'Emily Davis', 'email': 'emily@example.com', 'role': 'Admin', 'lastLogin': '2025-02-18 11:20', 'status': 'Active'},
    {'id': 5, 'name': 'Robert Brown', 'email': 'robert@example.com', 'role': 'Designer', 'lastLogin': '2025-02-15 13:10', 'status': 'Active'},
  ];

  String _searchQuery = '';
  String _roleFilter = 'All';

  List<Map<String, dynamic>> get _filteredUsers {
    return _users.where((user) {
      final matchesSearch = user['name'].toLowerCase().contains(_searchQuery.toLowerCase()) ||
                            user['email'].toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesRole = _roleFilter == 'All' || user['role'] == _roleFilter;
      return matchesSearch && matchesRole;
    }).toList();
  }

  int get totalUsers => _users.length;
  int get activeUsers => _users.where((u) => u['status'] == 'Active').length;
  int get inactiveUsers => _users.where((u) => u['status'] == 'Inactive').length;

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
                          'User Management',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.black,
                          ),
                        ),
                        const SizedBox(height: 30),

                        _buildStatsCards(),
                        const SizedBox(height: 30),

                        _buildTableHeader(),
                        const SizedBox(height: 15),

                        _buildUsersTable(),
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
        _sideButton(Icons.person_2_rounded, 'Users', isActive: true),
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
                case 'My Folders':
                  Get.toNamed('/files');
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
            'User Management',
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
    return Row(
      children: [
        Expanded(
          child: _buildStatCard('Total Users', totalUsers.toString(), Colors.blue),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: _buildStatCard('Active', activeUsers.toString(), Colors.green),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: _buildStatCard('Inactive', inactiveUsers.toString(), Colors.orange),
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
                  title == 'Total Users' ? Icons.people : title == 'Active' ? Icons.check_circle : Icons.pending,
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

  Widget _buildTableHeader() {
    return Row(
      children: [
        Expanded(
          flex: 3,
          child: TextField(
            onChanged: (value) => setState(() => _searchQuery = value),
            decoration: InputDecoration(
              hintText: 'Search users...',
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
        Container(
          width: 150,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFFE5E7EB)),
          ),
          child: DropdownButton<String>(
            value: _roleFilter,
            isExpanded: true,
            underline: const SizedBox(),
            items: ['All', 'Admin', 'Designer'].map((String role) {
              return DropdownMenuItem<String>(
                value: role,
                child: Text(role, style: const TextStyle(fontSize: 14)),
              );
            }).toList(),
            onChanged: (String? newValue) {
              if (newValue != null) setState(() => _roleFilter = newValue);
            },
          ),
        ),
        const SizedBox(width: 15),
        ElevatedButton.icon(
          onPressed: () => _showAddUserDialog(),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Add User'),
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryBlue,
            foregroundColor: Colors.white,
          ),
        ),
      ],
    );
  }

  Widget _buildUsersTable() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: _filteredUsers.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final user = _filteredUsers[index];
          return _buildUserRow(user);
        },
      ),
    );
  }

  Widget _buildUserRow(Map<String, dynamic> user) {
    final initials = user['name'].split(' ').map((n) => n[0]).take(2).join();
    final roleColor = user['role'] == 'Admin' ? Colors.blue : Colors.green;
    final statusColor = user['status'] == 'Active' ? Colors.green : Colors.orange;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          CircleAvatar(
            radius: 20,
            backgroundColor: const Color(0xFFE3F2FD),
            child: Text(initials, style: const TextStyle(fontWeight: FontWeight.bold, color: primaryBlue)),
          ),
          const SizedBox(width: 16),
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(user['name'], style: const TextStyle(fontWeight: FontWeight.w600)),
                Text(user['email'], style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280))),
              ],
            ),
          ),
          Expanded(
            flex: 1,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: roleColor.withAlpha((0.1 * 255).round()),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                user['role'],
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: roleColor, fontWeight: FontWeight.w600),
              ),
            ),
          ),
          Expanded(
            flex: 2,
            child: Text(
              user['lastLogin'],
              style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
            ),
          ),
          Expanded(
            flex: 1,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: statusColor.withAlpha((0.1 * 255).round()),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                user['status'],
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: statusColor, fontWeight: FontWeight.w600),
              ),
            ),
          ),
          Expanded(
            flex: 1,
            child: PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert, color: Colors.grey),
              onSelected: (value) {
                if (value == 'edit') {
                  _showEditUserDialog(user);
                } else if (value == 'delete') {
                  _showDeleteUserDialog(user['id']);
                }
              },
              itemBuilder: (context) => [
                const PopupMenuItem(value: 'edit', child: Text('Edit')),
                const PopupMenuItem(value: 'delete', child: Text('Delete', style: TextStyle(color: Colors.red))),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showAddUserDialog() {
    final nameController = TextEditingController();
    final emailController = TextEditingController();
    final passwordController = TextEditingController();

    Get.dialog(
      AlertDialog(
        title: const Text('Add User'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: 'Full Name'),
            ),
            TextField(
              controller: emailController,
              decoration: const InputDecoration(labelText: 'Email'),
            ),
            TextField(
              controller: passwordController,
              decoration: const InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              if (nameController.text.isNotEmpty && emailController.text.isNotEmpty) {
                setState(() {
                  _users.add({
                    'id': _users.length + 1,
                    'name': nameController.text,
                    'email': emailController.text,
                    'role': 'Designer',
                    'lastLogin': 'Never',
                    'status': 'Active',
                  });
                });
                Get.back();
                Get.snackbar('Success', 'User added successfully', snackPosition: SnackPosition.BOTTOM);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  void _showEditUserDialog(Map<String, dynamic> user) {
    final nameController = TextEditingController(text: user['name']);
    final emailController = TextEditingController(text: user['email']);

    Get.dialog(
      AlertDialog(
        title: const Text('Edit User'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: 'Full Name'),
            ),
            TextField(
              controller: emailController,
              decoration: const InputDecoration(labelText: 'Email'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              if (nameController.text.isNotEmpty && emailController.text.isNotEmpty) {
                setState(() {
                  user['name'] = nameController.text;
                  user['email'] = emailController.text;
                });
                Get.back();
                Get.snackbar('Success', 'User updated successfully', snackPosition: SnackPosition.BOTTOM);
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _showDeleteUserDialog(int userId) {
    Get.dialog(
      AlertDialog(
        title: const Text('Delete User'),
        content: const Text('Are you sure you want to delete this user? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              setState(() {
                _users.removeWhere((u) => u['id'] == userId);
              });
              Get.back();
              Get.snackbar('Deleted', 'User has been removed', snackPosition: SnackPosition.BOTTOM);
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}