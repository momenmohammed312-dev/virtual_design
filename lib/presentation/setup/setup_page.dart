// lib/presentation/setup/setup_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:virtual_design/core/enums/app_enums.dart';
import 'package:virtual_design/domain/entities/processing_settings.dart' as ps;
import 'package:virtual_design/presentation/setup/setup_controller.dart';

class SetupPage extends StatefulWidget {
  const SetupPage({super.key});

  @override
  State<SetupPage> createState() => _SetupPageState();
}

class _SetupPageState extends State<SetupPage> {
  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color sidebarBlue = Color(0xFF0E3182);
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  // State variables
  PrintType selectedPrintType = PrintType.screenPrinting;
  int selectedColorCount = 0;
  DetailLevel selectedDetailLevel = DetailLevel.medium;

  // Halftone settings
  bool showHalftoneSettings = false;
  int lpi = 85;
  DotShape selectedDotShape = DotShape.round;

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
  bool responsiveMode = false;

  int get meshCount {
    if (lpi < 45) return 110;
    if (lpi < 55) return 160;
    if (lpi < 70) return 200;
    if (lpi < 85) return 230;
    if (lpi < 105) return 280;
    if (lpi < 130) return 305;
    return 355;
  }

  int get strokeWidthInPixels {
    final strokeWidthCm = strokeWidth / 10;
    final strokeWidthInches = strokeWidthCm / 2.54;
    return (strokeWidthInches * printQuality).round();
  }

