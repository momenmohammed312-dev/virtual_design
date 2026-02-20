// lib/presentation/upload/upload_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'upload_controller.dart';

class UploadPage extends StatelessWidget {
  const UploadPage({super.key});

  @override
  Widget build(BuildContext context) {
    return GetBuilder<UploadController>(
      init: UploadController(),
      builder: (controller) {
        return Scaffold(
          appBar: AppBar(
            title: const Text('Upload Image'),
            elevation: 0,
          ),
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.image,
                  size: 80,
                  color: Get.theme.primaryColor,
                ),
                const SizedBox(height: 24),
                const Text(
                  'Select Image to Process',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 32),
                  child: Text(
                    'Choose an image from your gallery or device',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 16, color: Colors.grey),
                  ),
                ),
                const SizedBox(height: 48),
                ElevatedButton.icon(
                  onPressed: controller.pickImage,
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Pick from Gallery'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 32,
                      vertical: 16,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: controller.pickFile,
                  icon: const Icon(Icons.folder_open),
                  label: const Text('Pick from Files'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 32,
                      vertical: 16,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
