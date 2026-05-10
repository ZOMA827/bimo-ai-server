// lib/senses/physical_awareness.dart
// 📱 الجهاز العصبي لبيمو: يشعر بالهز (Dizzy) والقلب على الوجه (Sleep)

import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:sensors_plus/sensors_plus.dart';

class PhysicalAwareness {
  StreamSubscription? _accelSub;
  Function()? onShake;
  Function()? onFaceDown;

  bool _isFaceDown = false;
  Timer? _faceDownTimer;
  DateTime _lastShake = DateTime.now();

  void initialize({
    required Function() onShake,
    required Function() onFaceDown,
  }) {
    this.onShake = onShake;
    this.onFaceDown = onFaceDown;

    _accelSub = accelerometerEventStream().listen((AccelerometerEvent event) {
      final x = event.x;
      final y = event.y;
      final z = event.z;

      // 1. اكتشاف الهز (Shake Detection) 🌀
      // نحسب قوة التسارع (G-Force). الجاذبية الطبيعية هي 1G (حوالي 9.8).
      final gX = x / 9.81;
      final gY = y / 9.81;
      final gZ = z / 9.81;
      final gForce = sqrt(gX * gX + gY * gY + gZ * gZ);

      // إذا تجاوزت القوة 2.5G (يعني هزة قوية ومفاجئة)
      if (gForce > 2.5) {
        final now = DateTime.now();
        // نضع فاصل ثانيتين بين الهزات حتى لا يُصاب بالجنون
        if (now.difference(_lastShake).inMilliseconds > 2000) {
          _lastShake = now;
          this.onShake?.call();
        }
      }

      // 2. اكتشاف النوم (Face Down Detection) 📴
      // عندما يكون الهاتف مقلوباً على الطاولة، تكون الجاذبية تضغط على الشاشة (z تقترب من -9.8)
      if (z < -8.5 && x.abs() < 3.0 && y.abs() < 3.0) {
        if (!_isFaceDown) {
          _isFaceDown = true;
          // ⏳ ننتظر ثانيتين للتأكد أنه مقلوب عمداً وليس مجرد حركة عابرة باليد
          _faceDownTimer?.cancel();
          _faceDownTimer = Timer(const Duration(seconds: 2), () {
            if (_isFaceDown) {
              this.onFaceDown?.call();
            }
          });
        }
      } else {
        _isFaceDown = false;
        _faceDownTimer?.cancel();
      }
    });

    debugPrint('📱 الجهاز العصبي (المستشعرات) جاهز.');
  }

  void dispose() {
    _accelSub?.cancel();
    _faceDownTimer?.cancel();
  }
}
