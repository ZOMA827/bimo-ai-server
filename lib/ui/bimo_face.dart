// lib/ui/bimo_face.dart
// ✅ وجه بيمو برو: حالات جديدة + غمز + ضحك + خجل + فخر + تعابير غنية

import 'package:flutter/material.dart';
import '../main.dart';

class BimoFacePainter {
  static Widget buildEye(
    BimoState state,
    bool isBlinking,
    Offset lookTarget, {
    bool winkLeft = false,
    bool winkRight = false,
    bool isLaughing = false,
  }) {
    double width = 80;
    double height = 100;
    Color eyeColor = Colors.cyanAccent;
    BorderRadius borderRadius = BorderRadius.circular(15);
    double pupilSize = 16;
    double glowRadius = 20;

    switch (state) {
      case BimoState.happy:
        height = 45;
        width = 75;
        eyeColor = Colors.greenAccent;
        glowRadius = 30;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(50),
          topRight: Radius.circular(50),
          bottomLeft: Radius.circular(5),
          bottomRight: Radius.circular(5),
        );
        break;

      case BimoState.excited:
        height = 50;
        width = 85;
        eyeColor = Colors.limeAccent;
        glowRadius = 35;
        borderRadius = BorderRadius.circular(30);
        pupilSize = 18;
        break;

      case BimoState.angry:
        height = 38;
        width = 90;
        eyeColor = Colors.redAccent;
        glowRadius = 25;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(5),
          topRight: Radius.circular(40),
          bottomLeft: Radius.circular(5),
          bottomRight: Radius.circular(5),
        );
        break;

