// lib/presentation/setup/setup_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:virtual_design/core/enums/app_enums.dart';
import '../../domain/entities/processing_settings.dart' as ps;
import 'setup_controller.dart';

class SetupPage extends StatefulWidget {
  const SetupPage({super.key});

  @override
  State<SetupPage> createState() => _SetupPageState();
}

class _SetupPageState extends State<SetupPage> {
  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color sidebarBlue = Color(0xFF0E3182);

  // State variables - Now synced with controller viainitState
  PrintType selectedPrintType = PrintType.screenPrinting;
  int selectedColorCount = 0;
  DetailLevel selectedDetailLevel = DetailLevel.medium;

  // Halftone settings
  bool showHalftoneSettings = false;
  int lpi = 55;
  DotShape selectedDotShape = DotShape.round;
  // Custom paper size (cm) support in the UI
  bool isCustomPaper = false;
  double customPaperWidthCm = 21.0;
  double customPaperHeightCm = 29.7;

  // Specifications
  double strokeWidth = 0.5;
  String selectedPaperSize = 'A4 (21 × 29.7 cm)';
  int copies = 1;
  double printQuality = 300;

  // Fabric type
  FabricType? selectedFabricType;

  // Advanced settings
  bool showAdvancedSettings = false;
  bool autoUpscale = true;
  bool removeBackground = true;
  bool edgeEnhancement = false;
  bool colorCorrection = false;
  bool adaptiveThreshold = false;

  int get meshCount {
    // Calculate mesh count based on LPI and detail level
    // Standard mesh counts: 110, 160, 200, 230, 280, 355
    if (lpi < 30) return 110;
    if (lpi < 50) return 160;
    if (lpi < 65) return 200;
    if (lpi < 80) return 230;
    if (lpi < 90) return 280;
    return 355;
  }

