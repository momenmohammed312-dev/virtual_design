import 'package:shared_preferences/shared_preferences.dart';
// Note: flutter_secure_storage is optional - using SharedPreferences for simplicity

/// Repository for managing user-specific folders and settings.
/// Handles user identification and folder access control.
class FolderRepository {
  static const String _currentUserIdKey = 'current_user_id';
  static const String _usersKey = 'registered_users';
  
  /// Get the current logged-in user ID
  Future<String> getCurrentUserId() async {
    final prefs = await SharedPreferences.getInstance();
    String? userId = prefs.getString(_currentUserIdKey);
    
    // If no user is logged in, return default user
    if (userId == null) {
      userId = 'default_user';
      await setCurrentUserId(userId);
    }
    
    return userId;
  }
  
  /// Set the current logged-in user
  Future<void> setCurrentUserId(String userId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_currentUserIdKey, userId);
  }
  
  /// Get folders for a specific user
  Future<List<Map<String, dynamic>>> getFoldersByUser(String userId) async {
    // In a real app, this would query a database or API
    // For now, return user-specific sample data
    return [
      {
        'id': '${userId}_projects',
        'name': 'Projects',
        'path': '/storage/emulated/0/VirtualDesign/Projects',
        'itemCount': 12,
        'userId': userId,
      },
      {
        'id': '${userId}_exports',
        'name': 'Exports',
        'path': '/storage/emulated/0/VirtualDesign/Exports',
        'itemCount': 5,
        'userId': userId,
      },
      {
        'id': '${userId}_templates',
        'name': 'Templates',
        'path': '/storage/emulated/0/VirtualDesign/Templates',
        'itemCount': 3,
        'userId': userId,
      },
    ];
  }
  
  /// Get all folders (admin only - for user management)
  Future<List<Map<String, dynamic>>> getAllFolders() async {
    final prefs = await SharedPreferences.getInstance();
    final users = prefs.getStringList(_usersKey) ?? ['default_user'];
    
    List<Map<String, dynamic>> allFolders = [];
    for (final userId in users) {
      final folders = await getFoldersByUser(userId);
      allFolders.addAll(folders);
    }
    
    return allFolders;
  }
  
  /// Check if current user has access to a specific folder
  Future<bool> hasAccessToFolder(String folderId) async {
    final currentUserId = await getCurrentUserId();
    return folderId.startsWith(currentUserId);
  }
  
  /// Create a new folder for current user
  Future<void> createFolder(String name, String path) async {
    final userId = await getCurrentUserId();
    // In a real app, this would create the directory and update database
    print('Creating folder $name at $path for user $userId');
  }
  
  /// Delete a folder (only if user owns it)
  Future<void> deleteFolder(String folderId) async {
    if (!await hasAccessToFolder(folderId)) {
      throw Exception('Access denied: You do not own this folder');
    }
    // In a real app, delete from database and optionally filesystem
    print('Deleting folder $folderId');
  }
}