      case BimoState.sad:
        height = 50;
        width = 70;
        eyeColor = Colors.lightBlueAccent;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(40),
          topRight: Radius.circular(40),
          bottomLeft: Radius.circular(10),
          bottomRight: Radius.circular(10),
        );
        break;

      case BimoState.shy:
        height = 30;
        width = 75;
        eyeColor = Colors.pinkAccent;
        glowRadius = 15;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(40),
          topRight: Radius.circular(40),
          bottomLeft: Radius.circular(5),
          bottomRight: Radius.circular(5),
        );
        pupilSize = 12;
        break;

      case BimoState.proud:
        height = 40;
        width = 90;
        eyeColor = Colors.amberAccent;
        glowRadius = 28;
        borderRadius = BorderRadius.circular(10);
        pupilSize = 18;
        break;

      case BimoState.sleeping:
        height = 8;
        width = 80;
        eyeColor = Colors.grey.shade600;
        glowRadius = 5;
        borderRadius = BorderRadius.circular(10);
        pupilSize = 0;
        break;

      case BimoState.listening:
        width = 95;
        height = 115;
        eyeColor = Colors.yellowAccent;
        glowRadius = 35;
        borderRadius = BorderRadius.circular(40);
        pupilSize = 20;
        break;

      case BimoState.surprised:
        width = 100;
        height = 100;
        eyeColor = Colors.white;
        glowRadius = 40;
        borderRadius = BorderRadius.circular(50);
        pupilSize = 22;
        break;

      case BimoState.thinking:
        height = 55;
        width = 75;
        eyeColor = Colors.purpleAccent;
        glowRadius = 20;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(10),
          topRight: Radius.circular(10),
          bottomLeft: Radius.circular(40),
          bottomRight: Radius.circular(40),
        );
        break;

      case BimoState.dizzy:
        height = 80;
        width = 80;
        eyeColor = Colors.orangeAccent;
        glowRadius = 20;
        borderRadius = BorderRadius.circular(15);
        break;

      case BimoState.bored:
        height = 35;
        width = 85;
        eyeColor = Colors.grey.shade400;
        glowRadius = 10;
        borderRadius = BorderRadius.circular(5);
        break;

      default:
        break;
    }

    // ✅ ضحك: عيون نصف مغلقة بشكل مختلف
    if (isLaughing) {
      height = height * 0.4;
      borderRadius = const BorderRadius.only(
        topLeft: Radius.circular(40),
        topRight: Radius.circular(40),
        bottomLeft: Radius.circular(5),
        bottomRight: Radius.circular(5),
      );
    }

    final pupilOffset = state == BimoState.sleeping
        ? Offset.zero
        : Offset(
            lookTarget.dx.clamp(-15.0, 15.0) * 0.25,
            lookTarget.dy.clamp(-15.0, 15.0) * 0.25,
          );

    // ✅ غمز: سواء العين اليسرى أو اليمنى تُغلق
    final bool isWinking = winkLeft || winkRight;
    final double displayHeight = isWinking
        ? 3
        : (isBlinking && state != BimoState.sleeping ? 3 : height);

    return AnimatedContainer(
      duration: Duration(milliseconds: isWinking ? 80 : 250),
      curve: Curves.easeInOut,
      width: width,
      height: displayHeight,
      decoration: BoxDecoration(
        color: eyeColor,
        borderRadius: borderRadius,
        boxShadow: [
          BoxShadow(
            color: eyeColor.withOpacity(0.5),
            blurRadius: glowRadius,
            spreadRadius: glowRadius * 0.3,
          ),
        ],
      ),
      child: (!isWinking && pupilSize > 0)
          ? Center(
              child: AnimatedSlide(
                duration: const Duration(milliseconds: 150),
                offset: Offset(
                  pupilOffset.dx / (width > 0 ? width : 1),
                  pupilOffset.dy / (height > 0 ? height : 1),
                ),
                child: Container(
                  width: pupilSize,
                  height: pupilSize,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.white.withOpacity(0.6),
                        blurRadius: 8,
                      ),
                    ],
                  ),
                ),
              ),
            )
          : const SizedBox.shrink(),
    );
  }

  static Widget buildMouth(
    BimoState state, {
    bool isTalking = false,
    bool isLaughing = false,
  }) {
    double width = 60;
    double height = 6;
    Color mouthColor = Colors.cyanAccent.withOpacity(0.8);
    BorderRadius borderRadius = BorderRadius.circular(3);
    double glowRadius = 10;

    // ✅ ضحك: فم كبير مقوس للأسفل
    if (isLaughing) {
      return AnimatedContainer(
        duration: const Duration(milliseconds: 100),
        width: 65,
        height: 35,
        decoration: BoxDecoration(
          color: Colors.limeAccent,
          borderRadius: const BorderRadius.only(
            bottomLeft: Radius.circular(50),
            bottomRight: Radius.circular(50),
            topLeft: Radius.circular(5),
            topRight: Radius.circular(5),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.limeAccent.withOpacity(0.6),
              blurRadius: 25,
            ),
          ],
        ),
      );
    }

    // ✅ يتكلم: فم يفتح ويغلق
    if (isTalking) {
      return AnimatedContainer(
        duration: const Duration(milliseconds: 100),
        width: 48,
        height: 22,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.9),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(color: Colors.white.withOpacity(0.4), blurRadius: 15),
          ],
        ),
      );
    }

    switch (state) {
      case BimoState.happy:
      case BimoState.excited:
        width = 55;
        height = 30;
        mouthColor = Colors.greenAccent;
        glowRadius = 20;
        borderRadius = const BorderRadius.only(
          bottomLeft: Radius.circular(40),
          bottomRight: Radius.circular(40),
          topLeft: Radius.circular(5),
          topRight: Radius.circular(5),
        );
        break;

      case BimoState.proud:
        width = 50;
        height = 12;
        mouthColor = Colors.amberAccent;
        glowRadius = 18;
        borderRadius = BorderRadius.circular(8);
        break;

      case BimoState.shy:
        width = 30;
        height = 8;
        mouthColor = Colors.pinkAccent;
        glowRadius = 10;
        borderRadius = BorderRadius.circular(5);
        break;

      case BimoState.sad:
        width = 40;
        height = 18;
        mouthColor = Colors.lightBlueAccent;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(30),
          topRight: Radius.circular(30),
        );
        break;

      case BimoState.angry:
        width = 50;
        height = 8;
        mouthColor = Colors.redAccent;
        glowRadius = 15;
        borderRadius = BorderRadius.circular(4);
        break;

      case BimoState.listening:
        width = 45;
        height = 45;
        mouthColor = Colors.yellowAccent;
        glowRadius = 25;
        borderRadius = BorderRadius.circular(30);
        break;

      case BimoState.surprised:
        width = 35;
        height = 35;
        mouthColor = Colors.white.withOpacity(0.9);
        glowRadius = 20;
        borderRadius = BorderRadius.circular(20);
        break;

      case BimoState.thinking:
        width = 45;
        height = 6;
        mouthColor = Colors.purpleAccent;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(3),
          topRight: Radius.circular(10),
          bottomLeft: Radius.circular(10),
          bottomRight: Radius.circular(3),
        );
        break;

      case BimoState.sleeping:
        width = 50;
        height = 4;
        mouthColor = Colors.grey.shade600;
        glowRadius = 3;
        borderRadius = BorderRadius.circular(2);
        break;

      case BimoState.bored:
        width = 35;
        height = 5;
        mouthColor = Colors.grey.shade400;
        glowRadius = 5;
        borderRadius = BorderRadius.circular(3);
        break;

      default:
        break;
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: mouthColor,
        borderRadius: borderRadius,
        boxShadow: [
          BoxShadow(color: mouthColor.withOpacity(0.5), blurRadius: glowRadius),
        ],
      ),
    );
  }

  static Widget buildEyebrow(BimoState state, bool isLeft) {
    double rotation = 0;
    Color color = Colors.transparent;
    double width = 70;

    switch (state) {
      case BimoState.angry:
        rotation = isLeft ? 0.35 : -0.35;
        color = Colors.redAccent;
        break;
      case BimoState.thinking:
        rotation = isLeft ? 0.0 : -0.2;
        color = Colors.purpleAccent;
        break;
      case BimoState.proud:
        rotation = isLeft ? -0.1 : 0.1;
        color = Colors.amberAccent;
        width = 80;
        break;
      case BimoState.surprised:
        rotation = isLeft ? -0.2 : 0.2;
        color = Colors.white.withOpacity(0.8);
        break;
      default:
        return const SizedBox(height: 12);
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      margin: const EdgeInsets.only(bottom: 6),
      child: Transform.rotate(
        angle: rotation,
        child: Container(
          width: width,
          height: 6,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(3),
            boxShadow: [
              BoxShadow(color: color.withOpacity(0.5), blurRadius: 8),
            ],
          ),
        ),
      ),
    );
  }
}