  @override
  void initState() {
    super.initState();
    final controller = Get.find<SetupController>();
    selectedColorCount = controller.selectedColors.value;
    switch (controller.selectedDetail.value) {
      case ps.DetailLevel.high:
        selectedDetailLevel = DetailLevel.high;
        break;
      case ps.DetailLevel.medium:
        selectedDetailLevel = DetailLevel.medium;
        break;
      case ps.DetailLevel.low:
        selectedDetailLevel = DetailLevel.low;
        break;
    }
    lpi = controller.lpiValue.value;
    strokeWidth = controller.strokeWidth.value;
    printQuality = controller.printQuality.value;
    autoUpscale = controller.autoUpscale.value;
    removeBackground = controller.removeBackground.value;
    edgeEnhancement = controller.edgeEnhancement.value;
    colorCorrection = controller.colorCorrection.value;
    adaptiveThreshold = controller.adaptiveThreshold.value;
    responsiveMode = controller.responsiveMode.value;
    showHalftoneSettings = controller.isHalftone.value;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final bool isDesktop = constraints.maxWidth >= 900;
        return Scaffold(
          key: _scaffoldKey,
          backgroundColor: const Color(0xFFF5F5F5),
          drawer: isDesktop ? null : _buildSidebar(isDrawer: true),
          body: GetBuilder<SetupController>(
            builder: (controller) => Stack(
              children: [
                Row(
                  children: [
                    if (isDesktop) _buildSidebar(),
                    Expanded(
                      child: Column(
                        children: [
                          _buildTopBar(!isDesktop, _scaffoldKey),
                          Expanded(
                            child: SingleChildScrollView(
                              key: const PageStorageKey('setup_scroll'),
                              padding: EdgeInsets.all(isDesktop ? 30 : 15),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  _buildProgressSteps(isDesktop),
                                  const SizedBox(height: 30),
                                  const Text(
                                    'Production Parameters',
                                    style: TextStyle(
                                      fontSize: 28,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.black,
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  const Text(
                                    'Configure your print job parameters, finish type, and high-fidelity quality settings.',
                                    style: TextStyle(
                                      fontSize: 14,
                                      color: Color(0xFF6B7280),
                                    ),
                                  ),
                                  const SizedBox(height: 30),
                                  _buildColorComplexitySection(isDesktop),
                                  const SizedBox(height: 30),
                                  _buildDetailLevelSection(isDesktop),
                                  const SizedBox(height: 30),
                                  _buildPrintFinishSection(
                                      controller, isDesktop),
                                  const SizedBox(height: 30),
                                  _buildSpecificationsSection(isDesktop),
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
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 400),
                            child: Card(
                              color: Colors.white,
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16)),
                              child: Padding(
                                padding: const EdgeInsets.all(24),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.hourglass_bottom,
                                        size: 48, color: primaryBlue),
                                    const SizedBox(height: 16),
                                    const Text('Processing Image',
                                        style: TextStyle(
                                            fontSize: 20,
                                            fontWeight: FontWeight.bold)),
                                    const SizedBox(height: 24),
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(8),
                                      child: LinearProgressIndicator(
                                        minHeight: 6,
                                        value: controller.progress.value,
                                        backgroundColor:
                                            const Color(0xFFE5E7EB),
                                        valueColor:
                                            const AlwaysStoppedAnimation<Color>(
                                                primaryBlue),
                                      ),
                                    ),
                                    const SizedBox(height: 12),
                                    Text(
                                        '${(controller.progress.value * 100).toStringAsFixed(0)}%',
                                        style: const TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w600,
                                            color: primaryBlue)),
                                    const SizedBox(height: 16),
                                    Obx(() => Text(
                                        controller.progressMessage.value,
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                            fontSize: 13,
                                            color: Color(0xFF6B7280)))),
                                  ],
                                ),
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
      },
    );
  }

  // ============= Widgets =============

  Widget _buildSidebar({bool isDrawer = false}) {
    return Container(
      width: 280,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [sidebarBlue, sidebarBlue.withBlue(100)],
        ),
      ),
      child: Column(
        children: [
          const SizedBox(height: 60),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(30),
              shape: BoxShape.circle,
            ),
            child:
                const Icon(Icons.print_rounded, color: Colors.white, size: 40),
          ),
          const SizedBox(height: 20),
          const Text(
            'VIRTUAL DESIGNER',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.5,
            ),
          ),
          const Text(
            'SCREEN PRINTING STUDIO',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 11,
              fontWeight: FontWeight.w300,
              letterSpacing: 2.0,
            ),
          ),
          const SizedBox(height: 50),
          _buildSidebarItem(
              Icons.dashboard_customize_outlined, 'Job Setup', true),
          _buildSidebarItem(Icons.layers_outlined, 'Separations', false),
          _buildSidebarItem(Icons.analytics_outlined, 'Live Analysis', false),
          _buildSidebarItem(Icons.history_rounded, 'Archived Jobs', false),
          const Spacer(),
          Container(
            padding: const EdgeInsets.all(20),
            width: double.infinity,
            color: Colors.black.withAlpha(40),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('SYSTEM STATUS',
                    style: TextStyle(
                        color: Colors.white54,
                        fontSize: 10,
                        fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                            color: Colors.greenAccent, shape: BoxShape.circle)),
                    const SizedBox(width: 8),
                    const Text('ENGINE READY',
                        style: TextStyle(color: Colors.white, fontSize: 11)),
                  ],
                ),
                const SizedBox(height: 15),
                const Text('v1.1.0',
                    style: TextStyle(color: Colors.white24, fontSize: 10)),
                const SizedBox(height: 8),
                Text('MO2 CAPITAL',
                    style: TextStyle(
                        color: Colors.white.withAlpha(80),
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 1.5)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSidebarItem(IconData icon, String title, bool isSelected) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 15, vertical: 5),
      decoration: BoxDecoration(
        color: isSelected ? Colors.white.withAlpha(25) : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
      ),
      child: ListTile(
        leading: Icon(icon, color: isSelected ? Colors.white : Colors.white60),
        title: Text(title,
            style: TextStyle(
                color: isSelected ? Colors.white : Colors.white60,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal),
            overflow: TextOverflow.ellipsis),
        onTap: () {
          Get.snackbar(
            'Navigating to $title',
            'This feature is being initialized in the next build.',
            snackPosition: SnackPosition.BOTTOM,
            backgroundColor: sidebarBlue.withAlpha(200),
            colorText: Colors.white,
          );
        },
      ),
    );
  }

  Widget _buildTopBar(bool showMenu, GlobalKey<ScaffoldState> scaffoldKey) {
    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      color: Colors.white,
      child: Row(
        children: [
          if (showMenu)
            IconButton(
                onPressed: () => scaffoldKey.currentState?.openDrawer(),
                icon: const Icon(Icons.menu),
                color: primaryBlue),
          const SizedBox(width: 10),
          const Expanded(
            child: Text('System Configuration',
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ),
          const Spacer(),
          IconButton(
              onPressed: () {},
              icon: const Icon(Icons.notifications_none_outlined),
              color: Colors.grey),
        ],
      ),
    );
  }

  Widget _buildProgressSteps(bool isDesktop) {
    return Row(
      children: [
        _buildStepItem('IMAGE', true, true, isDesktop),
        _buildStepLine(true),
        _buildStepItem('SETUP', true, false, isDesktop),
        _buildStepLine(false),
        _buildStepItem('PREVIEW', false, false, isDesktop),
      ],
    );
  }

  Widget _buildStepItem(
      String title, bool isCompleted, bool isActive, bool isDesktop) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 24,
          height: 24,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isCompleted
                ? primaryBlue
                : (isActive
                    ? primaryBlue.withAlpha(50)
                    : const Color(0xFFE5E7EB)),
          ),
          child: Center(
            child: isCompleted
                ? const Icon(Icons.check, color: Colors.white, size: 14)
                : Text('1',
                    style: TextStyle(
                        color: isActive ? primaryBlue : Colors.grey,
                        fontSize: 12,
                        fontWeight: FontWeight.bold)),
          ),
        ),
        if (isDesktop) const SizedBox(width: 8),
        if (isDesktop)
          Text(
            title,
            style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: isCompleted || isActive ? Colors.black87 : Colors.grey),
            overflow: TextOverflow.ellipsis,
          ),
      ],
    );
  }

  Widget _buildStepLine(bool isCompleted) {
    return Expanded(
        child: Container(
            height: 2,
            margin: const EdgeInsets.symmetric(horizontal: 10),
            color: isCompleted ? primaryBlue : const Color(0xFFE5E7EB)));
  }

  Widget _buildColorComplexitySection(bool isDesktop) {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                      color: const Color(0xFFEDE7F6),
                      borderRadius: BorderRadius.circular(8)),
                  child: const Icon(Icons.palette_outlined,
                      color: Color(0xFF7E57C2), size: 20)),
              const SizedBox(width: 12),
              const Expanded(
                  child: Text('1. Color Complexity',
                      style:
                          TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      overflow: TextOverflow.ellipsis)),
            ],
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 15,
            runSpacing: 15,
            alignment: isDesktop ? WrapAlignment.start : WrapAlignment.center,
            children: [
              _buildAutoColorOption(isDesktop),
              ...[1, 2, 3, 4, 5, 6, 7, 8]
                  .map((count) => _buildColorOption(count, isDesktop)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAutoColorOption(bool isDesktop) {
    bool isSelected = selectedColorCount == 0;
    return InkWell(
      onTap: () {
        setState(() => selectedColorCount = 0);
        Get.find<SetupController>().selectedColors.value = 0;
      },
      child: Container(
        width: isDesktop ? 130 : 110,
        height: isDesktop ? 100 : 90,
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
                width: isSelected ? 2 : 1)),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
                width: 35,
                height: 35,
                decoration: const BoxDecoration(
                    shape: BoxShape.circle, color: Color(0xFF9C27B0)),
                child: const Icon(Icons.auto_awesome,
                    size: 20, color: Colors.white)),
            const SizedBox(height: 10),
            Text('Auto',
                style: TextStyle(
                    fontSize: 14,
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? primaryBlue : Colors.black87)),
          ],
        ),
      ),
    );
  }

  Widget _buildColorOption(int count, bool isDesktop) {
    bool isSelected = selectedColorCount == count;
    final colors = [
      Colors.black,
      Colors.black,
      const Color(0xFFEF4444),
      const Color(0xFF4CAF50),
      const Color(0xFF9C27B0),
      const Color(0xFF00BCD4),
      Colors.deepOrange,
      Colors.teal,
      Colors.indigo
    ];
    return InkWell(
      onTap: () {
        setState(() => selectedColorCount = count);
        Get.find<SetupController>().selectedColors.value = count;
      },
      child: Container(
        width: isDesktop ? 130 : 110,
        height: isDesktop ? 100 : 90,
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
                color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
                width: isSelected ? 2 : 1)),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
                width: 35,
                height: 35,
                decoration: BoxDecoration(
                    shape: BoxShape.circle, color: colors[count])),
            const SizedBox(height: 10),
            Text('$count Colors',
                style: TextStyle(
                    fontSize: 14,
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? primaryBlue : Colors.black87)),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailLevelSection(bool isDesktop) {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                      color: const Color(0xFFDCFCE7),
                      borderRadius: BorderRadius.circular(8)),
                  child: const Icon(Icons.tune,
                      color: Color(0xFF16A34A), size: 20)),
              const SizedBox(width: 12),
              const Expanded(
                child: Text('2. Detail Level',
                    overflow: TextOverflow.ellipsis,
                    style:
                        TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 20),
          isDesktop
              ? Row(
                  children: DetailLevel.values
                      .map((level) => Expanded(child: _buildDetailItem(level)))
                      .toList())
              : Column(
                  children: DetailLevel.values
                      .map((level) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _buildDetailItem(level)))
                      .toList()),
        ],
      ),
    );
  }

  Widget _buildDetailItem(DetailLevel level) {
    bool isSelected = selectedDetailLevel == level;
    return InkWell(
      onTap: () => setState(() => selectedDetailLevel = level),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 15),
        decoration: BoxDecoration(
            color: isSelected ? primaryBlue : Colors.white,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
                color: isSelected ? primaryBlue : const Color(0xFFE5E7EB))),
        child: Center(
            child: Text(level.displayName,
                style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: isSelected ? Colors.white : Colors.black87))),
      ),
    );
  }

  Widget _buildPrintFinishSection(SetupController controller, bool isDesktop) {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                      color: const Color(0xFFFEF3C7),
                      borderRadius: BorderRadius.circular(8)),
                  child: const Icon(Icons.gradient,
                      color: Color(0xFFF59E0B), size: 20)),
              const SizedBox(width: 12),
              const Expanded(
                child: Text('3. Print Finish',
                    overflow: TextOverflow.ellipsis,
                    style:
                        TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Obx(() => isDesktop
              ? Row(
                  children: PrintFinish.values
                      .map((finish) => Expanded(
                          child: _buildPrintFinishItem(controller, finish)))
                      .toList())
              : Column(
                  children: PrintFinish.values
                      .map((finish) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _buildPrintFinishItem(controller, finish)))
                      .toList())),
          if (showHalftoneSettings) ...[
            const SizedBox(height: 25),
            _buildHalftoneSettings(),
          ],
        ],
      ),
    );
  }

  Widget _buildPrintFinishItem(SetupController controller, PrintFinish finish) {
    bool isSelected =
        (controller.selectedFinish.value == ps.PrintFinish.halftone &&
                finish == PrintFinish.halftone) ||
            (controller.selectedFinish.value == ps.PrintFinish.solid &&
                finish == PrintFinish.solid);
    return InkWell(
      onTap: () {
        setState(() {
          final bool isHalftoneSelected = (finish == PrintFinish.halftone);
          controller.isHalftone.value = isHalftoneSelected;
          controller.selectedFinish.value = isHalftoneSelected
              ? ps.PrintFinish.halftone
              : ps.PrintFinish.solid;
          showHalftoneSettings = isHalftoneSelected;
          Get.log(
              '[SetupPage] Finish selected: $finish, isHalftone=$isHalftoneSelected, selectedFinish=${controller.selectedFinish.value}');
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 15),
        decoration: BoxDecoration(
            color: isSelected ? primaryBlue : Colors.white,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
                color: isSelected ? primaryBlue : const Color(0xFFE5E7EB))),
        child: Center(
            child: Text(finish.displayName,
                style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: isSelected ? Colors.white : Colors.black87))),
      ),
    );
  }

  Widget _buildHalftoneSettings() {
    return Container(
      padding: const EdgeInsets.all(20),
      color: const Color(0xFFF9FAFB),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Halftone Parameters',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 15),
          Row(
            children: [
              const Text('LPI'),
              Expanded(
                  child: Slider(
                      value: lpi.toDouble(),
                      min: 65,
                      max: 150,
                      divisions: 85,
                      activeColor: primaryBlue,
                      onChanged: (v) => setState(() => lpi = v.toInt()))),
              Text('$lpi'),
            ],
          ),
          const SizedBox(height: 15),
          Row(
            children: DotShape.values.map((shape) {
              bool isSelected = selectedDotShape == shape;
              return Expanded(
                  child: InkWell(
                onTap: () => setState(() => selectedDotShape = shape),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                      color: isSelected ? primaryBlue : Colors.white,
                      border: Border.all(color: const Color(0xFFE5E7EB))),
                  child: Center(
                      child: Text(shape.displayName,
                          style: TextStyle(
                              color: isSelected ? Colors.white : Colors.black87,
                              fontSize: 12))),
                ),
              ));
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildDPISlider() {
    String qualityLabel = 'Standard';
    Color qualityColor = Colors.grey;
    if (printQuality >= 4800) {
      qualityLabel = 'MAX QUALITY (Extreme)';
      qualityColor = Colors.deepOrange;
    } else if (printQuality >= 2400) {
      qualityLabel = 'Ultra Resolution';
      qualityColor = Colors.purple;
    } else if (printQuality >= 1200) {
      qualityLabel = 'High Fidelity';
      qualityColor = primaryBlue;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.high_quality_outlined,
                size: 18, color: Colors.black54),
            const SizedBox(width: 8),
            const Expanded(
                child: Text('Print Resolution (DPI)',
                    style: TextStyle(fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis)),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                  color: qualityColor.withAlpha(30),
                  borderRadius: BorderRadius.circular(4)),
              child: Text(qualityLabel,
                  style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: qualityColor)),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Slider(
          value: printQuality.clamp(300, 4800),
          min: 300,
          max: 4800,
          divisions: 15,
          activeColor: qualityColor,
          label: '${printQuality.toInt()} DPI',
          onChanged: (v) {
            setState(() {
              printQuality = v;
              Get.find<SetupController>().printQuality.value = v;
            });
          },
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('300',
                style: TextStyle(fontSize: 10, color: Colors.grey)),
            const Text('1200',
                style: TextStyle(fontSize: 10, color: Colors.grey)),
            const Text('2400',
                style: TextStyle(fontSize: 10, color: Colors.grey)),
            const Text('4800',
                style: TextStyle(fontSize: 10, color: Colors.grey)),
          ],
        ),
      ],
    );
  }

  Widget _buildSpecificationsSection(bool isDesktop) {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(
        children: [
          _buildDPISlider(),
          const SizedBox(height: 30),
          const Divider(height: 1, color: Color(0xFFF3F4F6)),
          const SizedBox(height: 30),
          isDesktop
              ? Row(children: [
                  Expanded(child: _buildPaperSizeColumn()),
                  const SizedBox(width: 30),
                  Expanded(child: _buildCopiesColumn())
                ])
              : Column(children: [
                  _buildPaperSizeColumn(),
                  const SizedBox(height: 20),
                  _buildCopiesColumn()
                ]),
        ],
      ),
    );
  }

  Widget _buildPaperSizeColumn() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Paper Size', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        DropdownButton<String>(
          value: selectedPaperSize,
          isExpanded: true,
          items: [
            'A4 (21 × 29.7 cm)',
            'A3 (29.7 × 42 cm)',
            'A5 (14.8 × 21 cm)',
            'Letter (21.6 × 27.9 cm)',
            'Custom (cm)'
          ].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
          onChanged: (v) {
            if (v != null) {
              setState(() {
                selectedPaperSize = v;
                isCustomPaper = (v == 'Custom (cm)');
              });
            }
          },
        ),
      ],
    );
  }

  Widget _buildCopiesColumn() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Copies', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        Row(children: [
          IconButton(
              onPressed: () {
                if (copies > 1) setState(() => copies--);
              },
              icon: const Icon(Icons.remove)),
          Text('$copies',
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          IconButton(
              onPressed: () => setState(() => copies++),
              icon: const Icon(Icons.add)),
        ]),
      ],
    );
  }

  Widget _buildAdvancedSettingsSection() {
    return Column(
      children: [
        ListTile(
            title: const Text('Advanced Settings'),
            trailing: Icon(
                showAdvancedSettings ? Icons.expand_less : Icons.expand_more),
            onTap: () =>
                setState(() => showAdvancedSettings = !showAdvancedSettings)),
        if (showAdvancedSettings)
          Wrap(
            spacing: 10,
            children: [
              _buildAdvancedOption('Auto Upscale', autoUpscale,
                  (v) => setState(() => autoUpscale = v)),
              _buildAdvancedOption('Edge Enhancement', edgeEnhancement,
                  (v) => setState(() => edgeEnhancement = v)),
              _buildAdvancedOption(
                  'Responsive Mode',
                  responsiveMode,
                  (v) => setState(() {
                        responsiveMode = v;
                        Get.find<SetupController>().responsiveMode.value = v;
                      })),
            ],
          ),
      ],
    );
  }

  Widget _buildAdvancedOption(
      String label, bool value, Function(bool) onChanged) {
    return FilterChip(
        label: Text(label),
        selected: value,
        onSelected: onChanged,
        selectedColor: primaryBlue.withAlpha(50));
  }

  Widget _buildOutputDirectorySection(SetupController controller) {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Row(children: [
        const Icon(Icons.folder_open),
        const SizedBox(width: 15),
        const Expanded(child: Text('Output Directory')),
        TextButton(onPressed: () {}, child: const Text('Change'))
      ]),
    );
  }

  Widget _buildBottomActions(SetupController controller) {
    return Row(children: [
      Expanded(
          child: OutlinedButton(
              onPressed: () {}, child: const Text('Save Template'))),
      const SizedBox(width: 20),
      Expanded(
        child: ElevatedButton(
          onPressed: () => controller.startProcessing(),
          style: ElevatedButton.styleFrom(
              backgroundColor: primaryBlue, foregroundColor: Colors.white),
          child: const Text('START PROCESSING'),
        ),
      ),
    ]);
  }
}
