// lib/ui/hologram_layer.dart
// ✨ نظام الجزيئات المطوّر: حلقات طاقة + نجوم متطايرة + ألوان تتغير بالمزاج

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
  late List<_Particle> _particles;
  late List<_StarParticle> _stars;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    // جزيئات الضوء المتصاعدة (25 جسيم)
    _particles = List.generate(25, (_) => _Particle(_rng));

    // نجوم متطايرة (12 نجمة للمزاج المتحمس)
    _stars = List.generate(12, (_) => _StarParticle(_rng));
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
      builder: (context, _) {
        for (var p in _particles) {
          p.update();
        }
        for (var s in _stars) {
          s.update();
        }
        return CustomPaint(
          size: Size.infinite,
          painter: _HologramPainter(
            color: widget.color,
            rotation: _ctrl.value * 2 * pi,
            secondRotation: -_ctrl.value * 2 * pi * 0.7,
            particles: _particles,
            stars: _stars,
            pulse: (_ctrl.value * 2 * pi).sin.abs(),
          ),
        );
      },
    );
  }
}

// ─── جسيم ضوئي متصاعد ───────────────────────────────
class _Particle {
  double x, y, speed, size, opacity;
  double drift; // انجراف أفقي خفيف

  _Particle(Random rng)
    : x = rng.nextDouble() * 300 - 150,
      y = rng.nextDouble() * 600 - 300,
      speed = rng.nextDouble() * 1.5 + 0.5,
      size = rng.nextDouble() * 2.5 + 0.5,
      opacity = rng.nextDouble() * 0.4 + 0.05,
      drift = (rng.nextDouble() - 0.5) * 0.4;

  void update() {
    y -= speed;
    x += drift;
    // إعادة من الأسفل
    if (y < -350) {
      y = 350;
      x = Random().nextDouble() * 300 - 150;
    }
  }
}

// ─── نجمة متطايرة (تظهر مع المزاج المتحمس) ──────────
class _StarParticle {
  double x, y, vx, vy, life, maxLife, size;

  _StarParticle(Random rng)
    : x = 0,
      y = 0,
      vx = (rng.nextDouble() - 0.5) * 4,
      vy = -(rng.nextDouble() * 3 + 1),
      life = rng.nextDouble(),
      maxLife = rng.nextDouble() * 60 + 30,
      size = rng.nextDouble() * 3 + 1;

  void update() {
    x += vx;
    y += vy;
    life++;
    vy += 0.05; // جاذبية خفيفة
    if (life >= maxLife) {
      // إعادة التوليد
      final rng = Random();
      x = (rng.nextDouble() - 0.5) * 60;
      y = (rng.nextDouble() - 0.5) * 60;
      vx = (rng.nextDouble() - 0.5) * 4;
      vy = -(rng.nextDouble() * 3 + 1);
      life = 0;
      maxLife = rng.nextDouble() * 60 + 30;
      size = rng.nextDouble() * 3 + 1;
    }
  }

  double get opacity => (1 - life / maxLife).clamp(0.0, 0.6);
}

// ─── الرسام الرئيسي ──────────────────────────────────
class _HologramPainter extends CustomPainter {
  final Color color;
  final double rotation;
  final double secondRotation;
  final List<_Particle> particles;
  final List<_StarParticle> stars;
  final double pulse; // 0.0 → 1.0

  _HologramPainter({
    required this.color,
    required this.rotation,
    required this.secondRotation,
    required this.particles,
    required this.stars,
    required this.pulse,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    // ─── 1. حلقة الرادار الدوارة (Ring 1 — متقطعة) ───────
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(rotation);
    _drawDashedCircle(canvas, 145, color.withOpacity(0.18), dashCount: 16);
    canvas.restore();

    // ─── 2. حلقة عكسية أبطأ (Ring 2 — نقاط) ─────────────
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(secondRotation);
    _drawDottedCircle(canvas, 175, color.withOpacity(0.10), dotCount: 24);
    canvas.restore();

    // ─── 3. حلقة نبض (Pulse Ring) ─────────────────────────
    final pulseRadius = 120 + pulse * 30;
    final pulsePaint = Paint()
      ..color = color.withOpacity(0.06 + pulse * 0.06)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5 + pulse * 2;
    canvas.drawCircle(center, pulseRadius, pulsePaint);

    // ─── 4. جزيئات الضوء المتطايرة ────────────────────────
    final particlePaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5);
    for (var p in particles) {
      particlePaint.color = color.withOpacity(p.opacity);
      canvas.drawCircle(
        Offset(center.dx + p.x, center.dy + p.y),
        p.size,
        particlePaint,
      );
    }

    // ─── 5. نجوم متطايرة من المركز ────────────────────────
    final starPaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.5);
    for (var s in stars) {
      starPaint.color = color.withOpacity(s.opacity);
      canvas.drawCircle(
        Offset(center.dx + s.x, center.dy + s.y),
        s.size,
        starPaint,
      );
    }

    // ─── 6. توهج المركز الخفيف ────────────────────────────
    final centerGlow = Paint()
      ..shader = RadialGradient(
        colors: [color.withOpacity(0.12 + pulse * 0.05), Colors.transparent],
      ).createShader(Rect.fromCircle(center: center, radius: 100));
    canvas.drawCircle(center, 100, centerGlow);
  }

  // حلقة متقطعة (شرطات)
  void _drawDashedCircle(
    Canvas canvas,
    double radius,
    Color c, {
    int dashCount = 20,
  }) {
    final paint = Paint()
      ..color = c
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8
      ..strokeCap = StrokeCap.round;

    final double totalAngle = 2 * pi;
    final double dashAngle = totalAngle / dashCount * 0.55;
    final double gapAngle = totalAngle / dashCount * 0.45;
    double angle = 0;

    while (angle < totalAngle) {
      canvas.drawArc(
        Rect.fromCircle(center: Offset.zero, radius: radius),
        angle,
        dashAngle,
        false,
        paint,
      );
      angle += dashAngle + gapAngle;
    }
  }

  // حلقة منقطة (دوائر صغيرة)
  void _drawDottedCircle(
    Canvas canvas,
    double radius,
    Color c, {
    int dotCount = 20,
  }) {
    final paint = Paint()
      ..color = c
      ..style = PaintingStyle.fill
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1);

    for (int i = 0; i < dotCount; i++) {
      final angle = (2 * pi / dotCount) * i;
      final dx = cos(angle) * radius;
      final dy = sin(angle) * radius;
      canvas.drawCircle(Offset(dx, dy), 2, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _HologramPainter old) =>
      old.rotation != rotation || old.pulse != pulse;
}

// ─── امتداد مفيد لحساب sin ────────────────────────────
extension _DoubleExt on double {
  double get sin => Sin(this);
  static double Sin(double x) => (x).abs() < 1e-10 ? 0 : _sin(x);
  static double _sin(double x) {
    // تقريب سريع
    return (2 * x / (2 * pi) - (2 * x / (2 * pi)).floor() - 0.5).abs() * 2 - 1;
  }
}
