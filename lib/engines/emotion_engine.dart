// lib/engines/emotion_engine.dart
// بيمو يتحكم بمشاعره بنفسه — مثل إيمو الحقيقي

import 'dart:async';
import 'dart:math';
import '../main.dart';

enum FaceAction {
  none,
  wink,
  lookAway,
  shakeNo,
  nodYes,
  zoomIn,
  spin,
  cry,
  laugh,
}

class EmotionEngine {
  BimoState _currentState = BimoState.sleeping;
  bool isAwake = false;

  Timer? _moodTimer;
  Timer? _blinkTimer;
  Timer? _randomExpressionTimer;
  Timer? _faceActionTimer;

  FaceAction _currentFaceAction = FaceAction.none;
  bool _winkLeft = false;

  // عدد ردود متتالية بدون ذكر الاسم — لتجنب التكرار
  int _replyCount = 0;

  Function()? onBlink;

  BimoState get currentState => _currentState;
  FaceAction get currentFaceAction => _currentFaceAction;
  bool get winkLeft => _winkLeft;
  int get replyCount => _replyCount;

  // ─────────────────────────────────────────
  // رمش تلقائي
  // ─────────────────────────────────────────
  void startAutoBlink(Function() blinkCallback) {
    onBlink = blinkCallback;
    _scheduleBlink();
  }

  void _scheduleBlink() {
    _blinkTimer?.cancel();
    // رمش عشوائي بين 2-4 ثانية
    final delay = Duration(milliseconds: 2000 + Random().nextInt(2000));
    _blinkTimer = Timer(delay, () {
      // لا ترمش أثناء الغمز
      if (_currentFaceAction != FaceAction.wink) {
        onBlink?.call();
      }
      _scheduleBlink();
    });
  }

  // ─────────────────────────────────────────
  // أفعال الوجه
  // ─────────────────────────────────────────
  void executeFaceAction(String? actionStr, Function() updateCallback) {
    final action = _parseFaceAction(actionStr);
    if (action == FaceAction.none) return;

    _currentFaceAction = action;
    updateCallback();

    if (action == FaceAction.wink) {
      _winkLeft = Random().nextBool();
    }

    _faceActionTimer?.cancel();
    _faceActionTimer = Timer(_getActionDuration(action), () {
      _currentFaceAction = FaceAction.none;
      updateCallback();
    });
  }

  FaceAction _parseFaceAction(String? str) {
    switch (str) {
      case 'wink':
        return FaceAction.wink;
      case 'look_away':
        return FaceAction.lookAway;
      case 'shake_no':
        return FaceAction.shakeNo;
      case 'nod_yes':
        return FaceAction.nodYes;
      case 'zoom_in':
        return FaceAction.zoomIn;
      case 'spin':
        return FaceAction.spin;
      case 'cry':
        return FaceAction.cry;
      case 'laugh':
        return FaceAction.laugh;
      default:
        return FaceAction.none;
    }
  }

  Duration _getActionDuration(FaceAction action) {
    switch (action) {
      case FaceAction.wink:
        return const Duration(milliseconds: 400);
      case FaceAction.lookAway:
        return const Duration(milliseconds: 1500);
      case FaceAction.shakeNo:
        return const Duration(milliseconds: 800);
      case FaceAction.nodYes:
        return const Duration(milliseconds: 600);
      case FaceAction.zoomIn:
        return const Duration(milliseconds: 500);
      case FaceAction.spin:
        return const Duration(milliseconds: 700);
      case FaceAction.cry:
        return const Duration(seconds: 3);
      case FaceAction.laugh:
        return const Duration(milliseconds: 1200);
      default:
        return Duration.zero;
    }
  }

  // ─────────────────────────────────────────
  // تحويل نص المشاعر لـ BimoState
  // ─────────────────────────────────────────
  BimoState mapEmotion(String? aiEmotion) {
    switch (aiEmotion?.toLowerCase()) {
      case 'happy':
        return BimoState.happy;
      case 'angry':
        return BimoState.angry;
      case 'sad':
        return BimoState.sad;
      case 'dizzy':
        return BimoState.dizzy;
      case 'bored':
        return BimoState.bored;
      case 'surprised':
        return BimoState.surprised;
      case 'thinking':
        return BimoState.thinking;
      case 'excited':
        return BimoState.excited;
      case 'shy':
        return BimoState.shy;
      case 'proud':
        return BimoState.proud;
      default:
        return BimoState.idle;
    }
  }

  // ─────────────────────────────────────────
  // تحديث المزاج مع مدة تلقائية
  // ─────────────────────────────────────────
  void updateMood(BimoState newState, Function() onUpdate) {
    if (_currentState == newState) return;
    _currentState = newState;
    _replyCount++;
    onUpdate();

    _moodTimer?.cancel();
    final duration = _getMoodDuration(newState);
    if (duration != null) {
      _moodTimer = Timer(duration, () {
        _currentState = isAwake ? BimoState.idle : BimoState.sleeping;
        onUpdate();
      });
    }
  }

  Duration? _getMoodDuration(BimoState state) {
    switch (state) {
      case BimoState.sleeping:
      case BimoState.listening:
      case BimoState.idle:
        return null;
      case BimoState.happy:
        return const Duration(seconds: 8);
      case BimoState.angry:
        return const Duration(seconds: 5);
      case BimoState.sad:
        return const Duration(seconds: 10);
      case BimoState.surprised:
        return const Duration(seconds: 3);
      case BimoState.thinking:
        return const Duration(seconds: 6);
      case BimoState.dizzy:
        return const Duration(seconds: 4);
      case BimoState.bored:
        return const Duration(seconds: 12);
      case BimoState.excited:
        return const Duration(seconds: 6);
      case BimoState.shy:
        return const Duration(seconds: 5);
      case BimoState.proud:
        return const Duration(seconds: 7);
    }
  }

  // ─────────────────────────────────────────
  // تعبيرات عشوائية ذكية
  // ─────────────────────────────────────────
  void startRandomExpressions(Function() onUpdate) {
    _randomExpressionTimer?.cancel();
    _randomExpressionTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      if (_currentState != BimoState.idle || !isAwake) return;
      final r = Random();
      if (r.nextDouble() < 0.35) {
        // مشاعر عشوائية مناسبة للـ idle
        final states = [
          BimoState.happy,
          BimoState.bored,
          BimoState.surprised,
          BimoState.excited,
          BimoState.shy,
        ];
        updateMood(states[r.nextInt(states.length)], onUpdate);

        // أحياناً فعل وجه مع المشاعر
        if (r.nextDouble() < 0.4) {
          final actions = ['wink', 'look_away', 'nod_yes', 'spin'];
          executeFaceAction(actions[r.nextInt(actions.length)], onUpdate);
        }
      }
    });
  }

  void dispose() {
    _moodTimer?.cancel();
    _blinkTimer?.cancel();
    _randomExpressionTimer?.cancel();
    _faceActionTimer?.cancel();
  }
}
