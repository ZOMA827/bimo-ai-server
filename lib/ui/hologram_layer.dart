// lib/ui/hologram_layer.dart
// ✨ نظام الجزيئات وحلقات الهولوغرام (VFX)

import 'dart:math';
import 'package:flutter/material.dart';

class HologramLayer extends StatefulWidget {
  final Color color;
  final bool isActive;

  const HologramLayer({super.key, required this.color, required this.isActive});

  @override
  State<HologramLayer> createState() => _HologramLayerState();
}

class _HologramLayerState extends State<HologramLayer>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  final Random _rng = Random();
  final List<_Particle> _particles = [];

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();
    // إنشاء 25 جزيء ضوئي
    for (int i = 0; i < 25; i++) {
      _particles.add(_Particle(_rng));
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isActive) return const SizedBox.shrink();

    return AnimatedBuilder(
      animation: _ctrl,
      builder: (context, child) {
        for (var p in _particles) {
          p.update();
        }
        return CustomPaint(
          size: Size.infinite,
          painter: _HologramPainter(
            color: widget.color,
            rotation: _ctrl.value * 2 * pi,
            particles: _particles,
          ),
        );
      },
    );
  }
}

class _Particle {
  double x, y, speed, size, opacity;
  _Particle(Random rng)
    : x = rng.nextDouble() * 400 - 200,
      y = rng.nextDouble() * 800 - 400,
      speed = rng.nextDouble() * 2 + 1,
      size = rng.nextDouble() * 3 + 1,
      opacity = rng.nextDouble() * 0.5 + 0.1;

  void update() {
    y -= speed;
    if (y < -400) y = 400; // إعادة التدوير من الأسفل
  }
}

class _HologramPainter extends CustomPainter {
  final Color color;
  final double rotation;
  final List<_Particle> particles;

  _HologramPainter({
    required this.color,
    required this.rotation,
    required this.particles,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    // 1. رسم حلقات الرادار (Radar Rings)
    final ringPaint = Paint()
      ..color = color.withOpacity(0.15)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(rotation);

    // حلقة متقطعة
    const dashWidth = 15.0;
    const dashSpace = 10.0;
    double startAngle = 0.0;
    while (startAngle < 2 * pi) {
      canvas.drawArc(
        Rect.fromCircle(center: Offset.zero, radius: 140),
        startAngle,
        dashWidth / 140,
        false,
        ringPaint,
      );
      startAngle += (dashWidth + dashSpace) / 140;
    }
    canvas.restore();

    // حلقة ثابتة واسعة
    canvas.drawCircle(center, 180, ringPaint..color = color.withOpacity(0.05));

    // 2. رسم الجزيئات المتطايرة (Particles)
    final particlePaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
    for (var p in particles) {
      particlePaint.color = color.withOpacity(p.opacity);
      canvas.drawCircle(
        Offset(center.dx + p.x, center.dy + p.y),
        p.size,
        particlePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
