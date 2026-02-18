// lib/presentation/setup/setup_page.dart

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:virtual_design/core/enums/app_enums.dart';

class SetupPage extends StatefulWidget {
  const SetupPage({super.key});

  @override
  State<SetupPage> createState() => _SetupPageState();
}

class _SetupPageState extends State<SetupPage> {
  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color sidebarBlue = Color(0xFF0E3182);
  
  // State variables
  PrintType selectedPrintType = PrintType.screenPrinting;
  int selectedColorCount = 4;
  DetailLevel selectedDetailLevel = DetailLevel.medium;
  PrintFinish selectedPrintFinish = PrintFinish.solid;
  
  // Halftone settings
  bool showHalftoneSettings = false;
  int lpi = 55;
  DotShape selectedDotShape = DotShape.round;
  
  // Specifications
  double strokeWidth = 0.5;
  String selectedPaperSize = 'A4 (210 × 297 mm)';
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
                          style: TextStyle(fontSize: 16, color: Color(0xFF6B7280)),
                        ),
                        const SizedBox(height: 30),
                        
                        _buildColorComplexitySection(),
                        const SizedBox(height: 30),
                        
                        _buildPrintTypeSection(),
                        const SizedBox(height: 30),
                        
                        if (selectedPrintType.requiresFabricType) ...[
                          _buildFabricTypeSection(),
                          const SizedBox(height: 30),
                        ],
                        
                        _buildDetailLevelSection(),
                        const SizedBox(height: 30),
                        
                        if (selectedPrintType.supportsHalftone) ...[
                          _buildPrintFinishSection(),
                          const SizedBox(height: 30),
                        ],
                        
                        _buildStrokeWidthSection(),
                        const SizedBox(height: 30),
                        
                        _buildSpecificationsSection(),
                        const SizedBox(height: 30),
                        
                        _buildAdvancedSettingsSection(),
                        const SizedBox(height: 30),
                        
                        _buildBottomActions(),
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
                child: const Icon(Icons.palette_outlined, color: Color(0xFF7E57C2), size: 20),
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
            children: [1, 2, 4, 8, 16].map((count) {
              return _buildColorOption(count);
            }).toList(),
          ),
        ],
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
    final colorIndex = [1, 2, 4, 8, 16].indexOf(count);
    
    return InkWell(
      onTap: () => setState(() => selectedColorCount = count),
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
                child: const Icon(Icons.print_outlined, color: Color(0xFF1976D2), size: 20),
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
              child: _buildPrintTypeOption(type),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildPrintTypeOption(PrintType type) {
    bool isSelected = selectedPrintType == type;
    
    return InkWell(
      onTap: type.isAvailable ? () {
        setState(() {
          selectedPrintType = type;
          if (!type.supportsHalftone) {
            selectedPrintFinish = PrintFinish.solid;
            showHalftoneSettings = false;
          }
        });
      } : null,
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
              isSelected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
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
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
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
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
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
                child: const Icon(Icons.checkroom, color: Color(0xFFEC4899), size: 20),
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
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
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
                child: const Icon(Icons.tune, color: Color(0xFF16A34A), size: 20),
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
                          color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
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
  Widget _buildPrintFinishSection() {
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
                child: const Icon(Icons.gradient, color: Color(0xFFF59E0B), size: 20),
              ),
              const SizedBox(width: 12),
              const Text(
                '4. Print Finish',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            children: PrintFinish.values.map((finish) {
              bool isSelected = selectedPrintFinish == finish;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 5),
                  child: InkWell(
                    onTap: () {
                      setState(() {
                        selectedPrintFinish = finish;
                        showHalftoneSettings = finish == PrintFinish.halftone;
                      });
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 15),
                      decoration: BoxDecoration(
                        color: isSelected ? primaryBlue : Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          finish.displayName,
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
                      const Text('LPI (Lines Per Inch)',
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                      Text('$lpi', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: primaryBlue)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Text('45', style: TextStyle(fontSize: 12, color: Colors.grey)),
                      Expanded(
                        child: Slider(
                          value: lpi.toDouble(),
                          min: 45,
                          max: 85,
                          divisions: 40,
                          activeColor: primaryBlue,
                          onChanged: (value) => setState(() => lpi = value.toInt()),
                        ),
                      ),
                      const Text('85', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    ],
                  ),
                  const SizedBox(height: 20),
                  
                  // Mesh Count (Auto)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Mesh Count', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                      Text('$meshCount (Auto)', style: const TextStyle(fontSize: 14, color: Color(0xFF6B7280))),
                    ],
                  ),
                  const SizedBox(height: 20),
                  
                  // Dot Shape
                  const Text('Dot Shape', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 10),
                  Row(
                    children: DotShape.values.map((shape) {
                      bool isSelected = selectedDotShape == shape;
                      return Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: InkWell(
                            onTap: () => setState(() => selectedDotShape = shape),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: isSelected ? primaryBlue : Colors.white,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: isSelected ? primaryBlue : const Color(0xFFE5E7EB),
                                ),
                              ),
                              child: Center(
                                child: Text(
                                  shape.displayName,
                                  style: TextStyle(
                                    fontSize: 13,
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
                child: const Icon(Icons.straighten, color: Color(0xFF0284C7), size: 20),
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
              const Text('Width', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              Text(
                '${strokeWidth.toStringAsFixed(1)}mm (≈$strokeWidthInPixels px @ ${printQuality.toInt()} DPI)',
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: primaryBlue),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Text('0.5mm', style: TextStyle(fontSize: 12, color: Colors.grey)),
              Expanded(
                child: Slider(
                  value: strokeWidth,
                  min: 0.5,
                  max: 2.0,
                  divisions: 15,
                  activeColor: hasWarning ? const Color(0xFFFBBF24) : primaryBlue,
                  onChanged: (value) => setState(() => strokeWidth = value),
                ),
              ),
              const Text('2.0mm', style: TextStyle(fontSize: 12, color: Colors.grey)),
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
                child: const Icon(Icons.settings_outlined, color: Color(0xFF009688), size: 20),
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
                    const Text('Paper Size', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
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
                          'A4 (210 × 297 mm)',
                          'A3 (297 × 420 mm)',
                          'Letter (216 × 279 mm)',
                        ].map((String value) {
                          return DropdownMenuItem<String>(
                            value: value,
                            child: Text(value, style: const TextStyle(fontSize: 14)),
                          );
                        }).toList(),
                        onChanged: (String? newValue) {
                          if (newValue != null) {
                            setState(() => selectedPaperSize = newValue);
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 30),
              
              Expanded(
                flex: 1,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Copies', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
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
                          Text('$copies', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
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
                  const Text('Print Quality', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                  Text(
                    '${printQuality >= 450 ? "Best" : printQuality >= 300 ? "High" : "Draft"} (${printQuality.toInt()} DPI)',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: primaryBlue),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  const Text('Draft', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  Expanded(
                    child: Slider(
                      value: printQuality,
                      min: 150,
                      max: 600,
                      divisions: 3,
                      activeColor: primaryBlue,
                      onChanged: (value) => setState(() => printQuality = value),
                    ),
                  ),
                  const Text('Best', style: TextStyle(fontSize: 12, color: Colors.grey)),
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
            onTap: () => setState(() => showAdvancedSettings = !showAdvancedSettings),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  const Icon(Icons.tune, size: 20, color: Color(0xFF6B7280)),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Advanced Settings',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),
                  Icon(
                    showAdvancedSettings ? Icons.expand_less : Icons.expand_more,
                    color: const Color(0xFF6B7280),
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
                  _buildAdvancedOption('Auto-upscale if needed', autoUpscale, (val) => setState(() => autoUpscale = val)),
                  const SizedBox(height: 15),
                  _buildAdvancedOption('Background removal', removeBackground, (val) => setState(() => removeBackground = val)),
                  const SizedBox(height: 15),
                  _buildAdvancedOption('Edge enhancement', edgeEnhancement, (val) => setState(() => edgeEnhancement = val)),
                  const SizedBox(height: 15),
                  _buildAdvancedOption('Color correction', colorCorrection, (val) => setState(() => colorCorrection = val)),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAdvancedOption(String title, bool value, Function(bool) onChanged) {
    return Row(
      children: [
        Expanded(
          child: Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
        ),
        Switch(
          value: value,
          onChanged: onChanged,
          activeThumbColor: primaryBlue,
        ),
      ],
    );
  }

  // ============= Bottom Actions =============
  Widget _buildBottomActions() {
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
              setState(() {
                selectedPrintType = PrintType.screenPrinting;
                selectedColorCount = 4;
                selectedDetailLevel = DetailLevel.medium;
                selectedPrintFinish = PrintFinish.solid;
                showHalftoneSettings = false;
                strokeWidth = 0.5;
                selectedPaperSize = 'A4 (210 × 297 mm)';
                copies = 1;
                printQuality = 300;
                selectedFabricType = null;
                autoUpscale = true;
                removeBackground = true;
                edgeEnhancement = false;
                colorCorrection = false;
              });
            },
            child: const Text(
              'Reset to Defaults',
              style: TextStyle(fontSize: 14, color: Colors.grey, fontWeight: FontWeight.w600),
            ),
          ),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () {
              // Navigate to Preview
              Get.toNamed('/preview');
            },
            icon: const Icon(Icons.arrow_forward, size: 18),
            label: const Text('Preview', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            style: ElevatedButton.styleFrom(
              backgroundColor: primaryBlue,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
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
            color: isComplete ? Colors.green : isActive ? primaryBlue : const Color(0xFFE5E7EB),
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
              Text('Virtua Designer', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
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
            child: const Text('JD', style: TextStyle(color: Color(0xFFFF6B6B), fontWeight: FontWeight.bold)),
          ),
          const SizedBox(width: 10),
          const Text('Jane Doe', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
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