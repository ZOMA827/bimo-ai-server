// lib/ui/animations.dart
// ✅ لا تغيير جوهري — فقط إضافة تأثير نبض للـ listening

import 'package:flutter/material.dart';

class BimoAnimations {
  // أنيميشن التنفس (Breathing)
  static Animation<double> createBreathing(TickerProvider vsync) {
    final controller = AnimationController(
      vsync: vsync,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    return Tween<double>(
      begin: 1.0,
      end: 1.03,
    ).animate(CurvedAnimation(parent: controller, curve: Curves.easeInOut));
  }

  // ✅ أنيميشن نبض أسرع للـ listening
  static Animation<double> createPulse(TickerProvider vsync) {
    final controller = AnimationController(
      vsync: vsync,
      duration: const Duration(milliseconds: 600),
    )..repeat(reverse: true);

    return Tween<double>(
      begin: 1.0,
      end: 1.06,
    ).animate(CurvedAnimation(parent: controller, curve: Curves.easeInOut));
  }

  // مصفوفة التحويل للحركة
  static Matrix4 getFaceTransform(Offset offset, double rotation) {
    return Matrix4.identity()
      ..translate(offset.dx, offset.dy)
      ..rotateZ(rotation);
  }
}
