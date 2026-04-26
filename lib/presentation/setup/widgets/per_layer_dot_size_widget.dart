import 'package:flutter/material.dart';

class PerLayerDotSizeWidget extends StatefulWidget {
  final int colorCount;
  final int baseLpi;
  final Function(List<double>) onChanged;

  const PerLayerDotSizeWidget({
    super.key,
    required this.colorCount,
    required this.baseLpi,
    required this.onChanged,
  });

  @override
  State<PerLayerDotSizeWidget> createState() => _PerLayerDotSizeWidgetState();
}

class _PerLayerDotSizeWidgetState extends State<PerLayerDotSizeWidget> {
  late List<double> multipliers;
  bool isLinked = false;

  final List<Color> layerColors = [
    Colors.black,
    Colors.red,
    Colors.green,
    Colors.blue,
    Colors.orange,
    Colors.purple,
    Colors.teal,
    Colors.indigo,
    Colors.brown,
    Colors.cyan,
    Colors.pink,
    Colors.lime,
  ];

  @override
  void initState() {
    super.initState();
    multipliers =
        List.filled(widget.colorCount > 0 ? widget.colorCount : 1, 0.7);
  }

  @override
  void didUpdateWidget(PerLayerDotSizeWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.colorCount != widget.colorCount) {
      final currentMultipliers = List<double>.from(multipliers);
      multipliers =
          List.filled(widget.colorCount > 0 ? widget.colorCount : 1, 0.7);
      for (int i = 0;
          i < currentMultipliers.length && i < multipliers.length;
          i++) {
        multipliers[i] = currentMultipliers[i];
      }
      WidgetsBinding.instance
          .addPostFrameCallback((_) => widget.onChanged(multipliers));
    }
  }

  void _updateMultiplier(int index, double value) {
    setState(() {
      if (isLinked) {
        for (int i = 0; i < multipliers.length; i++) {
          multipliers[i] = value;
        }
      } else {
        multipliers[index] = value;
      }
    });
    widget.onChanged(multipliers);
  }

  String _getLabel(double multiplier) {
    if (multiplier <= 0.4) return 'Extra Fine';
    if (multiplier <= 0.6) return 'Fine';
    if (multiplier <= 0.8) return 'Normal';
    if (multiplier <= 1.0) return 'Bold';
    return 'Very Bold';
  }

  int _getEffectiveLpi(double multiplier) {
    if (multiplier <= 0) multiplier = 0.5;
    return (widget.baseLpi / multiplier).round().clamp(25, 300);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Layer Dot Sizes',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              Row(
                children: [
                  IconButton(
                    icon: Icon(isLinked ? Icons.link : Icons.link_off,
                        color: isLinked ? Colors.blue : Colors.grey),
                    tooltip: 'Link All Layers',
                    onPressed: () {
                      setState(() {
                        isLinked = !isLinked;
                        if (isLinked && multipliers.isNotEmpty) {
                          double first = multipliers[0];
                          for (int i = 0; i < multipliers.length; i++) {
                            multipliers[i] = first;
                          }
                          widget.onChanged(multipliers);
                        }
                      });
                    },
                  ),
                  TextButton.icon(
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('Reset'),
                    onPressed: () {
                      setState(() {
                        multipliers = List.filled(multipliers.length, 0.7);
                        widget.onChanged(multipliers);
                      });
                    },
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (multipliers.isEmpty || (widget.colorCount == 0))
            const Text('Auto color selected. Apply image first.',
                style: TextStyle(fontStyle: FontStyle.italic)),
          if ((widget.colorCount > 0))
            ...List.generate(multipliers.length, (index) {
              Color c = layerColors[index % layerColors.length];
              double val = multipliers[index];
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8.0),
                child: Row(
                  children: [
                    Container(
                      width: 20,
                      height: 20,
                      decoration:
                          BoxDecoration(color: c, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 8),
                    Text('L${index + 1}',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Slider(
                        value: val.clamp(0.3, 1.2),
                        min: 0.3,
                        max: 1.2,
                        divisions: 18,
                        activeColor: c,
                        onChanged: (v) => _updateMultiplier(index, v),
                      ),
                    ),
                    SizedBox(
                      width: 80,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(_getLabel(val),
                              style: const TextStyle(
                                  fontSize: 12, fontWeight: FontWeight.bold)),
                          Text('≈ ${_getEffectiveLpi(val)} LPI',
                              style: TextStyle(
                                  fontSize: 10, color: Colors.grey.shade600)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    DotSizePreview(multiplier: val, color: c),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}

class DotSizePreview extends StatelessWidget {
  final double multiplier;
  final Color color;

  const DotSizePreview(
      {super.key, required this.multiplier, required this.color});

  @override
  Widget build(BuildContext context) {
    // 1.0 = normal size
    double size = 20 * multiplier;
    return Container(
      width: 24,
      height: 24,
      decoration:
          BoxDecoration(border: Border.all(color: Colors.grey.shade300)),
      child: Center(
        child: Container(
          width: size.clamp(2.0, 24.0),
          height: size.clamp(2.0, 24.0),
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
      ),
    );
  }
}

class LayerDotSizeConfig {
  final int layerIndex;
  final double multiplier;
  LayerDotSizeConfig({required this.layerIndex, required this.multiplier});
}
