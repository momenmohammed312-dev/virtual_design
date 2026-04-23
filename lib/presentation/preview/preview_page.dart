// lib/presentation/preview/preview_page.dart

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'preview_controller.dart';

void _showAIFixDialog(PreviewController controller) {
  final textController = TextEditingController();
  Get.dialog(
    AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.auto_fix_high, color: Colors.deepPurple),
          SizedBox(width: 10),
          Text('AI Fix'),
        ],
      ),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Describe what you want to adjust in the film:',
              style: TextStyle(fontSize: 14, color: Color(0xFF6B7280)),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: textController,
              maxLines: 4,
              decoration: const InputDecoration(
                hintText:
                    'e.g. Make the lines thinner, increase contrast, remove noise from edges...',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.all(12),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Cancel'),
        ),
        ElevatedButton.icon(
          onPressed: () {
            final prompt = textController.text.trim();
            if (prompt.isNotEmpty) {
              Get.back();
              controller.applyAIFix(prompt);
            }
          },
          icon: const Icon(Icons.auto_fix_high, size: 16),
          label: const Text('Apply AI Fix'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.deepPurple,
            foregroundColor: Colors.white,
          ),
        ),
      ],
    ),
  );
}

class PreviewPage extends StatelessWidget {
  const PreviewPage({super.key});

  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color sidebarBlue = Color(0xFF0E3182);

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
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final isNarrow = constraints.maxWidth < 1200;
                      return SingleChildScrollView(
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
                              style: TextStyle(
                                fontSize: 16,
                                color: Color(0xFF6B7280),
                              ),
                            ),
                            const SizedBox(height: 30),
                            SizedBox(
                              height: 500,
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Main Preview Area
                                  Expanded(
                                    flex: 7,
                                    child: _buildPreviewArea(controller),
                                  ),
                                  const SizedBox(width: 20),

                                  // Sidebar with Layers Panel only (Bug 1: Removed Fine-Tune tab)
                                  SizedBox(
                                    width: 260,
                                    child: _buildRightPanel(controller),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 20),
                            _buildBottomActions(controller, isNarrow),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPreviewArea(PreviewController controller) {
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
                  onPressed: controller.zoomIn,
                  icon: const Icon(Icons.zoom_in),
                  tooltip: 'Zoom In',
                ),
                IconButton(
                  onPressed: controller.zoomOut,
                  icon: const Icon(Icons.zoom_out),
                  tooltip: 'Zoom Out',
                ),
                IconButton(
                  onPressed: controller.fitToScreen,
                  icon: const Icon(Icons.fit_screen),
                  tooltip: 'Fit to Screen',
                ),
              ],
            ),
          ),

          // Preview Canvas
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }

              if (controller.previewPaths.isEmpty) {
                return Container(
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
                        const Icon(
                          Icons.image_outlined,
                          size: 64,
                          color: Color(0xFF9CA3AF),
                        ),
                        const SizedBox(height: 20),
                        const Text(
                          'No films generated yet',
                          style: TextStyle(
                            fontSize: 16,
                            color: Color(0xFF6B7280),
                          ),
                        ),
                        const SizedBox(height: 10),
                        ElevatedButton.icon(
                          onPressed: () => Get.offAllNamed('/upload'),
                          icon: const Icon(Icons.upload),
                          label: const Text('Upload Image'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: primaryBlue,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }

              return Container(
                margin: const EdgeInsets.all(20),
                constraints: const BoxConstraints(minHeight: 200),
                decoration: BoxDecoration(
                  color: const Color(0xFFF9FAFB),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFE5E7EB)),
                ),
                child: SingleChildScrollView(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Film display with progress overlay (BUG 2 FIX)
                        Stack(
                          alignment: Alignment.center,
                          children: [
                            Container(
                              constraints: const BoxConstraints(
                                maxWidth: 600,
                                maxHeight: 450,
                              ),
                              decoration: BoxDecoration(
                                color: Colors
                                    .white, // White background for film preview
                                borderRadius: BorderRadius.circular(8),
                                border:
                                    Border.all(color: const Color(0xFFE5E7EB)),
                              ),
                              child: Obx(() {
                                final idx = controller.selectedFilmIndex.value;
                                if (controller.previewPaths.isEmpty) {
                                  return const Icon(
                                    Icons.broken_image,
                                    size: 64,
                                    color: Colors.grey,
                                  );
                                }
                                final path = controller.previewPaths[idx];
                                return _buildFilmPreview(controller, path, idx);
                              }),
                            ),
                            // BUG 2 FIX: Progress overlay during regeneration
                            Obx(() {
                              if (!controller.isRegenerating.value) {
                                return const SizedBox.shrink();
                              }
                              return Container(
                                constraints: const BoxConstraints(
                                  maxWidth: 500,
                                  maxHeight: 500,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.white
                                      .withAlpha((0.9 * 255).round()),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Center(
                                  child: Container(
                                    width: 300,
                                    padding: const EdgeInsets.all(20),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(12),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black
                                              .withAlpha((0.1 * 255).round()),
                                          blurRadius: 10,
                                          offset: const Offset(0, 4),
                                        ),
                                      ],
                                    ),
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Obx(() => LinearProgressIndicator(
                                              value: controller.progress.value >
                                                      0
                                                  ? controller.progress.value
                                                  : null,
                                              backgroundColor:
                                                  const Color(0xFFE5E7EB),
                                              valueColor:
                                                  const AlwaysStoppedAnimation<
                                                      Color>(primaryBlue),
                                            )),
                                        const SizedBox(height: 12),
                                        Obx(() => Text(
                                              controller.progressMessage.value
                                                      .isNotEmpty
                                                  ? controller
                                                      .progressMessage.value
                                                  : 'Processing...',
                                              style: const TextStyle(
                                                fontSize: 14,
                                                color: Color(0xFF6B7280),
                                              ),
                                              textAlign: TextAlign.center,
                                            )),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            }),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Obx(
                          () => Text(
                            'Film ${controller.selectedFilmIndex.value + 1} of ${controller.previewPaths.length}',
                            style: const TextStyle(
                              fontSize: 14,
                              color: Color(0xFF6B7280),
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          height: 12,
                          child: SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: List.generate(
                                controller.previewPaths.length,
                                (index) {
                                  return Obx(() {
                                    final isSelected =
                                        controller.selectedFilmIndex.value ==
                                            index;
                                    return AnimatedContainer(
                                      duration:
                                          const Duration(milliseconds: 200),
                                      margin: const EdgeInsets.symmetric(
                                          horizontal: 4),
                                      width: isSelected ? 24 : 12,
                                      height: 12,
                                      decoration: BoxDecoration(
                                        color: isSelected
                                            ? primaryBlue
                                            : Colors.grey.shade300,
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                    );
                                  });
                                },
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildFilmPreview(
      PreviewController controller, String path, int index) {
    if (!File(path).existsSync()) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.broken_image, size: 64, color: Colors.grey),
          const SizedBox(height: 10),
          const Text('File not found', style: TextStyle(color: Colors.grey)),
        ],
      );
    }

    return Obx(() {
      final isInverted = controller.isLayerInverted.length > index
          ? controller.isLayerInverted[index]
          : false;
      final tShirtCol = controller.tshirtColor.value;
      final showSim = controller.showTshirtSimulation.value;

      // matrix to invert colors: output = 255 - input
      const invertMatrix = <double>[
        -1,
        0,
        0,
        0,
        255,
        0,
        -1,
        0,
        0,
        255,
        0,
        0,
        -1,
        0,
        255,
        0,
        0,
        0,
        1,
        0,
      ];

      Widget image = Image.file(
        File(path),
        key: ValueKey(
            '${path}_${controller.lastUpdateTimestamp.value}'), // Cache Busting (Phase 10)
        fit: BoxFit.contain,
        gaplessPlayback: true, // Smoother transitions (Phase 11)
        errorBuilder: (context, error, stackTrace) => const Icon(Icons.error),
      );

      // 1. Apply Fast Inversion Simulation
      if (isInverted) {
        image = ColorFiltered(
          colorFilter: const ColorFilter.matrix(invertMatrix),
          child: image,
        );
      }

      // 2. Apply T-Shirt Simulation (Multiply design on top of color)
      if (showSim) {
        image = Container(
          color: tShirtCol,
          child: ColorFiltered(
            colorFilter: ColorFilter.mode(tShirtCol, BlendMode.multiply),
            child: image,
          ),
        );
      }

      return ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: InteractiveViewer(
          transformationController: controller.transformationController,
          minScale: 0.5,
          maxScale: 5.0,
          boundaryMargin: const EdgeInsets.all(100),
          child: image,
        ),
      );
    });
  }

  Widget _buildLayersPanel(PreviewController controller) {
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
              children: [
                const Icon(Icons.layers, size: 20, color: Color(0xFF6B7280)),
                const SizedBox(width: 10),
                const Text(
                  'Color Layers',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                Obx(
                  () => Text(
                    '${controller.previewPaths.length} films',
                    style: const TextStyle(
                      fontSize: 13,
                      color: Color(0xFF6B7280),
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Obx(() {
              if (controller.previewPaths.isEmpty) {
                return const Center(
                  child: Text(
                    'No films available',
                    style: TextStyle(color: Color(0xFF6B7280)),
                  ),
                );
              }

              return ListView.builder(
                padding: const EdgeInsets.all(15),
                itemCount: controller.previewPaths.length,
                itemBuilder: (context, index) {
                  final isSelected =
                      controller.selectedFilmIndex.value == index;
                  final path = controller.previewPaths[index];
                  final isPdf = path.toLowerCase().endsWith('.pdf');
                  return GestureDetector(
                    onTap: () => controller.selectFilm(index),
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? primaryBlue.withAlpha((0.05 * 255).round())
                            : const Color(0xFFF9FAFB),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isSelected
                              ? primaryBlue
                              : const Color(0xFFE5E7EB),
                          width: isSelected ? 2 : 1,
                        ),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: Colors.grey.shade300),
                            ),
                            child: _buildColorSwatchOrThumb(
                                controller, index, path),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _buildFilmColorName(
                                    controller, index, isSelected),
                                _buildFilmDetails(controller, index),
                              ],
                            ),
                          ),
                          // Per-layer Halftone Toggle (NEW Fix 5)
                          Obx(() => IconButton(
                                icon: Icon(
                                  controller.layerIsHalftone.length > index &&
                                          controller.layerIsHalftone[index]
                                      ? Icons.grain
                                      : Icons.square,
                                  color: controller.layerIsHalftone.length >
                                              index &&
                                          controller.layerIsHalftone[index]
                                      ? primaryBlue
                                      : Colors.grey.shade400,
                                  size: 20,
                                ),
                                onPressed: () =>
                                    controller.toggleLayerHalftone(index),
                                tooltip: 'Per-layer Halftone',
                              )),
                          const SizedBox(width: 4),
                          isPdf
                              ? IconButton(
                                  icon: const Icon(Icons.open_in_new, size: 18),
                                  onPressed: () => controller.openFile(path),
                                  tooltip: 'Open PDF',
                                )
                              : Icon(
                                  isSelected
                                      ? Icons.radio_button_checked
                                      : Icons.radio_button_unchecked,
                                  color: isSelected ? primaryBlue : Colors.grey,
                                ),
                        ],
                      ),
                    ),
                  );
                },
              );
            }),
          ),
          Container(
            padding: const EdgeInsets.all(15),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: Color(0xFFE5E7EB))),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.info_outline,
                      size: 18,
                      color: Color(0xFF6B7280),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Obx(
                        () => Text(
                          '${controller.previewPaths.length} film${controller.previewPaths.length == 1 ? '' : 's'} detected',
                          style: const TextStyle(
                            fontSize: 13,
                            color: Color(0xFF6B7280),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: controller.exportAll,
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

  Widget _buildBottomActions(PreviewController controller, bool isNarrow) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: isNarrow
          ? Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                OutlinedButton.icon(
                  onPressed: controller.goBackToSetup,
                  icon: const Icon(Icons.arrow_back, size: 18),
                  label: const Text('Back'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.grey,
                    side: const BorderSide(color: Color(0xFFE5E7EB)),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 15, vertical: 12),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () => _showAIFixDialog(controller),
                  icon: const Icon(Icons.auto_fix_high, size: 18),
                  label: const Text('AI Fix'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.deepPurple,
                    side: const BorderSide(color: Colors.deepPurple),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 15, vertical: 12),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: controller.exportAll,
                  icon: const Icon(Icons.download, size: 18),
                  label: const Text('Save PDF'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: primaryBlue,
                    side: const BorderSide(color: primaryBlue),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 15, vertical: 12),
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: controller.sendToPrint,
                  icon: const Icon(Icons.print, size: 18),
                  label: const Text('Print'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: primaryBlue,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 15, vertical: 12),
                  ),
                ),
              ],
            )
          : Row(
              children: [
                OutlinedButton.icon(
                  onPressed: controller.goBackToSetup,
                  icon: const Icon(Icons.arrow_back, size: 18),
                  label: const Text('Back to Setup'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.grey,
                    side: const BorderSide(color: Color(0xFFE5E7EB)),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 20, vertical: 15),
                  ),
                ),
                const Spacer(),
                OutlinedButton.icon(
                  onPressed: () => _showAIFixDialog(controller),
                  icon: const Icon(Icons.auto_fix_high, size: 18),
                  label: const Text('AI Fix'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.deepPurple,
                    side: const BorderSide(color: Colors.deepPurple),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 20, vertical: 15),
                  ),
                ),
                const SizedBox(width: 15),
                OutlinedButton.icon(
                  onPressed: controller.exportAll,
                  icon: const Icon(Icons.download, size: 18),
                  label: const Text('Save Combined PDF'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: primaryBlue,
                    side: const BorderSide(color: primaryBlue),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 20, vertical: 15),
                  ),
                ),
                const SizedBox(width: 15),
                ElevatedButton.icon(
                  onPressed: controller.sendToPrint,
                  icon: const Icon(Icons.print, size: 18),
                  label: const Text('Send to Print'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: primaryBlue,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 30, vertical: 15),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildProgressSteps() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _buildStep(1, 'Upload File', true, false),
          _buildProgressLine(true),
          _buildStep(2, 'System Setup', true, false),
          _buildProgressLine(true),
          _buildStep(3, 'Print Preview', false, true),
        ],
      ),
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
            color: isComplete
                ? Colors.green
                : isActive
                    ? primaryBlue
                    : const Color(0xFFE5E7EB),
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
    return Container(
      width: 100,
      height: 2,
      margin: const EdgeInsets.only(bottom: 30),
      color: isComplete ? Colors.green : const Color(0xFFE5E7EB),
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
              child: Icon(Icons.print_rounded, color: Colors.white, size: 20),
            ),
          ),
          SizedBox(width: 10),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Virtual Designer',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProfile() {
    return Padding(
      padding: const EdgeInsets.all(15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Text('M02',
                style: TextStyle(
                    color: Colors.grey.shade400,
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 1.5)),
          ),
          Row(
            children: [
              CircleAvatar(
                radius: 20,
                backgroundColor: const Color(0xFFE3F2FD),
                child: const Icon(Icons.admin_panel_settings,
                    color: Color(0xFF1564A5), size: 22),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Admin',
                        style: TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 14)),
                    Text('admin@virtualdesigner.app',
                        style: TextStyle(fontSize: 11, color: Colors.grey)),
                  ],
                ),
              ),
            ],
          ),
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
          leading: Icon(
            icon,
            color: isActive ? primaryBlue : Colors.grey,
            size: 20,
          ),
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
            color: Colors.black.withAlpha((0.05 * 255).round()),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          const Expanded(
            child: Text(
              'Print Preview',
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
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

  // ─── Helpers for Color Layers ──────────────────────────────────────────────

  Widget _buildColorSwatchOrThumb(
      PreviewController controller, int index, String path) {
    // If we have color info, show a clean swatch
    if (controller.colorInfo.length > index) {
      final colorData = controller.colorInfo[index];
      final hex = colorData['hex'] as String;
      final color = _hexToColor(hex);

      return Container(
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(5),
        ),
      );
    }

    // Fallback: show thumbnail
    return Container(
      key: ValueKey(
          '${path}_${controller.lastUpdateTimestamp.value}'), // Cache Busting (Phase 10)
      decoration: BoxDecoration(
        color: Colors.grey.shade300,
        borderRadius: BorderRadius.circular(5),
        image: DecorationImage(
          image: FileImage(File(path)),
          fit: BoxFit.cover,
        ),
      ),
    );
  }

  Widget _buildFilmColorName(
      PreviewController controller, int index, bool isSelected) {
    String name = 'Film ${index + 1}';

    if (controller.colorInfo.length > index) {
      name = controller.colorInfo[index]['name'] ?? name;
    }

    return Text(
      name,
      style: TextStyle(
        fontSize: 14,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        color: isSelected ? primaryBlue : Colors.black87,
      ),
    );
  }

  Widget _buildFilmDetails(PreviewController controller, int index) {
    String detailText = '';
    if (controller.colorInfo.length > index) {
      final colorData = controller.colorInfo[index];
      final coverage = colorData['percentage'] ?? 0.0;
      final hex = colorData['hex'] ?? '';
      detailText = '$hex • $coverage% coverage';
    } else {
      detailText = 'Generic Film Layer';
    }

    // Add dot size info if available
    if (controller.dotSizeMultipliers.length > index) {
      final mult = controller.dotSizeMultipliers[index];
      String label = 'Normal';
      if (mult <= 0.6) label = 'Very Fine';
      else if (mult <= 0.8) label = 'Fine';
      else if (mult >= 1.4) label = 'Very Bold';
      else if (mult >= 1.2) label = 'Bold';
      
      detailText += ' • $label (${mult.toStringAsFixed(1)}x)';
    }

    return Text(
      detailText,
      style: const TextStyle(
        fontSize: 12,
        color: Color(0xFF6B7280),
      ),
    );
  }

  Color _hexToColor(String hexString) {
    final buffer = StringBuffer();
    if (hexString.length == 6 || hexString.length == 7) buffer.write('ff');
    buffer.write(hexString.replaceFirst('#', ''));
    return Color(int.parse(buffer.toString(), radix: 16));
  }

  Widget _buildRightPanel(PreviewController controller) {
    return DefaultTabController(
      length: 1,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Column(
          children: [
            const TabBar(
              labelColor: primaryBlue,
              unselectedLabelColor: Colors.grey,
              indicatorColor: primaryBlue,
              tabs: [
                Tab(text: 'Layers', icon: Icon(Icons.layers, size: 18)),
                // BUG 1 FIX: Removed Fine-Tune tab to prevent unwanted re-processing
              ],
            ),
            Expanded(
              child: TabBarView(
                children: [
                  _buildLayersPanel(controller),
                  // BUG 1 FIX: Removed _buildFineTunePanel to prevent slider debounce triggers
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
