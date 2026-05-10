// lib/senses/wake_word_engine.dart
// 🎙️ الأذن للاستيقاظ (نسخة محسنة ومستقرة تماماً)

import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class WakeWordEngine {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isInitialized = false;
  bool _isActive = false;
  Function()? onWakeWordDetected;

  Future<bool> initialize(Function() onWake) async {
    onWakeWordDetected = onWake;
    try {
      _isInitialized = await _speech.initialize(
        onError: (e) {
          final msg = e.errorMsg;
          // 🔥 إخفاء أخطاء الصمت الطبيعية حتى لا تظن أن هناك مشكلة
          if (msg != 'error_speech_timeout' && msg != 'error_no_match') {
            debugPrint('❌ خطأ في الأذن: $msg');
          }
        },
        onStatus: (status) {
          // إعادة التشغيل بهدوء في حالة الصمت
          if (status == 'notListening' && _isInitialized && _isActive) {
            // 🔥 التعديل السحري 3: تأخير 1.5 ثانية (بدل 0.5) لكسر حلقة التضارب
            Future.delayed(const Duration(milliseconds: 1500), () {
              if (_isActive) startListening();
            });
          }
        },
      );
      debugPrint('✅ الأذن جاهزة: $_isInitialized');
      return _isInitialized;
    } catch (e) {
      debugPrint('❌ فشل تهيئة الأذن: $e');
      return false;
    }
  }

  void startListening() async {
    if (!_isInitialized) return;
    _isActive = true;

    if (_speech.isListening) return;

    debugPrint('💤 بيمو نائم... الأذن تستمع لكلمة السر.');
    await _speech.listen(
      onResult: (result) {
        final text = result.recognizedWords.toLowerCase();
        if (text.contains('بيمو') ||
            text.contains('ديمو') ||
            text.contains('bimo') ||
            text.contains('فيمو')) {
          stopListening();
          onWakeWordDetected?.call();
        }
      },
      localeId: 'ar-SA',
      listenMode: stt.ListenMode.dictation,
      pauseFor: const Duration(
        seconds: 30,
      ), // 🔥 الاستماع لمدة 30 ثانية قبل التوقف المؤقت
    );
  }

  void stopListening() async {
    _isActive = false;
    if (_speech.isListening) {
      await _speech.stop();
      debugPrint('☀️ تم إيقاف الأذن المحلية (بيمو مستيقظ).');
    }
  }

  void dispose() {
    _isInitialized = false;
    _isActive = false;
    _speech.stop();
  }
}
