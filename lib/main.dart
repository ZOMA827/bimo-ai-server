// lib/main.dart — بيمو برو النهائي
// ✅ لا كلام عشوائي | كاميرا Lazy | صوت ذكر | مبادرات ذكية

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
  final Random _rng = Random();

  late Animation<double> _breathing;
  late Animation<double> _pulseAnim;

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
  Timer? _spontaneousPoller; // يسأل السيرفر عن مبادرات العقل الباطن

  int _replysSinceNameUsed = 0;

  static const _visionKeywords = [
    'شوف',
    'انظر',
    'نظر',
    'هنا',
    'ما هذا',
    'ماذا البس',
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
  ];

  // ─────────────────────────────────────────
  // Busy
  // ─────────────────────────────────────────
  void _setBusy(bool v, {Duration? autoRelease}) {
    _busyTimeout?.cancel();
    _isBusy = v;
    if (v && autoRelease != null)
      _busyTimeout = Timer(autoRelease, _releaseBusy);
    if (mounted) setState(() {});
  }

  void _releaseBusy() {
    _busyTimeout?.cancel();
    _isBusy = false;
    _mic.resumeAfterSpeaking();
    if (mounted) setState(() {});
  }

  // ─────────────────────────────────────────
  // Init
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
    final micOk = await _mic.initialize(_handleSpeech);
    if (micOk) _mic.startListening();

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

    // بدء polling العقل الباطن — كل 30 ثانية
    _spontaneousPoller = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _checkSpontaneous(),
    );
  }

  // ─────────────────────────────────────────
  // ✅ صوت ذكر — pitch = 0.85 (أقل من 1.0 = أعمق)
  // ─────────────────────────────────────────
  Future<void> _setupTTS() async {
    await _tts.setLanguage("ar-SA");
    await _tts.setPitch(0.85);
    await _tts.setSpeechRate(0.47);
    await _tts.setVolume(1.0);

    final voices = await _tts.getVoices;
    if (voices != null) {
      final list = voices as List;
      final male = list.firstWhere(
        (v) =>
            v['locale']?.toString().contains('ar') == true &&
            (v['name']?.toString().toLowerCase().contains('male') == true ||
                v['name']?.toString().toLowerCase().contains('tarik') == true ||
                v['name']?.toString().toLowerCase().contains('hamdan') ==
                    true ||
                v['name']?.toString().toLowerCase().contains('omar') == true),
        orElse: () => null,
      );
      final arab =
          male ??
          list.firstWhere(
            (v) => v['locale']?.toString().contains('ar') == true,
            orElse: () => null,
          );
      if (arab != null) {
        await _tts.setVoice({'name': arab['name'], 'locale': arab['locale']});
        debugPrint('🎤 صوت: ${arab['name']}');
      }
    }
    _tts.setCompletionHandler(_releaseBusy);
    _tts.setCancelHandler(_releaseBusy);
    _tts.setErrorHandler((_) => _releaseBusy());
  }

  // ─────────────────────────────────────────
  // ✅ معالجة الكلام — فقط لما يتكلم المستخدم فعلاً
  // ─────────────────────────────────────────
  void _handleSpeech(String words) {
    if (words.isEmpty) return;
    final cmd = words.trim().toLowerCase();
    debugPrint('🎙 "$cmd"');

    _cancelAlone(); // المستخدم عاد — ألغِ وحدة بيمو

    if (!_emotion.isAwake) {
      const wake = ['بيمو', 'ديمو', 'فيمو', 'مرحبا', 'اصحى', 'استيقظ', 'bimo'];
      if (wake.any((w) => cmd.contains(w))) _wakeUp();
      return;
    }

    _resetSleepTimer();
    _resetAloneTimer();

    if (_isBusy) {
      if (cmd.contains('اسكت') || cmd.contains('وقف') || cmd.contains('كفى')) {
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
    _emotion.updateMood(BimoState.happy, () => setState(() {}));
    _vision.quickFaceScan((off) {
      if (mounted) setState(() => _faceOffset = off);
    });
    const gs = ['نعم، أنا هنا!', 'صحيت! شو في؟', 'أيوه، تفضل.', 'هلا، قل.'];
    _speak(gs[_rng.nextInt(gs.length)]);
  }

  void _goToSleep() {
    _emotion.isAwake = false;
    _sleepTimer?.cancel();
    _cancelAlone();
    _api.clearHistory();
    _emotion.updateMood(BimoState.sleeping, () => setState(() {}));
    _speak('تصبح على خير!');
  }

  void _resetSleepTimer() {
    _sleepTimer?.cancel();
    _sleepTimer = Timer(const Duration(minutes: 5), () {
      if (_emotion.isAwake && mounted && !_isBusy) _goToSleep();
    });
  }

  // ─────────────────────────────────────────
  // ✅ السلوك الانفرادي — Flutter side
  // (الذكاء الحقيقي في SubconsciousAgent بالسيرفر)
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
        // يلعب بوجهه بدون كلام
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
        // "رقص"
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
  // ✅ Polling العقل الباطن من السيرفر
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
  // استدعاء العقل
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
      // ✅ ابدأ بمسح الوجه أولاً (للتتبع)، ثم التقط الصورة
      await _vision.quickFaceScan((off) {
        if (mounted) setState(() => _faceOffset = off);
      });
      base64Image = await _vision.takeSnapshotBase64();
      debugPrint(base64Image != null ? '✅ صورة جاهزة' : '❌ فشل التصوير');
    }

    final res = await _api.askBimo(
      message,
      visionData: {
        if (base64Image != null) 'image': base64Image,
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
    _mic.pauseForSpeaking();
    _startMouthAnimation();
    await _tts.speak(text);
  }

  // ─────────────────────────────────────────
  @override
  void dispose() {
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
                  ],
                ),
              ),
            ),
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
    } else
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
