// lib/presentation/upload/upload_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'upload_controller.dart';

class UploadPage extends StatefulWidget {
  const UploadPage({super.key});

  @override
  State<UploadPage> createState() => _UploadPageState();
}

class _UploadPageState extends State<UploadPage> {
  final TextEditingController _urlController = TextEditingController();

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GetBuilder<UploadController>(
      init: UploadController(),
      builder: (controller) {
        return Scaffold(
          appBar: AppBar(title: const Text('Upload Image'), elevation: 0),
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.image, size: 80, color: Get.theme.primaryColor),
                const SizedBox(height: 24),
                const Text(
                  'Select Image to Process',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
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
                SizedBox(
                  width: 420,
                  child: TextField(
                    controller: _urlController,
                    decoration: const InputDecoration(
                      labelText: 'Image URL (public)',
                      hintText: 'https://example.com/image.png',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.url,
                    onChanged: (v) => controller.urlInput.value = v,
                  ),
                ),
                const SizedBox(height: 12),
                ElevatedButton.icon(
                  onPressed: () =>
                      controller.importFromUrl(_urlController.text),
                  icon: const Icon(Icons.cloud_download),
                  label: const Text('Import from URL'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 32,
                      vertical: 16,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Obx(() {
                  if (!controller.isUrlDownloading.value) {
                    return const SizedBox(height: 0);
                  }
                  return SizedBox(
                    width: 420,
                    child: Column(
                      children: [
                        LinearProgressIndicator(
                          value: controller.urlDownloadProgress.value > 0
                              ? controller.urlDownloadProgress.value
                              : null,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          controller.urlDownloadStatus.value,
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.grey,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  );
                }),
                const SizedBox(height: 24),
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
