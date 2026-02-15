import 'package:flutter/material.dart';

class SetupPage extends StatefulWidget {
  const SetupPage({super.key});

  @override
  State<SetupPage> createState() => _SetupPageState();
}

class _SetupPageState extends State<SetupPage> {
  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color sidebarBlue = Color(0xFF0E3182);
  
  int selectedColorComplexity = 2; // 4 Colors selected by default
  String selectedPaperSize = 'A4 (210 × 297 mm)';
  int copies = 1;
  double printQuality = 300; // DPI

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      body: Row(
        children: [
          // Sidebar
          _buildSidebar(),
          
          // Main Content
          Expanded(
            child: Column(
              children: [
                // Top Bar
                _buildTopBar(),
                
                // Content Area
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(30),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Progress Steps
                        _buildProgressSteps(),
                        
                        const SizedBox(height: 30),
                        
                        // Title
                        const Text(
                          'Print & System Setup',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.black,
                          ),
                        ),
                        
                        const SizedBox(height: 10),
                        
                        // Subtitle
                        const Text(
                          'Configure your print job parameters, finish type, and quality settings below.',
                          style: TextStyle(
                            fontSize: 16,
                            color: Color(0xFF6B7280),
                          ),
                        ),
                        
                        const SizedBox(height: 30),
                        
                        // 1. Color Complexity
                        _buildColorComplexitySection(),
                        
                        const SizedBox(height: 30),
                        
                        // 2. Specifications
                        _buildSpecificationsSection(),
                        
                        const SizedBox(height: 30),
                        
                        // Bottom Actions
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
          _sideButton(Icons.dashboard, 'Dashboard', isActive: false, isClicked: true),
          _sideButton(Icons.tune,isClicked: false, 'System Setup', isActive: true),
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
                'PrintManager',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              Text(
                'v2.4.0 (Desktop)',
                style: TextStyle(fontSize: 10, color: Colors.grey),
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

  Widget _sideButton(IconData icon, String text, {required bool isActive, required bool isClicked}) {
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

  // ================= Top Bar =================
  Widget _buildTopBar() {
    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 30),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
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

  // ================= Progress Steps =================
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

  // ================= Color Complexity Section =================
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
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.black,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 15,
            runSpacing: 15,
            children: [
              _buildColorOption(0, '1 Color', Colors.black),
              _buildColorOption(1, '2 Colors', const Color(0xFFEF4444)),
              _buildColorOption(2, '4 Colors', const Color(0xFF4CAF50)),
              _buildColorOption(3, '8 Colors', const Color(0xFF9C27B0)),
              _buildColorOption(4, '16 Colors', const Color(0xFF00BCD4)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildColorOption(int index, String label, Color iconColor) {
    bool isSelected = selectedColorComplexity == index;
    return InkWell(
      onTap: () {
        setState(() {
          selectedColorComplexity = index;
        });
      },
      child: Container(
        width: 140,
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
                color: iconColor,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              label,
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

  // ================= Specifications Section =================
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
                '2. Specifications',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.black,
                ),
              ),
            ],
          ),
          const SizedBox(height: 25),
          Row(
            children: [
              // Paper Size
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
                        color: Colors.black87,
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
                            setState(() {
                              selectedPaperSize = newValue;
                            });
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 30),
              // Copies
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
                        color: Colors.black87,
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
                              if (copies > 1) {
                                setState(() {
                                  copies--;
                                });
                              }
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
                            onPressed: () {
                              setState(() {
                                copies++;
                              });
                            },
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
          // Print Quality
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Print Quality',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: Colors.black87,
                    ),
                  ),
                  Text(
                    'High (${printQuality.toInt()} DPI)',
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
                  const Text('Draft', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  Expanded(
                    child: Slider(
                      value: printQuality,
                      min: 150,
                      max: 600,
                      divisions: 3,
                      activeColor: primaryBlue,
                      onChanged: (value) {
                        setState(() {
                          printQuality = value;
                        });
                      },
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

  // ================= Bottom Actions =================
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
                selectedColorComplexity = 2;
                selectedPaperSize = 'A4 (210 × 297 mm)';
                copies = 1;
                printQuality = 300;
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
            onPressed: () {},
            icon: const Icon(Icons.arrow_forward, size: 18),
            label: const Text(
              'Preview',
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
}