  int get strokeWidthInPixels {
    final strokeWidthCm = strokeWidth / 10;
    final strokeWidthInches = strokeWidthCm / 2.54;
    return (strokeWidthInches * printQuality).round();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      body: GetBuilder<SetupController>(
        builder: (controller) => Stack(
          children: [
            Row(
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
                              _buildProgressSteps(),
                              const SizedBox(height: 30),
                              const Text(
                                'Print & System Setup',
                                style: TextStyle(
                                  fontSize: 32,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.black,
                                ),
                              ),
                              const SizedBox(height: 10),
                              const Text(
                                'Configure your print job parameters, finish type, and quality settings below.',
                                style: TextStyle(
                                  fontSize: 16,
                                  color: Color(0xFF6B7280),
                                ),
                              ),
                              const SizedBox(height: 30),
                              _buildColorComplexitySection(),
                              const SizedBox(height: 30),
                              _buildImageTypeSection(controller),
                              const SizedBox(height: 30),
                              _buildPrintTypeSection(),
                              const SizedBox(height: 30),
                              if (true) ...[
                                _buildFabricTypeSection(),
                                const SizedBox(height: 30),
                              ],
                              _buildDetailLevelSection(),
                              const SizedBox(height: 30),
                              _buildPrintFinishSection(controller),
                              const SizedBox(height: 30),
                              _buildStrokeWidthSection(),
                              const SizedBox(height: 30),
                              _buildSpecificationsSection(),
                              const SizedBox(height: 30),
                              _buildAdvancedSettingsSection(),
                              const SizedBox(height: 30),
                              _buildOutputDirectorySection(controller),
                              const SizedBox(height: 30),
                              _buildBottomActions(controller),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            // Progress Overlay
            Obx(() {
              if (!controller.isProcessing.value) {
                return const SizedBox.shrink();
              }
              return Positioned.fill(
                child: Container(
                  color: Colors.black.withAlpha((0.5 * 255).round()),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 400),
                      child: Card(
                        color: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.hourglass_bottom,
                                size: 48,
                                color: primaryBlue,
                              ),
                              const SizedBox(height: 16),
                              const Text(
                                'Processing Image',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 24),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(8),
                                child: LinearProgressIndicator(
                                  minHeight: 6,
                                  value: controller.progress.value,
                                  backgroundColor: const Color(0xFFE5E7EB),
                                  valueColor:
                                      const AlwaysStoppedAnimation<Color>(
                                    primaryBlue,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                '${(controller.progress.value * 100).toStringAsFixed(0)}%',
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: primaryBlue,
                                ),
                              ),
                              const SizedBox(height: 16),
                              Obx(
                                () => Text(
                                  controller.progressMessage.value,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(
                                    fontSize: 13,
                                    color: Color(0xFF6B7280),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  // ============= Color Complexity Section =============
  Widget _buildColorComplexitySection() {
    return Container(
      padding: const EdgeInsets.all(25),
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
                  color: const Color(0xFFEDE7F6),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.palette_outlined,
                  color: Color(0xFF7E57C2),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '1. Color Complexity',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 15,
            runSpacing: 15,
            children: [
              _buildAutoColorOption(),
              ...[1, 2, 3, 4].map((count) {
                return _buildColorOption(count);
              }),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAutoColorOption() {
    bool isSelected = selectedColorCount == 0;

    return InkWell(
      onTap: () {
        setState(() => selectedColorCount = 0);
        Get.find<SetupController>().selectedColors.value = 0;
      },
      child: Container(
        width: 130,
        height: 100,
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 35,
              height: 35,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF9C27B0),
              ),
              child: const Icon(
                Icons.auto_awesome,
                size: 20,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'Auto',
              style: TextStyle(
                fontSize: 14,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? primaryBlue : Colors.black87,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildColorOption(int count) {
    bool isSelected = selectedColorCount == count;
    final colors = [
      Colors.black,
      const Color(0xFFEF4444),
      const Color(0xFF4CAF50),
      const Color(0xFF9C27B0),
      const Color(0xFF00BCD4),
    ];
    final colorIndex = count - 1;

    return InkWell(
      onTap: () {
        setState(() => selectedColorCount = count);
        // Propagate to SetupController for processing
        Get.find<SetupController>().selectedColors.value = count;
      },
      child: Container(
        width: 130,
        height: 100,
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 35,
              height: 35,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: colors[colorIndex],
              ),
            ),
            const SizedBox(height: 10),
            Text(
              '$count Color${count > 1 ? 's' : ''}',
              style: TextStyle(
                fontSize: 14,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? primaryBlue : Colors.black87,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============= Image Type Section =============
  Widget _buildImageTypeSection(SetupController controller) {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFE0F2F1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.image_search_outlined,
                  color: Color(0xFF00897B),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '2. Image Type',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              const Tooltip(
                message: 'CHOOSE BASED ON YOUR ARTWORK DETAILS',
                child: Icon(Icons.info_outline, size: 18, color: Colors.grey),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'The engine will auto-tune thresholding and cleanup based on your choice.',
            style: TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
          ),
          const SizedBox(height: 25),
          Obx(() => SegmentedButton<ps.ImageType>(
                segments: const [
                  ButtonSegment(
                    value: ps.ImageType.simple,
                    label: Text('Simple'),
                    icon: Icon(Icons.text_fields),
                    tooltip: 'Logos, Text, High Contrast',
                  ),
                  ButtonSegment(
                    value: ps.ImageType.mixed,
                    label: Text('Mixed'),
                    icon: Icon(Icons.collections),
                    tooltip: 'Normal Photos or Illustrations',
                  ),
                  ButtonSegment(
                    value: ps.ImageType.complex,
                    label: Text('Complex'),
                    icon: Icon(Icons.auto_fix_high),
                    tooltip: 'High Detail, Shadows, Gradients',
                  ),
                  ButtonSegment(
                    value: ps.ImageType.auto,
                    label: Text('Auto'),
                    icon: Icon(Icons.auto_awesome),
                    tooltip: 'Recommended — System Decides',
                  ),
                ],
                selected: {controller.selectedImageType.value},
                onSelectionChanged: (Set<ps.ImageType> newSelection) {
                  controller.selectedImageType.value = newSelection.first;
                },
                style: ButtonStyle(
                  side: WidgetStateProperty.all(
                    const BorderSide(color: Color(0xFFE5E7EB)),
                  ),
                  backgroundColor: WidgetStateProperty.resolveWith<Color?>(
                    (Set<WidgetState> states) {
                      if (states.contains(WidgetState.selected)) {
                        return primaryBlue;
                      }
                      return Colors.white;
                    },
                  ),
                  foregroundColor: WidgetStateProperty.resolveWith<Color?>(
                    (Set<WidgetState> states) {
                      if (states.contains(WidgetState.selected)) {
                        return Colors.white;
                      }
                      return Colors.black87;
                    },
                  ),
                ),
              )),
          const SizedBox(height: 15),
          Obx(() {
            final type = controller.selectedImageType.value;
            String desc = '';
            Color color = Colors.grey;
            switch (type) {
              case ps.ImageType.simple:
                desc =
                    'BEST FOR: Logos, Text, and sharp vectors. (Fast & Clean)';
                color = Colors.green;
              case ps.ImageType.mixed:
                desc = 'BEST FOR: Standard images with balanced details.';
                color = Colors.blue;
              case ps.ImageType.complex:
                desc =
                    'BEST FOR: Intricate designs, shadows, or damaged artwork.';
                color = Colors.orange;
              case ps.ImageType.auto:
                desc =
                    'The system will analyze and pick the best algorithm for you.';
                color = primaryBlue;
            }
            return Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.05),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: color.withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  Icon(Icons.lightbulb_outline, size: 16, color: color),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      desc,
                      style: TextStyle(
                        fontSize: 12,
                        color: color.withOpacity(0.8),
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  // ============= Print Type Section =============
  Widget _buildPrintTypeSection() {
    return Container(
      padding: const EdgeInsets.all(25),
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
                  color: const Color(0xFFE3F2FD),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.print_outlined,
                  color: Color(0xFF1976D2),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '2. Print Type',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 20),
          ...PrintType.values.map((type) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _buildPrintTypeOption(type, Get.find<SetupController>()),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildPrintTypeOption(PrintType type, SetupController controller) {
    bool isSelected = selectedPrintType == type;

    return InkWell(
      onTap: type.isAvailable
          ? () {
              setState(() {
                selectedPrintType = type;
                if (!type.supportsHalftone) {
                  controller.isHalftone.value = false;
                  controller.selectedFinish.value = ps.PrintFinish.solid;
                  showHalftoneSettings = false;
                }
              });
            }
          : null,
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFEFF6FF) : const Color(0xFFF9FAFB),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(
              isSelected
                  ? Icons.radio_button_checked
                  : Icons.radio_button_unchecked,
              color: isSelected ? primaryBlue : const Color(0xFF9CA3AF),
              size: 24,
            ),
            const SizedBox(width: 15),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    type.displayName,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight:
                          isSelected ? FontWeight.bold : FontWeight.normal,
                      color: type.isAvailable ? Colors.black : Colors.grey,
                    ),
                  ),
                  if (!type.isAvailable) ...[
                    const SizedBox(height: 4),
                    const Text(
                      'Coming Soon',
                      style: TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
                    ),
                  ],
                ],
              ),
            ),
            if (!type.isAvailable)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'Coming Soon',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF92400E),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ============= Fabric Type Section =============
  Widget _buildFabricTypeSection() {
    return Container(
      padding: const EdgeInsets.all(25),
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
                  color: const Color(0xFFFCE7F3),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.checkroom,
                  color: Color(0xFFEC4899),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                'Fabric Type',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: FabricType.values.map((fabric) {
              bool isSelected = selectedFabricType == fabric;
              return InkWell(
                onTap: () => setState(() => selectedFabricType = fabric),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: isSelected ? primaryBlue : Colors.white,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
                    ),
                  ),
                  child: Text(
                    fabric.displayName,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: isSelected ? Colors.white : Colors.black87,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  // ============= Detail Level Section =============
  Widget _buildDetailLevelSection() {
    return Container(
      padding: const EdgeInsets.all(25),
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
                  color: const Color(0xFFDCFCE7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.tune,
                  color: Color(0xFF16A34A),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '3. Detail Level',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 15),
          const Text(
            'Affects threshold and vector simplification',
            style: TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
          ),
          const SizedBox(height: 20),
          Row(
            children: DetailLevel.values.map((level) {
              bool isSelected = selectedDetailLevel == level;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 5),
                  child: InkWell(
                    onTap: () {
                      setState(() {
                        selectedDetailLevel = level;
                        if (showHalftoneSettings) {
                          // Recalculate mesh count
                        }
                      });
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 15),
                      decoration: BoxDecoration(
                        color: isSelected ? primaryBlue : Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isSelected
                              ? primaryBlue
                              : const Color(0xFFE5E7EB),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          level.displayName,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: isSelected ? Colors.white : Colors.black87,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  // ============= Print Finish Section =============
  Widget _buildPrintFinishSection(SetupController controller) {
    return Container(
      padding: const EdgeInsets.all(25),
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
                  color: const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.gradient,
                  color: Color(0xFFF59E0B),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '4. Print Finish',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Obx(() => Row(
                children: PrintFinish.values.map((finish) {
                  // Sync with controller value
                  bool isSelected = (controller.selectedFinish.value ==
                              ps.PrintFinish.halftone &&
                          finish == PrintFinish.halftone) ||
                      (controller.selectedFinish.value ==
                              ps.PrintFinish.solid &&
                          finish == PrintFinish.solid);

                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 5),
                      child: InkWell(
                        onTap: () {
                          setState(() {
                            controller.isHalftone.value =
                                (finish == PrintFinish.halftone);
                            controller.selectedFinish.value =
                                (finish == PrintFinish.halftone)
                                    ? ps.PrintFinish.halftone
                                    : ps.PrintFinish.solid;
                            showHalftoneSettings =
                                (finish == PrintFinish.halftone);
                          });
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 15),
                          decoration: BoxDecoration(
                            color: isSelected ? primaryBlue : Colors.white,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isSelected
                                  ? primaryBlue
                                  : const Color(0xFFE5E7EB),
                            ),
                          ),
                          child: Center(
                            child: Text(
                              finish.displayName,
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w600,
                                color:
                                    isSelected ? Colors.white : Colors.black87,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              )),
          if (showHalftoneSettings) ...[
            const SizedBox(height: 25),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFFF9FAFB),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE5E7EB)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '📊 Halftone Settings',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),

                  // LPI Slider
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'LPI (Lines Per Inch)',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        '$lpi',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: primaryBlue,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Text(
                        '45',
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                      Expanded(
                        child: Slider(
                          value: lpi.toDouble(),
                          min: 45,
                          max: 85,
                          divisions: 40,
                          activeColor: primaryBlue,
                          onChanged: (value) {
                            setState(() => lpi = value.toInt());
                            Get.find<SetupController>().lpiValue.value =
                                value.toInt();
                          },
                        ),
                      ),
                      const Text(
                        '85',
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // Mesh Count (Auto)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Mesh Count',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        '$meshCount (Auto)',
                        style: const TextStyle(
                          fontSize: 14,
                          color: Color(0xFF6B7280),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // Dot Shape
                  const Text(
                    'Dot Shape',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: DotShape.values.map((shape) {
                      bool isSelected = selectedDotShape == shape;
                      return Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: InkWell(
                            onTap: () {
                              setState(() => selectedDotShape = shape);
                              Get.find<SetupController>()
                                      .selectedDotShape
                                      .value =
                                  shape.technicalName == 'circle'
                                      ? 'round'
                                      : shape.technicalName;
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: isSelected ? primaryBlue : Colors.white,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: isSelected
                                      ? primaryBlue
                                      : const Color(0xFFE5E7EB),
                                ),
                              ),
                              child: Center(
                                child: Text(
                                  shape.displayName,
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: isSelected
                                        ? Colors.white
                                        : Colors.black87,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // ============= Stroke Width Section =============
  Widget _buildStrokeWidthSection() {
    bool hasWarning = strokeWidth < 0.5 || strokeWidthInPixels < 6;

    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: hasWarning ? const Color(0xFFFBBF24) : const Color(0xFFE5E7EB),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFE0F2FE),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.straighten,
                  color: Color(0xFF0284C7),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '5. Minimum Stroke Width',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Width',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
              ),
              Text(
                '${strokeWidth.toStringAsFixed(1)}mm (≈$strokeWidthInPixels px @ ${printQuality.toInt()} DPI)',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: primaryBlue,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Text(
                '0.5mm',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
              Expanded(
                child: Slider(
                  value: strokeWidth,
                  min: 0.5,
                  max: 2.0,
                  divisions: 15,
                  activeColor:
                      hasWarning ? const Color(0xFFFBBF24) : primaryBlue,
                  onChanged: (value) {
                    setState(() => strokeWidth = value);
                    Get.find<SetupController>().strokeWidth.value = value;
                  },
                ),
              ),
              const Text(
                '2.0mm',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
          if (hasWarning) ...[
            const SizedBox(height: 15),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF3C7),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: const [
                  Icon(Icons.warning_amber, size: 20, color: Color(0xFFF59E0B)),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Strokes below 0.5mm may not print clearly',
                      style: TextStyle(fontSize: 13, color: Color(0xFF92400E)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // ============= Specifications Section =============
  Widget _buildSpecificationsSection() {
    return Container(
      padding: const EdgeInsets.all(25),
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
                  color: const Color(0xFFE0F2F1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.settings_outlined,
                  color: Color(0xFF009688),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                '6. Specifications',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 25),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Paper Size',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 15),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF9FAFB),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFE5E7EB)),
                      ),
                      child: DropdownButton<String>(
                        value: selectedPaperSize,
                        isExpanded: true,
                        underline: const SizedBox(),
                        items: [
                          // CM options (new default)
                          'A4 (21 × 29.7 cm)',
                          'A3 (29.7 × 42 cm)',
                          'A5 (14.8 × 21 cm)',
                          'Letter (21.6 × 27.9 cm)',
                          // MM options (kept for compatibility)
                          'A4 (210 × 297 mm)',
                          'A3 (297 × 420 mm)',
                          'Letter (216 × 279 mm)',
                          // Custom cm-based size
                          'Custom (cm)',
                        ].map((String value) {
                          return DropdownMenuItem<String>(
                            value: value,
                            child: Text(
                              value,
                              style: const TextStyle(fontSize: 14),
                            ),
                          );
                        }).toList(),
                        onChanged: (String? newValue) {
                          if (newValue != null) {
                            setState(() {
                              selectedPaperSize = newValue;
                              // If Custom (cm) selected, show inputs
                              isCustomPaper = newValue == 'Custom (cm)';
                            });
                            // Sync with controller if needed
                            if (newValue == 'Custom (cm)') {
                              // ensure the controller knows current custom values
                              Get.find<SetupController>().paperWidthCm.value =
                                  customPaperWidthCm;
                              Get.find<SetupController>().paperHeightCm.value =
                                  customPaperHeightCm;
                            }
                          }
                        },
                      ),
                    ),
                    if (isCustomPaper) ...[
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                decimal: true,
                              ),
                              decoration: const InputDecoration(
                                labelText: 'Width (cm)',
                                border: OutlineInputBorder(),
                              ),
                              onChanged: (text) {
                                final v =
                                    double.tryParse(text) ?? customPaperWidthCm;
                                setState(() => customPaperWidthCm = v);
                                Get.find<SetupController>().paperWidthCm.value =
                                    v;
                              },
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextField(
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                decimal: true,
                              ),
                              decoration: const InputDecoration(
                                labelText: 'Height (cm)',
                                border: OutlineInputBorder(),
                              ),
                              onChanged: (text) {
                                final v = double.tryParse(text) ??
                                    customPaperHeightCm;
                                setState(() => customPaperHeightCm = v);
                                Get.find<SetupController>()
                                    .paperHeightCm
                                    .value = v;
                              },
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 30),
              Expanded(
                flex: 1,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Copies',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF9FAFB),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFE5E7EB)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          IconButton(
                            onPressed: () {
                              if (copies > 1) setState(() => copies--);
                            },
                            icon: const Icon(Icons.remove, size: 18),
                            color: Colors.grey,
                          ),
                          Text(
                            '$copies',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          IconButton(
                            onPressed: () => setState(() => copies++),
                            icon: const Icon(Icons.add, size: 18),
                            color: Colors.grey,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 25),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Print Quality',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                  ),
                  Text(
                    '${printQuality >= 450 ? "Best" : printQuality >= 300 ? "High" : "Draft"} (${printQuality.toInt()} DPI)',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: primaryBlue,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  const Text(
                    'Draft',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  Expanded(
                    child: Slider(
                      value: printQuality,
                      min: 150,
                      max: 600,
                      divisions: 3,
                      activeColor: primaryBlue,
                      onChanged: (value) {
                        setState(() => printQuality = value);
                        Get.find<SetupController>().printQuality.value = value;
                      },
                    ),
                  ),
                  const Text(
                    'Best',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ============= Advanced Settings Section =============
  Widget _buildAdvancedSettingsSection() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () =>
                setState(() => showAdvancedSettings = !showAdvancedSettings),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  const Icon(Icons.tune, size: 20, color: Color(0xFF6B7280)),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Advanced Settings',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  AnimatedRotation(
                    turns: showAdvancedSettings ? 0.5 : 0.0,
                    duration: const Duration(milliseconds: 200),
                    child: const Icon(
                      Icons.expand_more,
                      color: Color(0xFF6B7280),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (showAdvancedSettings) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  _buildAdvancedOption(
                    'Auto Upscale',
                    autoUpscale,
                    (val) {
                      setState(() => autoUpscale = val);
                      Get.find<SetupController>().autoUpscale.value = val;
                    },
                  ),
                  const SizedBox(height: 16),
                  _buildAdvancedOption(
                    'Remove Background',
                    removeBackground,
                    (val) => setState(() => removeBackground = val),
                  ),
                  const SizedBox(height: 16),
                  _buildAdvancedOption(
                    'Edge Enhancement',
                    edgeEnhancement,
                    (val) {
                      setState(() => edgeEnhancement = val);
                      Get.find<SetupController>().edgeEnhancement.value = val;
                    },
                  ),
                  const SizedBox(height: 16),
                  _buildAdvancedOption(
                    'Color Correction',
                    colorCorrection,
                    (val) {
                      setState(() => colorCorrection = val);
                      Get.find<SetupController>().colorCorrection.value = val;
                    },
                  ),
                  const SizedBox(height: 16),
                  _buildAdvancedOption(
                    'Auto-Adjust Threshold',
                    adaptiveThreshold,
                    (val) {
                      setState(() => adaptiveThreshold = val);
                      Get.find<SetupController>().adaptiveThreshold.value = val;
                    },
                  ),
                  const SizedBox(height: 16),
                  // Smoothing Factor — Auto-config when not Auto mode
                  Obx(() {
                    final ctrl = Get.find<SetupController>();
                    final isAuto =
                        ctrl.selectedImageType.value == ps.ImageType.auto;
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Smoothing Factor',
                                style: TextStyle(fontSize: 14)),
                            Text(
                              ctrl.smoothingFactor.value.toStringAsFixed(2),
                              style: TextStyle(
                                  fontSize: 12,
                                  color: isAuto ? Colors.grey : Colors.green),
                            ),
                          ],
                        ),
                        if (isAuto)
                          Slider(
                            value: ctrl.smoothingFactor.value,
                            min: 0.05,
                            max: 0.50,
                            divisions: 45,
                            onChanged: (val) {
                              ctrl.smoothingFactor.value = val;
                            },
                          )
                        else
                          const Padding(
                            padding: EdgeInsets.only(top: 8.0),
                            child: Text(
                              'Auto-configured based on image type',
                              style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.green,
                                  fontStyle: FontStyle.italic),
                            ),
                          ),
                      ],
                    );
                  }),
                  const SizedBox(height: 16),
                  // Corner Threshold — Auto-config when not Auto mode
                  Obx(() {
                    final ctrl = Get.find<SetupController>();
                    final isAuto =
                        ctrl.selectedImageType.value == ps.ImageType.auto;
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Corner Threshold (°)',
                                style: TextStyle(fontSize: 14)),
                            Text(
                              '${ctrl.cornerThreshold.value.toInt()}°',
                              style: TextStyle(
                                  fontSize: 12,
                                  color: isAuto ? Colors.grey : Colors.green),
                            ),
                          ],
                        ),
                        if (isAuto)
                          Slider(
                            value: ctrl.cornerThreshold.value,
                            min: 0,
                            max: 90,
                            divisions: 90,
                            onChanged: (val) {
                              ctrl.cornerThreshold.value = val;
                            },
                          )
                        else
                          const Padding(
                            padding: EdgeInsets.only(top: 8.0),
                            child: Text(
                              'Auto-configured based on image type',
                              style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.green,
                                  fontStyle: FontStyle.italic),
                            ),
                          ),
                      ],
                    );
                  }),
                  const SizedBox(height: 16),
                  // Corner Threshold Slider
                  Obx(() => Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('Corner Threshold (°)',
                                  style: TextStyle(fontSize: 14)),
                              Text(
                                  '${Get.find<SetupController>().cornerThreshold.value.toInt()}°',
                                  style: const TextStyle(
                                      fontSize: 12, color: Colors.grey)),
                            ],
                          ),
                          Slider(
                            value: Get.find<SetupController>()
                                .cornerThreshold
                                .value,
                            min: 0,
                            max: 90,
                            divisions: 90,
                            onChanged: (val) {
                              Get.find<SetupController>()
                                  .cornerThreshold
                                  .value = val;
                            },
                          ),
                        ],
                      )),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAdvancedOption(
    String title,
    bool value,
    Function(bool) onChanged,
  ) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ),
        Switch(
          value: value,
          onChanged: onChanged,
          activeThumbColor: primaryBlue,
        ),
      ],
    );
  }

  // ============= Output Directory Section =============
  Widget _buildOutputDirectorySection(SetupController controller) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.folder_open, color: Color(0xFF1B4F8A)),
              SizedBox(width: 8),
              Text('مجلد الحفظ', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          Obx(
            () => Text(
              controller.outputDir.value.isEmpty
                  ? 'المجلد الافتراضي (Documents/SilkScreen)'
                  : controller.outputDir.value,
              style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              ElevatedButton.icon(
                onPressed: controller.selectOutputDirectory,
                icon: const Icon(Icons.folder_open, size: 18),
                label: const Text('اختر مجلداً'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1B4F8A),
                  foregroundColor: Colors.white,
                ),
              ),
              const SizedBox(width: 8),
              if (controller.outputDir.value.isNotEmpty)
                TextButton(
                  onPressed: () => controller.outputDir.value = '',
                  child: const Text('إعادة تعيين'),
                ),
            ],
          ),
        ],
      ),
    );
  }

  // ============= Bottom Actions =============
  Widget _buildBottomActions(SetupController controller) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Row(
        children: [
          TextButton(
            onPressed: () {
              controller.resetToDefaults();
              setState(() {
                selectedColorCount = 0;
                selectedDetailLevel = DetailLevel.medium;
                showHalftoneSettings = false;
                lpi = 55;
                selectedDotShape = DotShape.round;
                strokeWidth = 0.5;
                printQuality = 300;
                autoUpscale = true;
                removeBackground = true;
                edgeEnhancement = false;
                colorCorrection = false;
                adaptiveThreshold = false;
              });
            },
            child: const Text(
              'Reset to Defaults',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: controller.startProcessing,
            icon: const Icon(Icons.arrow_forward, size: 18),
            label: const Text(
              'Process & Preview',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            style: ElevatedButton.styleFrom(
              backgroundColor: primaryBlue,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ============= Progress Steps =============
  Widget _buildProgressSteps() {
    return Row(
      children: [
        _buildStep(1, 'Upload File', true, false),
        _buildProgressLine(true),
        _buildStep(2, 'System Setup', false, true),
        _buildProgressLine(false),
        _buildStep(3, 'Print Preview', false, false),
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
    return Expanded(
      child: Container(
        height: 2,
        margin: const EdgeInsets.only(bottom: 30),
        color: isComplete ? Colors.green : const Color(0xFFE5E7EB),
      ),
    );
  }

  // ============= Sidebar =============
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
          _sideButton(Icons.tune, 'System Setup', isActive: true),
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
              Text(
                'Virtua Designer',
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
      child: Row(
        children: [
          CircleAvatar(
            radius: 20,
            backgroundColor: const Color(0xFFFFE4E1),
            child: const Text(
              'JD',
              style: TextStyle(
                color: Color(0xFFFF6B6B),
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 10),
          const Text(
            'Jane Doe',
            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
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
          onTap: () {
            if (text == 'Dashboard') Get.back();
          },
        ),
      ),
    );
  }

  // ============= Top Bar =============
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
            'System Configuration',
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
