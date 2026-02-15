import 'package:flutter/material.dart';

class PreviewPage extends StatefulWidget {
  const PreviewPage({super.key});

  @override
  State<PreviewPage> createState() => _PreviewPageState();
}

class _PreviewPageState extends State<PreviewPage> {
  double brightness = 10;
  double contrast = 0;
  String inkDensity = 'High';
  int zoomLevel = 100;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFCECECE),
      body: Column(
        children: [
          // Top App Bar
          _buildTopBar(),
          
          // Main Content Area
          Expanded(
            child: Row(
              children: [
                // Left Side - Image Preview Area (5/6)
                Expanded(
                  flex: 5,
                  child: _buildImagePreviewSection(),
                ),
                
                // Right Side - Job Summary (1/6)
                Expanded(
                  flex: 1,
                  child: _buildJobSummarySection(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // Top Navigation Bar
  Widget _buildTopBar() {
    return Container(
      height: 56,
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          // Preview Title (left side only)
          const Text(
            'Preview',
            style: TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 16,
            ),
          ),
          
          const Spacer(),
          
          // Right side buttons
          IconButton(
            onPressed: () {},
            icon: const Icon(
              Icons.share_outlined,
              color: Color(0xFF585858),
              size: 20,
            ),
            tooltip: 'Share',
          ),
          
          const SizedBox(width: 8),
          
          TextButton(
            onPressed: () {},
            child: const Text(
              'Save',
              style: TextStyle(
                color: Color(0xFF1D3EB8),
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          
          const SizedBox(width: 8),
          
          ElevatedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.print, size: 18),
            label: const Text('Print'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1D3EB8),
              foregroundColor: Colors.white,
              elevation: 0,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            ),
          ),
        ],
      ),
    );
  }

  // Image Preview Section
  Widget _buildImagePreviewSection() {
    return Column(
      children: [
        // Main Preview Area
        Expanded(
          flex: 8,
          child: Container(
            margin: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Stack(
              children: [
                // Grid background
                Positioned.fill(
                  child: CustomPaint(
                    painter: GridPainter(),
                  ),
                ),
                
                // Image and pen preview
                Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Blueprint/Floor plan image
                      Container(
                        width: 400,
                        height: 400,
                        color: Colors.grey[300],
                        child: const Center(
                          child: Text(
                            'Image Preview',
                            style: TextStyle(color: Colors.grey),
                          ),
                        ),
                      ),
                      
                      const SizedBox(height: 20),
                      
                      // Pen/Pencil graphic
                      Image.asset(
                        'assets/pen.png',
                        width: 200,
                        height: 100,
                        errorBuilder: (context, error, stackTrace) {
                          return Container(
                            width: 200,
                            height: 100,
                            color: Colors.amber[100],
                            child: const Icon(Icons.edit, size: 40),
                          );
                        },
                      ),
                    ],
                  ),
                ),
                
                // Zoom controls (top center)
                Positioned(
                  top: 16,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: _buildZoomControls(),
                  ),
                ),
              ],
            ),
          ),
        ),
        
        // Bottom Controls Area
        Expanded(
          flex: 1,
          child: _buildControlsSection(),
        ),
      ],
    );
  }

  // Zoom Controls
  Widget _buildZoomControls() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            onPressed: () {
              setState(() {
                if (zoomLevel > 10) zoomLevel -= 10;
              });
            },
            icon: const Icon(Icons.remove, size: 18),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
          
          const SizedBox(width: 8),
          
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey[300]!),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              '$zoomLevel%',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          
          const SizedBox(width: 8),
          
          IconButton(
            onPressed: () {
              setState(() {
                if (zoomLevel < 200) zoomLevel += 10;
              });
            },
            icon: const Icon(Icons.add, size: 18),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
          
          const VerticalDivider(width: 24),
          
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.refresh, size: 18),
            tooltip: 'Reset',
          ),
          
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.fit_screen, size: 18),
            tooltip: 'Fit to screen',
          ),
          
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.grid_on, size: 18),
            tooltip: 'Toggle grid',
          ),
        ],
      ),
    );
  }

  // Bottom Controls Section (Tabs + Sliders)
  Widget _buildControlsSection() {
    return Container(
      color: Colors.white,
      child: Column(
        children: [
          // Tabs
          Container(
            height: 48,
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(color: Colors.grey[300]!),
              ),
            ),
            child: Row(
              children: [
                _buildTab('Adjustments', isSelected: true),
                _buildTab('Measurements', isSelected: false),
                _buildTab('Bleed & Crop', isSelected: false),
              ],
            ),
          ),
          
          // Sliders
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: _buildSlider(
                      icon: Icons.brightness_6,
                      label: 'BRIGHTNESS',
                      value: brightness,
                      displayValue: '+${brightness.toInt()}%',
                      onChanged: (val) => setState(() => brightness = val),
                      min: -100,
                      max: 100,
                    ),
                  ),
                  
                  const SizedBox(width: 32),
                  
                  Expanded(
                    child: _buildSlider(
                      icon: Icons.contrast,
                      label: 'CONTRAST',
                      value: contrast,
                      displayValue: '${contrast.toInt()}%',
                      onChanged: (val) => setState(() => contrast = val),
                      min: -100,
                      max: 100,
                    ),
                  ),
                  
                  const SizedBox(width: 32),
                  
                  Expanded(
                    child: _buildInkDensitySelector(),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTab(String label, {required bool isSelected}) {
    return Expanded(
      child: InkWell(
        onTap: () {},
        child: Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: isSelected ? const Color(0xFF1D3EB8) : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 14,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
              color: isSelected ? const Color(0xFF1D3EB8) : Colors.grey[600],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSlider({
    required IconData icon,
    required String label,
    required double value,
    required String displayValue,
    required ValueChanged<double> onChanged,
    required double min,
    required double max,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: Colors.grey[600]),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.grey[600],
              ),
            ),
            const Spacer(),
            Text(
              displayValue,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 8),
        
        SliderTheme(
          data: SliderTheme.of(context).copyWith(
            trackHeight: 2,
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
            overlayShape: const RoundSliderOverlayShape(overlayRadius: 12),
          ),
          child: Slider(
            value: value,
            min: min,
            max: max,
            activeColor: const Color(0xFF1D3EB8),
            onChanged: onChanged,
          ),
        ),
      ],
    );
  }

  Widget _buildInkDensitySelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.opacity, size: 16, color: Colors.grey[600]),
            const SizedBox(width: 8),
            Text(
              'INK DENSITY',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.grey[600],
              ),
            ),
            const Spacer(),
            Text(
              inkDensity,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        
        const SizedBox(height: 8),
        
        Row(
          children: [
            Expanded(
              child: _buildDensityButton('Eco', inkDensity == 'Eco'),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildDensityButton('Std', inkDensity == 'Std'),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildDensityButton('High', inkDensity == 'High'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDensityButton(String label, bool isSelected) {
    return InkWell(
      onTap: () => setState(() => inkDensity = label),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF1D3EB8) : Colors.transparent,
          border: Border.all(
            color: isSelected ? const Color(0xFF1D3EB8) : Colors.grey[300]!,
          ),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: isSelected ? Colors.white : Colors.grey[700],
          ),
        ),
      ),
    );
  }

  // Job Summary Section
  Widget _buildJobSummarySection() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Text(
                'Job Summary',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 16,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green[50],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.check_circle, size: 14, color: Colors.green[700]),
                    const SizedBox(width: 4),
                    Text(
                      'READY',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: Colors.green[700],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 24),
          
          // Estimated Cost
          const Center(
            child: Column(
              children: [
                Text(
                  'Estimated Cost',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  '\$12.50',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF1D3EB8),
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Estimated Time
          _buildInfoRow(
            icon: Icons.timer,
            label: 'Est. Time',
            value: '4m 30s',
          ),
          
          const Divider(height: 32),
          
          // Print Settings Header
          const Text(
            'PRINT SETTINGS',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: Colors.grey,
              letterSpacing: 0.5,
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Paper Type
          _buildSettingRow(
            icon: Icons.description_outlined,
            iconColor: const Color(0xFF1D3EB8),
            title: 'Paper Type',
            value: 'A3 Glossy',
          ),
          
          const SizedBox(height: 16),
          
          // Dimensions
          _buildSettingRow(
            icon: Icons.straighten,
            iconColor: const Color(0xFF9C27B0),
            title: 'Dimensions',
            value: '297 × 420 mm',
          ),
          
          const SizedBox(height: 16),
          
          // Resolution
          _buildSettingRow(
            icon: Icons.high_quality,
            iconColor: const Color(0xFFFF9800),
            title: 'Resolution',
            value: '300 DPI',
          ),
          
          const SizedBox(height: 16),
          
          // Color Mode
          _buildSettingRow(
            icon: Icons.palette_outlined,
            iconColor: const Color(0xFF4CAF50),
            title: 'Color Mode',
            value: 'CMYK',
          ),
          
          const Spacer(),
          
          // Printer Status
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.green[50],
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.green[200]!),
            ),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: Colors.green[600],
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'HP DesignJet T650',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        'Online • Ink Levels OK',
                        style: TextStyle(
                          fontSize: 10,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Row(
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 13,
            color: Colors.grey,
          ),
        ),
        const Spacer(),
        Icon(icon, size: 16, color: Colors.grey),
        const SizedBox(width: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildSettingRow({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String value,
  }) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: iconColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, size: 18, color: iconColor),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// Grid Painter for background
class GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.grey[300]!
      ..strokeWidth = 0.5;

    const gridSize = 40.0;

    // Vertical lines
    for (double x = 0; x < size.width; x += gridSize) {
      canvas.drawLine(
        Offset(x, 0),
        Offset(x, size.height),
        paint,
      );
    }

    // Horizontal lines
    for (double y = 0; y < size.height; y += gridSize) {
      canvas.drawLine(
        Offset(0, y),
        Offset(size.width, y),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}