// lib/presentation/splash/splash_screen.dart

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  // ── Colors ──────────────────────────────────────────────
  static const Color primaryBlue = Color(0xFF1564A5);
  static const Color darkBlue = Color(0xFF0E3182);
  static const Color accentBlue = Color(0xFF2196F3);
  static const Color bgColor = Color(0xFF0A1628);

  // ── Animation Controllers ────────────────────────────────
  late AnimationController _logoController;
  late AnimationController _textController;
  late AnimationController _progressController;
  late AnimationController _pulseController;

  // ── Animations ───────────────────────────────────────────
  late Animation<double> _logoScale;
  late Animation<double> _logoOpacity;
  late Animation<Offset> _logoSlide;
  late Animation<double> _textOpacity;
  late Animation<Offset> _textSlide;
  late Animation<double> _progressValue;
  late Animation<double> _pulseScale;
  late Animation<double> _devOpacity;

  // ── Loading text ─────────────────────────────────────────
  final RxString _loadingText = 'Initializing...'.obs;
  final List<String> _loadingSteps = [
    'Initializing...',
    'Loading processing engine...',
    'Preparing color separation...',
    'Loading registration system...',
    'Almost ready...',
  ];

  @override
  void initState() {
    super.initState();
    _setupAnimations();
    _startSequence();
  }

  void _setupAnimations() {
    // Logo animation (scale + fade + slide)
    _logoController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );

    _logoScale = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _logoController, curve: Curves.elasticOut),
    );
    _logoOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _logoController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeIn),
      ),
    );
    _logoSlide = Tween<Offset>(begin: const Offset(0, -0.3), end: Offset.zero)
        .animate(
          CurvedAnimation(parent: _logoController, curve: Curves.easeOutBack),
        );

    // Text animation
    _textController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _textOpacity = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _textController, curve: Curves.easeIn));
    _textSlide = Tween<Offset>(begin: const Offset(0, 0.2), end: Offset.zero)
        .animate(
          CurvedAnimation(parent: _textController, curve: Curves.easeOutCubic),
        );

    // Progress animation
    _progressController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    );
    _progressValue = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _progressController, curve: Curves.easeInOut),
    );

    // Pulse animation for logo glow
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _pulseScale = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Dev text opacity (fade in late)
    _devOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _textController,
        curve: const Interval(0.5, 1.0, curve: Curves.easeIn),
      ),
    );
  }

  void _startSequence() async {
    // Step 1: Logo appears
    await Future.delayed(const Duration(milliseconds: 200));
    _logoController.forward();

    // Step 2: Text appears
    await Future.delayed(const Duration(milliseconds: 700));
    _textController.forward();

    // Step 3: Progress starts
    await Future.delayed(const Duration(milliseconds: 400));
    _progressController.forward();

    // Step 4: Cycle loading messages
    for (int i = 0; i < _loadingSteps.length; i++) {
      await Future.delayed(const Duration(milliseconds: 550));
      if (mounted) _loadingText.value = _loadingSteps[i];
    }

    // Step 5: Navigate to dashboard
    await Future.delayed(const Duration(milliseconds: 600));
    if (mounted) {
      Get.offAllNamed('/dashboard');
    }
  }

  @override
  void dispose() {
    _logoController.dispose();
    _textController.dispose();
    _progressController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: Stack(
        children: [
          // ── Background gradient ──────────────────────────
          _buildBackground(),

          // ── Decorative circles ───────────────────────────
          _buildDecorativeCircles(),

          // ── Main content ─────────────────────────────────
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo
                _buildLogo(),
                const SizedBox(height: 40),

                // App name
                _buildAppName(),
                const SizedBox(height: 12),

                // Tagline
                _buildTagline(),
                const SizedBox(height: 60),

                // Progress bar
                _buildProgressBar(),
                const SizedBox(height: 16),

                // Loading text
                _buildLoadingText(),
              ],
            ),
          ),

          // ── Developer credit (bottom) ────────────────────
          _buildDeveloperCredit(),
        ],
      ),
    );
  }

  // ── Background ───────────────────────────────────────────
  Widget _buildBackground() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0A1628), Color(0xFF0E1F3D), Color(0xFF0A1628)],
          stops: [0.0, 0.5, 1.0],
        ),
      ),
    );
  }

  // ── Decorative Circles ───────────────────────────────────
  Widget _buildDecorativeCircles() {
    return Stack(
      children: [
        // Top-right circle
        Positioned(
          top: -80,
          right: -80,
          child: AnimatedBuilder(
            animation: _pulseController,
            builder: (_, __) => Transform.scale(
              scale: _pulseScale.value,
              child: Container(
                width: 300,
                height: 300,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      primaryBlue.withValues(alpha: 0.15),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
        // Bottom-left circle
        Positioned(
          bottom: -100,
          left: -100,
          child: Container(
            width: 350,
            height: 350,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [darkBlue.withValues(alpha: 0.2), Colors.transparent],
              ),
            ),
          ),
        ),
        // Center glow
        Center(
          child: AnimatedBuilder(
            animation: _pulseController,
            builder: (_, __) => Container(
              width: 200 * _pulseScale.value,
              height: 200 * _pulseScale.value,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    accentBlue.withValues(alpha: 0.05),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  // ── Logo ─────────────────────────────────────────────────
  Widget _buildLogo() {
    return AnimatedBuilder(
      animation: _logoController,
      builder: (_, __) => FadeTransition(
        opacity: _logoOpacity,
        child: SlideTransition(
          position: _logoSlide,
          child: ScaleTransition(
            scale: _logoScale,
            child: AnimatedBuilder(
              animation: _pulseController,
              builder: (_, __) => Transform.scale(
                scale: _pulseScale.value,
                child: Container(
                  width: 130,
                  height: 130,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [primaryBlue, darkBlue],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: primaryBlue.withValues(alpha: 0.5),
                        blurRadius: 30,
                        spreadRadius: 5,
                      ),
                      BoxShadow(
                        color: accentBlue.withValues(alpha: 0.2),
                        blurRadius: 60,
                        spreadRadius: 10,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.print_rounded,
                    color: Colors.white,
                    size: 65,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ── App Name ─────────────────────────────────────────────
  Widget _buildAppName() {
    return AnimatedBuilder(
      animation: _textController,
      builder: (_, __) => FadeTransition(
        opacity: _textOpacity,
        child: SlideTransition(
          position: _textSlide,
          child: Column(
            children: [
              // Main title
              ShaderMask(
                shaderCallback: (bounds) => const LinearGradient(
                  colors: [Colors.white, Color(0xFF90CAF9)],
                ).createShader(bounds),
                child: const Text(
                  'Virtual Design',
                  style: TextStyle(
                    fontSize: 38,
                    fontWeight: FontWeight.w900,
                    color: Colors.white,
                    letterSpacing: 1.5,
                  ),
                ),
              ),
              const SizedBox(height: 6),
              // Subtitle
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: primaryBlue.withValues(alpha: 0.6),
                    width: 1,
                  ),
                  borderRadius: BorderRadius.circular(20),
                  color: primaryBlue.withValues(alpha: 0.1),
                ),
                child: const Text(
                  'SILK SCREEN STUDIO',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF90CAF9),
                    letterSpacing: 4,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Tagline ──────────────────────────────────────────────
  Widget _buildTagline() {
    return AnimatedBuilder(
      animation: _textController,
      builder: (_, __) => FadeTransition(
        opacity: _textOpacity,
        child: const Text(
          'Professional Color Separation for Screen Printing',
          style: TextStyle(
            fontSize: 14,
            color: Color(0xFF78909C),
            fontWeight: FontWeight.w400,
            letterSpacing: 0.5,
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  // ── Progress Bar ─────────────────────────────────────────
  Widget _buildProgressBar() {
    return SizedBox(
      width: 280,
      child: AnimatedBuilder(
        animation: _progressController,
        builder: (_, __) => Column(
          children: [
            // Track
            Container(
              height: 4,
              width: 280,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(2),
              ),
              child: FractionallySizedBox(
                alignment: Alignment.centerLeft,
                widthFactor: _progressValue.value,
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(2),
                    gradient: const LinearGradient(
                      colors: [accentBlue, primaryBlue],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: accentBlue.withValues(alpha: 0.5),
                        blurRadius: 8,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Loading Text ─────────────────────────────────────────
  Widget _buildLoadingText() {
    return Obx(
      () => AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        child: Text(
          _loadingText.value,
          key: ValueKey(_loadingText.value),
          style: const TextStyle(
            fontSize: 13,
            color: Color(0xFF546E7A),
            fontWeight: FontWeight.w400,
          ),
        ),
      ),
    );
  }

  // ── Developer Credit ─────────────────────────────────────
  Widget _buildDeveloperCredit() {
    return Positioned(
      bottom: 40,
      left: 0,
      right: 0,
      child: AnimatedBuilder(
        animation: _textController,
        builder: (_, __) => FadeTransition(
          opacity: _devOpacity,
          child: Column(
            children: [
              // Divider line
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 40,
                    height: 1,
                    color: Colors.white.withValues(alpha: 0.1),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'Developed by',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withValues(alpha: 0.3),
                      letterSpacing: 1,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Container(
                    width: 40,
                    height: 1,
                    color: Colors.white.withValues(alpha: 0.1),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // MO2 Logo
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // MO2 Badge
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          primaryBlue.withValues(alpha: 0.3),
                          darkBlue.withValues(alpha: 0.3),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: primaryBlue.withValues(alpha: 0.4),
                        width: 1,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // MO2 Icon
                        Container(
                          width: 24,
                          height: 24,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              colors: [accentBlue, primaryBlue],
                            ),
                          ),
                          child: const Center(
                            child: Text(
                              'M',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        // MO2 Text
                        RichText(
                          text: TextSpan(
                            children: [
                              const TextSpan(
                                text: 'MO',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 1,
                                ),
                              ),
                              TextSpan(
                                text: '2',
                                style: TextStyle(
                                  color: accentBlue,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w900,
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
              const SizedBox(height: 8),

              // Version
              Text(
                'Version 1.0.0',
                style: TextStyle(
                  fontSize: 10,
                  color: Colors.white.withValues(alpha: 0.2),
                  letterSpacing: 1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
