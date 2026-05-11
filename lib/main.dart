// lib/main.dart — بيمو برو النهائي
// ✅ صوت ذكر محسّن | كاميرا Lazy | مبادرات ذكية | متعدد اللغات | تفاعل فيزيائي | تفاعل صوتي (غناء وتصفيق)

import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:math';
import 'package:flutter_tts/flutter_tts.dart';
import 'core/api_service.dart';
import 'senses/vision_awareness.dart';
import 'senses/smart_mic.dart';
import 'engines/emotion_engine.dart';
import 'ui/bimo_face.dart';
import 'ui/animations.dart';
import 'senses/wake_word_engine.dart';
import 'senses/physical_awareness.dart';
import 'ui/hud_layer.dart'; // 🔥 أضف هذا
import 'ui/hologram_layer.dart'; // 🔥 أضف هذا

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const MaterialApp(debugShowCheckedModeBanner: false, home: BimoProFace()),
  );
}

enum BimoState {
  idle,
  happy,
  angry,
  sad,
  listening,
  dizzy,
  bored,
  sleeping,
  surprised,
  thinking,
  excited,
  shy,
  proud,
}

class BimoProFace extends StatefulWidget {
  const BimoProFace({super.key});
  @override
  State<BimoProFace> createState() => _BimoProFaceState();
}

class _BimoProFaceState extends State<BimoProFace>
    with TickerProviderStateMixin {
  final ApiService _api = ApiService();
  final VisionAwareness _vision = VisionAwareness();
  final SmartMic _mic = SmartMic();
  final EmotionEngine _emotion = EmotionEngine();
  final FlutterTts _tts = FlutterTts();
  final WakeWordEngine _wakeWord = WakeWordEngine();
  final PhysicalAwareness _physical = PhysicalAwareness();
  final Random _rng = Random();

  late Animation<double> _breathing;
  late Animation<double> _pulseAnim;

  // 🔥 متغيرات شاشة الهولوغرام العائمة
  String _hudAction = 'none';
  String _hudUrl = '';
  String _hudImageUrl = ''; // 🔥 أضف هذا
  String _hudTitle = '';

  Offset _faceOffset = Offset.zero;
  bool _isBlinking = false;
  bool _isBusy = false;
  bool _isMouthOpen = false;
  bool _aloneMode = false;

  Timer? _sleepTimer;
  Timer? _busyTimeout;
  Timer? _mouthTimer;
  Timer? _aloneTimer;
  Timer? _aloneRepeat;
  Timer? _spontaneousPoller;

  int _replysSinceNameUsed = 0;

  // ─── كلمات تشغل الكاميرا ───────────────────
  static const _visionKeywords = [
    'شوف',
    'انظر',
    'نظر',
    'هنا',
    'ما هذا',
    'ماذا ألبس',
    'ملابس',
    'قميص',
    'لون',
    'ابتسم',
    'رأيك',
    'هذا',
    'صورة',
    'اقرأ',
    'ما أمامك',
    'ما تراه',
    'ما لون',
    'كيف أبدو',
    'ما الذي',
    'انظر إليّ',
    'شايفني',
    'look',
    'see',
    'what is this',
    'what do you see',
    'what color',
    'read this',
    'describe',
  ];

  // ─────────────────────────────────────────
  void _setBusy(bool v, {Duration? autoRelease}) {
    _busyTimeout?.cancel();
    _isBusy = v;
    if (v && autoRelease != null) {
      _busyTimeout = Timer(autoRelease, _releaseBusy);
    }
    if (mounted) setState(() {});
  }

  void _releaseBusy() {
    _busyTimeout?.cancel();
    _isBusy = false;

    if (_emotion.isAwake) {
      _mic.resumeAfterSpeaking();
    }

    if (mounted) setState(() {});
  }

  // ─────────────────────────────────────────
  @override
  void initState() {
    super.initState();
    _breathing = BimoAnimations.createBreathing(this)
      ..addListener(() => setState(() {}));
    _pulseAnim = BimoAnimations.createPulse(this)
      ..addListener(() => setState(() {}));
    _initBimo();
  }

  void _initBimo() async {
    await _vision.initialize((face) {});
    await _setupTTS();

    final wakeWordOk = await _wakeWord.initialize(_wakeUp);

    // 🔥 تهيئة الميكروفون الذكي وإضافة ميزة الاستماع للتصفيق/الضجيج!
    await _mic.initialize(
      _handleSpeech,
      onLoudNoise: () {
        if (!_emotion.isAwake || _isBusy) return;
        debugPrint('👏 صوت ضجيج أو تصفيق!');
        _emotion.updateMood(BimoState.surprised, () => setState(() {}));
        _emotion.executeFaceAction('spin', () => setState(() {}));
      },
    );

    _physical.initialize(
      onShake: () {
        if (!_emotion.isAwake || _isBusy) return;
        debugPrint('🌀 الهاتف يهتز! بيمو يشعر بالدوار');
        _emotion.updateMood(BimoState.dizzy, () => setState(() {}));
        _emotion.executeFaceAction('spin', () => setState(() {}));
        _speak('آآآخ! راسي يدوور! توقف عن هزي يا بطل!');
      },
      onFaceDown: () {
        if (_emotion.isAwake) {
          debugPrint('📴 الهاتف مقلوب... بيمو يذهب للنوم لتوفير البطارية');
          _goToSleep();
        }
      },
    );

    if (wakeWordOk) {
      _wakeWord.startListening();
    }

    _emotion.startAutoBlink(() {
      if (!mounted) return;
      setState(() => _isBlinking = true);
      Future.delayed(const Duration(milliseconds: 120), () {
        if (mounted) setState(() => _isBlinking = false);
      });
    });

    _emotion.startRandomExpressions(() {
      if (mounted) setState(() {});
    });

    _emotion.updateMood(BimoState.sleeping, () => setState(() {}));

    _spontaneousPoller = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _checkSpontaneous(),
    );
  }

  // ─────────────────────────────────────────
  Future<void> _setupTTS() async {
    await _tts.setLanguage("ar-SA");
    await _tts.setPitch(0.70);
    await _tts.setSpeechRate(0.48);
    await _tts.setVolume(1.0);
    await _tts.awaitSpeakCompletion(true);

    try {
      final voices = await _tts.getVoices;
      if (voices != null) {
        final List<Map<String, String>> voiceList = (voices as List).map((v) {
          return Map<String, String>.from(v as Map);
        }).toList();

        Map<String, String>? bestVoice;

        for (var v in voiceList) {
          final name = v['name']?.toLowerCase() ?? '';
          final locale = v['locale']?.toLowerCase() ?? '';
          if (locale.contains('ar') &&
              name.contains('network') &&
              name.contains('male')) {
            bestVoice = v;
            break;
          }
        }

        if (bestVoice == null) {
          for (var v in voiceList) {
            final name = v['name']?.toLowerCase() ?? '';
            final locale = v['locale']?.toLowerCase() ?? '';
            if (locale.contains('ar') &&
                (name.contains('male') ||
                    name.contains('tarik') ||
                    name.contains('majed'))) {
              bestVoice = v;
              break;
            }
          }
        }

        if (bestVoice != null) {
          await _tts.setVoice({
            'name': bestVoice['name']!,
            'locale': bestVoice['locale']!,
          });
          debugPrint('🎤 تم تفعيل الصوت الفخم: ${bestVoice['name']}');
        } else {
          debugPrint('🎤 تم تفعيل الصوت الافتراضي مع تضخيم النبرة');
        }
      }
    } catch (e) {
      debugPrint('⚠️ خطأ في إعداد الصوت: $e');
    }

    _tts.setCompletionHandler(_releaseBusy);
    _tts.setCancelHandler(_releaseBusy);
    _tts.setErrorHandler((_) => _releaseBusy());
  }

  // ─────────────────────────────────────────
  void _handleSpeech(String words) {
    if (words.isEmpty) return;
    final cmd = words.trim().toLowerCase();
    debugPrint('🎙 "$cmd"');

    setState(() {
      _hudAction = 'none'; // 🔥 إخفاء النافذة القديمة عند بدء حوار جديد
    });

    _cancelAlone();

    if (!_emotion.isAwake) {
      const wake = [
        'بيمو',
        'ديمو',
        'فيمو',
        'مرحبا',
        'اصحى',
        'استيقظ',
        'bimo',
        'hey bimo',
      ];
      if (wake.any((w) => cmd.contains(w))) _wakeUp();
      return;
    }

    _resetSleepTimer();
    _resetAloneTimer();

    if (_isBusy) {
      if (cmd.contains('اسكت') ||
          cmd.contains('وقف') ||
          cmd.contains('كفى') ||
          cmd.contains('stop') ||
          cmd.contains('quiet')) {
        _tts.stop();
        _releaseBusy();
        _emotion.updateMood(BimoState.idle, () => setState(() {}));
      }
      return;
    }

    final sleepCmds = [
      'إلى اللقاء',
      'نوم',
      'أرتاح',
      'مع السلامة',
      'bye',
      'sleep',
      'good night',
    ];
    if (sleepCmds.any((kw) => cmd.contains(kw))) {
      _goToSleep();
    } else {
      _callBrain(words.trim());
    }
  }

  // ─────────────────────────────────────────
  void _wakeUp() {
    _emotion.isAwake = true;
    _resetSleepTimer();
    _resetAloneTimer();
    _tts.stop();
    _releaseBusy();

    _wakeWord.stopListening();
    _mic.startListening();

    _emotion.updateMood(BimoState.happy, () => setState(() {}));
    _vision.quickFaceScan((off) {
      if (mounted) setState(() => _faceOffset = off);
    });
    const gs = [
      'نعم، أنا هنا!',
      'صحيت! شو في؟',
      'أيوه، تفضل.',
      'هلا، قل.',
      'Yes! I\'m here!',
    ];
    _speak(gs[_rng.nextInt(gs.length)]);
  }

  void _goToSleep() async {
    _emotion.isAwake = false;
    _sleepTimer?.cancel();
    _cancelAlone();
    _api.clearHistory();

    _mic.stopListening();
    _emotion.updateMood(BimoState.sleeping, () => setState(() {}));

    await _speak('تصبح على خير!');
    await Future.delayed(const Duration(milliseconds: 1500));

    if (!_emotion.isAwake) {
      _wakeWord.startListening();
    }
  }

  void _resetSleepTimer() {
    _sleepTimer?.cancel();
    _sleepTimer = Timer(const Duration(minutes: 5), () {
      if (_emotion.isAwake && mounted && !_isBusy) _goToSleep();
    });
  }

  // ─────────────────────────────────────────
  void _resetAloneTimer() {
    _aloneTimer?.cancel();
    _aloneRepeat?.cancel();
    _aloneMode = false;
    _aloneTimer = Timer(const Duration(seconds: 60), _startAlone);
  }

  void _startAlone() {
    if (!_emotion.isAwake || _isBusy || !mounted) return;
    _aloneMode = true;
    if (mounted) setState(() {});
    _doAloneAction(0);
    int phase = 1;
    _aloneRepeat = Timer.periodic(const Duration(seconds: 90), (_) {
      if (!_emotion.isAwake || _isBusy || !mounted) {
        _cancelAlone();
        return;
      }
      _doAloneAction(phase % 4);
      phase++;
    });
  }

  void _doAloneAction(int phase) {
    switch (phase) {
      case 0:
        const calls = ['وين رحت؟', 'هلو؟', 'لازلت هناك؟', 'تعال ندردش!'];
        _emotion.updateMood(BimoState.surprised, () => setState(() {}));
        _speak(calls[_rng.nextInt(calls.length)]);
        break;
      case 1:
        const acts = ['wink', 'look_away', 'spin', 'nod_yes'];
        const states = [BimoState.happy, BimoState.excited, BimoState.shy];
        _emotion.updateMood(
          states[_rng.nextInt(states.length)],
          () => setState(() {}),
        );
        _emotion.executeFaceAction(
          acts[_rng.nextInt(acts.length)],
          () => setState(() {}),
        );
        Timer(const Duration(milliseconds: 1200), () {
          if (!mounted || _isBusy) return;
          _emotion.executeFaceAction(
            acts[_rng.nextInt(acts.length)],
            () => setState(() {}),
          );
        });
        break;
      case 2:
        const mono = [
          'بفكر... هل الوقت نسبي فعلاً؟',
          'الصمت مريح أحياناً.',
          'لو كنت إنساناً كنت شغلت موسيقى.',
        ];
        _emotion.updateMood(BimoState.thinking, () => setState(() {}));
        _speak(mono[_rng.nextInt(mono.length)]);
        break;
      case 3:
        _emotion.updateMood(BimoState.excited, () => setState(() {}));
        _emotion.executeFaceAction('spin', () => setState(() {}));
        Timer(const Duration(milliseconds: 800), () {
          if (!mounted) return;
          _emotion.executeFaceAction('wink', () => setState(() {}));
        });
        Timer(const Duration(milliseconds: 1600), () {
          if (!mounted) return;
          _emotion.executeFaceAction('nod_yes', () => setState(() {}));
        });
        break;
    }
  }

  void _cancelAlone() {
    _aloneTimer?.cancel();
    _aloneRepeat?.cancel();
    _aloneMode = false;
  }

  // ─────────────────────────────────────────
  Future<void> _checkSpontaneous() async {
    if (!_emotion.isAwake || _isBusy || !mounted) return;
    final result = await _api.checkSpontaneous();
    if (result == null || result['speak'] != true) return;

    final reply = result['reply'] as String? ?? '';
    if (reply.isEmpty) return;

    _emotion.updateMood(
      _emotion.mapEmotion(result['emotion'] as String?),
      () => setState(() {}),
    );
    _emotion.executeFaceAction(
      result['face_action'] as String?,
      () => setState(() {}),
    );
    await _speak(reply);
  }

  // ─────────────────────────────────────────
  Future<void> _callBrain(String message) async {
    _mic.pauseForSpeaking();
    _setBusy(true, autoRelease: const Duration(seconds: 30));
    _emotion.updateMood(BimoState.thinking, () => setState(() {}));

    String? base64Image;
    final needsVision = _visionKeywords.any(
      (kw) => message.toLowerCase().contains(kw),
    );

    if (needsVision) {
      debugPrint('📸 يفتح الكاميرا...');
      await _vision.quickFaceScan((off) {
        if (mounted) setState(() => _faceOffset = off);
      });
      base64Image = await _vision.takeSnapshotBase64();
      debugPrint(base64Image != null ? '✅ صورة جاهزة' : '❌ فشل التصوير');
    }

    final res = await _api.askBimo(
      message,
      visionData: {
        if (base64Image != null)
          'image':
              base64Image, // 🔥 تم تصحيح الكتابة البرمجية هنا لتجنب خطأ الـ Dart
        'suppress_name': _replysSinceNameUsed < 6,
      },
    );

    if (!mounted) return;

    if (res != null) {
      _emotion.updateMood(
        _emotion.mapEmotion(res['emotion'] as String?),
        () => setState(() {}),
      );
      _emotion.executeFaceAction(
        res['face_action'] as String?,
        () => setState(() {}),
      );

      // 🔥 قراءة أوامر الشاشة العائمة
      _hudAction = res['ui_action'] as String? ?? 'none';
      _hudUrl = res['media_url'] as String? ?? '';
      _hudImageUrl = res['image_url'] as String? ?? ''; // 🔥 أضف هذا
      _hudTitle = res['media_title'] as String? ?? '';

      _replysSinceNameUsed++;
      await _speak(res['reply'] as String? ?? 'لم أفهم.');
    } else {
      _releaseBusy();
      _emotion.updateMood(BimoState.idle, () => setState(() {}));
    }
  }

  // ─────────────────────────────────────────
  void _startMouthAnimation() {
    _mouthTimer?.cancel();
    _mouthTimer = Timer.periodic(const Duration(milliseconds: 130), (t) {
      if (!_isBusy) {
        t.cancel();
        if (mounted) setState(() => _isMouthOpen = false);
      } else {
        if (mounted) setState(() => _isMouthOpen = !_isMouthOpen);
      }
    });
  }

  Future<void> _speak(String text) async {
    if (text.isEmpty) return;
    final dur = Duration(seconds: (text.length / 5).ceil() + 4);
    _setBusy(true, autoRelease: dur);

    if (_emotion.isAwake) {
      _mic.pauseForSpeaking();
    }

    _startMouthAnimation();
    await _tts.speak(text);
  }

  // ─────────────────────────────────────────
  @override
  void dispose() {
    _wakeWord.dispose();
    _physical.dispose();
    _vision.dispose();
    _sleepTimer?.cancel();
    _busyTimeout?.cancel();
    _mouthTimer?.cancel();
    _aloneTimer?.cancel();
    _aloneRepeat?.cancel();
    _spontaneousPoller?.cancel();
    _emotion.dispose();
    _mic.dispose();
    _tts.stop();
    super.dispose();
  }

  // 🔥 دالة تصميم الميكروفون واليدين عند الغناء
  Widget _buildSingingMic() {
    return Padding(
      padding: const EdgeInsets.only(top: 20),
      child: AnimatedBuilder(
        animation: _pulseAnim,
        builder: (context, child) {
          // حركة اهتزاز (رقص) خفيفة مع الموسيقى
          final danceOffset = (_pulseAnim.value - 1.0) * 80;
          return Transform.translate(
            offset: Offset(0, -danceOffset),
            child: child,
          );
        },
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // اليد اليسرى
            Container(
              width: 25,
              height: 25,
              decoration: const BoxDecoration(
                color: Colors.cyanAccent,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 5),
            // الميكروفون
            const Icon(
              Icons.mic_external_on,
              color: Colors.white,
              size: 55,
              shadows: [Shadow(color: Colors.cyan, blurRadius: 15)],
            ),
            const SizedBox(width: 5),
            // اليد اليمنى
            Container(
              width: 25,
              height: 25,
              decoration: const BoxDecoration(
                color: Colors.cyanAccent,
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // 🔥 دالة تجلب لون المزاج الحالي للنافذة العائمة
  Color _getGlowColor() {
    switch (_emotion.currentState) {
      case BimoState.happy:
        return Colors.greenAccent;
      case BimoState.angry:
        return Colors.redAccent;
      case BimoState.dizzy:
        return Colors.orangeAccent;
      case BimoState.thinking:
        return Colors.purpleAccent;
      default:
        return Colors.cyanAccent;
    }
  }

  // ─────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    Offset pos = _faceOffset;
    double scale = 1.0;
    double rot = 0.0;

    switch (_emotion.currentFaceAction) {
      case FaceAction.lookAway:
        pos = Offset(_faceOffset.dx + 40, _faceOffset.dy);
        break;
      case FaceAction.nodYes:
        pos = Offset(_faceOffset.dx, _faceOffset.dy + 10);
        break;
      case FaceAction.zoomIn:
        scale = 1.15;
        break;
      case FaceAction.spin:
        rot = 0.12;
        break;
      default:
        break;
    }

    final animScale = _emotion.currentState == BimoState.listening
        ? _pulseAnim.value
        : _breathing.value;

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          _buildBg(),

          // ✨ نظام الهولوغرام والجزيئات (خلف بيمو)
          HologramLayer(
            color: _getGlowColor(),
            isActive: _emotion.currentState != BimoState.sleeping,
          ),

          Center(
            child: Transform.scale(
              scale: animScale,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                curve: Curves.easeInOut,
                transform: BimoAnimations.getFaceTransform(pos, rot)
                  ..scale(scale, scale, 1.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (_emotion.currentFaceAction == FaceAction.cry) _tears(),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        BimoFacePainter.buildEyebrow(
                          _emotion.currentState,
                          true,
                        ),
                        const SizedBox(width: 50),
                        BimoFacePainter.buildEyebrow(
                          _emotion.currentState,
                          false,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        BimoFacePainter.buildEye(
                          _emotion.currentState,
                          _isBlinking,
                          pos,
                          winkLeft:
                              _emotion.currentFaceAction == FaceAction.wink &&
                              _emotion.winkLeft,
                          winkRight: false,
                          isLaughing:
                              _emotion.currentFaceAction == FaceAction.laugh,
                        ),
                        const SizedBox(width: 50),
                        BimoFacePainter.buildEye(
                          _emotion.currentState,
                          _isBlinking,
                          pos,
                          winkLeft: false,
                          winkRight:
                              _emotion.currentFaceAction == FaceAction.wink &&
                              !_emotion.winkLeft,
                          isLaughing:
                              _emotion.currentFaceAction == FaceAction.laugh,
                        ),
                      ],
                    ),
                    const SizedBox(height: 50),
                    BimoFacePainter.buildMouth(
                      _emotion.currentState,
                      isTalking: _isBusy && _isMouthOpen,
                      isLaughing:
                          _emotion.currentFaceAction == FaceAction.laugh,
                    ),
                    const SizedBox(height: 30),
                    _statusLabel(),

                    // 🔥 الميكروفون واليدين عند الغناء
                    if (_emotion.currentFaceAction == FaceAction.sing)
                      _buildSingingMic(),
                  ],
                ),
              ),
            ),
          ),

          // 🌐 شاشة الهولوغرام العائمة (HUD) تضاف هنا كطبقة فوق الجميع
          // 🌐 شاشة الهولوغرام العائمة (HUD)
          HudLayer(
            uiAction: _hudAction,
            mediaUrl: _hudUrl,
            imageUrl: _hudImageUrl, // 🔥 أضف هذا
            mediaTitle: _hudTitle,
            glowColor: _getGlowColor(),
          ),
        ],
      ),
    );
  }

  Widget _tears() => Row(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [_tearDrop(), const SizedBox(width: 100), _tearDrop()],
  );

  Widget _tearDrop() => Container(
    width: 8,
    height: 20,
    decoration: BoxDecoration(
      color: Colors.lightBlueAccent.withOpacity(0.8),
      borderRadius: const BorderRadius.only(
        bottomLeft: Radius.circular(8),
        bottomRight: Radius.circular(8),
      ),
    ),
  );

  Widget _buildBg() {
    Color c = Colors.transparent;
    switch (_emotion.currentState) {
      case BimoState.happy:
      case BimoState.excited:
        c = Colors.green.withOpacity(0.05);
        break;
      case BimoState.angry:
        c = Colors.red.withOpacity(0.05);
        break;
      case BimoState.sad:
        c = Colors.blue.withOpacity(0.05);
        break;
      case BimoState.proud:
        c = Colors.amber.withOpacity(0.04);
        break;
      case BimoState.shy:
        c = Colors.pink.withOpacity(0.04);
        break;
      case BimoState.thinking:
      case BimoState.listening:
        c = Colors.yellow.withOpacity(0.04);
        break;
      default:
        break;
    }
    return AnimatedContainer(
      duration: const Duration(milliseconds: 600),
      color: c,
    );
  }

  Widget _statusLabel() {
    String t = '';
    Color c = Colors.transparent;
    if (_isBusy && _emotion.currentState != BimoState.thinking) {
      t = '◉ يتكلم';
      c = Colors.cyanAccent.withOpacity(0.7);
    } else {
      switch (_emotion.currentState) {
        case BimoState.thinking:
          t = '◌ يفكر...';
          c = Colors.purpleAccent;
          break;
        case BimoState.sleeping:
          t = 'z z z';
          c = Colors.grey;
          break;
        default:
          t = _aloneMode ? '○ وحيد...' : '● يستمع';
          c = Colors.yellowAccent.withOpacity(0.6);
      }
    }
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 300),
      opacity: t.isEmpty ? 0 : 1,
      child: Text(
        t,
        style: TextStyle(color: c, fontSize: 14, letterSpacing: 2),
      ),
    );
  }
}
