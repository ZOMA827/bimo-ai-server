// lib/main.dart — بيمو برو: النسخة الإنتاجية الشاملة 🎭 (يوتيوب + أخبار + نوافذ + حركة)

import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';

import 'core/api_service.dart';
import 'senses/vision_awareness.dart';
import 'senses/smart_mic.dart';
import 'senses/wake_word_engine.dart';
import 'senses/physical_awareness.dart';
import 'engines/emotion_engine.dart';

import 'ui/bimo_face.dart';
import 'ui/animations.dart';
import 'ui/hologram_layer.dart';
import 'ui/hud_layer.dart'; // 🔥 عادت طبقة اليوتيوب والطقس!
import 'ui/floating_windows.dart'; // النوافذ العائمة
import 'ui/news_panel.dart'; // سلايد الأخبار

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
  final WakeWordEngine _wakeWord = WakeWordEngine();
  final PhysicalAwareness _physical = PhysicalAwareness();
  final EmotionEngine _emotion = EmotionEngine();
  final FlutterTts _tts = FlutterTts();

  late Animation<double> _breathing;
  late Animation<double> _pulseAnim;

  Offset _faceOffset = Offset.zero;
  bool _isBlinking = false;
  bool _isBusy = false;
  bool _isMouthOpen = false;
  String _currentTtsLang = 'ar-SA';

  // ─── متغيرات الـ HUD القديمة (عادت من جديد!) ───
  String _currentUiAction = 'none';
  String _mediaUrl = '';
  String _imageUrl = '';
  String _mediaTitle = '';

  // ─── إحداثيات المسرح (حركة بيمو) ───
  double _bimoAlignX = 0.0;
  double _bimoAlignY = 0.0;
  double _bimoScale = 1.0;

  // ─── النوافذ العائمة ───
  final List<FloatWindow> _floatWins = [];
  int _winCounter = 0;

  // ─── لوحة الأخبار المنزلقة ───
  bool _showNews = false;
  String _newsTitle = '';
  String _newsBody = '';
  String _newsImageUrl = '';

  Timer? _busyTimeout;
  Timer? _mouthTimer;
  Timer? _spontaneousPoller;

  static const _visionKeywords = [
    'شوف',
    'انظر',
    'نظر',
    'هنا',
    'ما هذا',
    'ملابس',
    'قميص',
    'لون',
    'ابتسم',
    'رأيك',
    'صورة',
    'look',
    'see',
  ];

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

    final micOk = await _mic.initialize(_handleSpeech, onLoudNoise: _onClap);
    if (micOk) _mic.startListening();

    await _wakeWord.initialize(_wakeUp);
    _wakeWord.startListening();

    _physical.initialize(onShake: _onShake, onFaceDown: _onFaceDown);

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

  // ─── أوامر المسرح الجديدة ───
  void _updateBimoPosition(String position, double scale) {
    _bimoScale = scale;
    switch (position) {
      case 'top_right':
        _bimoAlignX = 0.8;
        _bimoAlignY = -0.7;
        break;
      case 'top_left':
        _bimoAlignX = -0.8;
        _bimoAlignY = -0.7;
        break;
      case 'top_center':
        _bimoAlignX = 0.0;
        _bimoAlignY = -0.7;
        break;
      case 'bottom_right':
        _bimoAlignX = 0.8;
        _bimoAlignY = 0.7;
        break;
      case 'bottom_left':
        _bimoAlignX = -0.8;
        _bimoAlignY = 0.7;
        break;
      case 'center':
      default:
        _bimoAlignX = 0.0;
        _bimoAlignY = 0.0;
        break;
    }
  }

  void _addFloatWindow(String title, String content) {
    if (_floatWins.length >= 3) _floatWins.removeAt(0);
    final id = 'w${_winCounter++}';
    double startX = 20.0 + (_floatWins.length * 30);
    double startY = 80.0 + (_floatWins.length * 40);
    setState(
      () => _floatWins.add(
        FloatWindow(
          id: id,
          title: title,
          content: content,
          x: startX,
          y: startY,
        ),
      ),
    );
  }

  void _openNewsPanel(String title, String body, String imageUrl) {
    setState(() {
      _newsTitle = title;
      _newsBody = body;
      _newsImageUrl = imageUrl;
      _showNews = true;
      _bimoAlignX = 0.0;
      _bimoAlignY = -0.8;
      _bimoScale = 0.8;
      _faceOffset = const Offset(0, 25); // بيمو ينظر للأسفل نحو الخبر!
    });
  }

  void _closeNewsPanel() {
    setState(() {
      _showNews = false;
      _bimoAlignY = 0.0;
      _bimoScale = 1.0;
      _faceOffset = Offset.zero;
    });
  }

  // ─── إعدادات الصوت والحواس ───
  Future<void> _setupTTS() async {
    await _tts.setLanguage('ar-SA');
    await _tts.setPitch(0.85);
    await _tts.setSpeechRate(0.47);
    _tts.setCompletionHandler(_releaseBusy);
    _tts.setCancelHandler(_releaseBusy);
    _tts.setErrorHandler((_) => _releaseBusy());
  }

  Future<void> _adaptTtsLang(String text) async {
    final hasEn = RegExp(r'[a-zA-Z]{4,}').hasMatch(text);
    final lang = hasEn ? 'en-US' : 'ar-SA';
    if (lang != _currentTtsLang) {
      _currentTtsLang = lang;
      await _tts.setLanguage(lang);
    }
  }

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

  void _onShake() {
    if (!_emotion.isAwake) return;
    _emotion.updateMood(BimoState.dizzy, () => setState(() {}));
    _emotion.executeFaceAction('spin', () => setState(() {}));
    _speak('يا.. دوختني!');
  }

  void _onClap() {
    if (!_emotion.isAwake) return;
    _emotion.updateMood(BimoState.excited, () => setState(() {}));
    _emotion.executeFaceAction('laugh', () => setState(() {}));
    _speak('شكراً! أحب التصفيق!');
  }

  void _onFaceDown() {
    if (_emotion.isAwake) _goToSleep();
  }

  void _handleSpeech(String words) {
    if (words.isEmpty) return;
    final cmd = words.trim().toLowerCase();
    debugPrint('🎙 "$cmd"');

    if (!_emotion.isAwake) {
      if (['بيمو', 'استيقظ', 'bimo'].any((w) => cmd.contains(w))) _wakeUp();
      return;
    }

    if (_isBusy && ['اسكت', 'وقف', 'stop'].any((w) => cmd.contains(w))) {
      _tts.stop();
      _releaseBusy();
      return;
    }

    if (['إلى اللقاء', 'نوم', 'sleep'].any((w) => cmd.contains(w))) {
      _goToSleep();
    } else {
      _callBrain(words.trim());
    }
  }

  void _wakeUp() {
    if (_emotion.isAwake) return;
    _emotion.isAwake = true;
    _wakeWord.stopListening();
    _emotion.updateMood(BimoState.happy, () => setState(() {}));
    _emotion.executeFaceAction('zoom_in', () => setState(() {}));
    _speak('نعم، أنا هنا!');
  }

  void _goToSleep() {
    _emotion.isAwake = false;
    _closeNewsPanel();
    _floatWins.clear();
    setState(() => _currentUiAction = 'none'); // إغلاق اليوتيوب عند النوم
    _api.clearHistory();
    _emotion.updateMood(BimoState.sleeping, () => setState(() {}));
    _bimoAlignX = 0.0;
    _bimoAlignY = 0.0;
    _bimoScale = 1.0;
    _speak('تصبح على خير!');
    Future.delayed(const Duration(seconds: 3), _wakeWord.startListening);
  }

  Future<void> _checkSpontaneous() async {
    if (!_emotion.isAwake || _isBusy || !mounted) return;
    final result = await _api.checkSpontaneous();
    if (result == null || result['speak'] != true) return;
    _speak(result['reply'] ?? '');
  }

  // ─── العقل المدبر ودمج الـ JSON ───
  Future<void> _callBrain(String message) async {
    _mic.pauseForSpeaking();
    _setBusy(true, autoRelease: const Duration(seconds: 30));
    _emotion.updateMood(BimoState.thinking, () => setState(() {}));

    String? base64Image;
    if (_visionKeywords.any((kw) => message.toLowerCase().contains(kw))) {
      base64Image = await _vision.takeSnapshotBase64();
    }

    final res = await _api.askBimo(
      message,
      visionData: {if (base64Image != null) 'image': base64Image},
    );
    if (!mounted) return;

    if (res != null) {
      _emotion.updateMood(
        _emotion.mapEmotion(res['emotion']),
        () => setState(() {}),
      );
      _emotion.executeFaceAction(res['face_action'], () => setState(() {}));

      setState(() {
        // 🔥 تحديث متغيرات اليوتيوب والبطاقات (التي تم حذفها بالخطأ سابقاً)
        _currentUiAction = res['ui_action'] ?? 'none';
        _mediaUrl = res['media_url'] ?? '';
        _imageUrl = res['image_url'] ?? '';
        _mediaTitle = res['media_title'] ?? '';

        // أوامر المسرح وحركة بيمو
        final layout = res['bimo_layout'] as Map<String, dynamic>?;
        if (layout != null && !_showNews) {
          _updateBimoPosition(
            layout['position'] ?? 'center',
            (layout['scale'] ?? 1.0).toDouble(),
          );
        }

        // أوامر سلايد الأخبار
        final bottomSheet = res['bottom_sheet'] as Map<String, dynamic>?;
        if (bottomSheet != null && bottomSheet['active'] == true) {
          _openNewsPanel(
            bottomSheet['title'] ?? '',
            bottomSheet['description'] ?? '',
            bottomSheet['image_url'] ?? '',
          );
        } else if (_showNews) {
          _closeNewsPanel();
        }

        // أوامر النوافذ العائمة
        final windows = res['floating_windows'] as List?;
        if (windows != null) {
          for (var w in windows) {
            _addFloatWindow(w['title'] ?? 'نافذة', w['data'] ?? '');
          }
        }
      });

      await _speak(res['reply'] ?? 'لم أفهم.');
    } else {
      _releaseBusy();
      _emotion.updateMood(BimoState.idle, () => setState(() {}));
    }
  }

  void _startMouthAnimation() {
    _mouthTimer?.cancel();
    _mouthTimer = Timer.periodic(const Duration(milliseconds: 130), (t) {
      if (!_isBusy) {
        t.cancel();
        if (mounted) setState(() => _isMouthOpen = false);
        return;
      }
      if (mounted) setState(() => _isMouthOpen = !_isMouthOpen);
    });
  }

  Future<void> _speak(String text) async {
    if (text.isEmpty) return;
    _setBusy(
      true,
      autoRelease: Duration(seconds: (text.length / 5).ceil() + 4),
    );
    _startMouthAnimation();
    await _adaptTtsLang(text);
    await _tts.speak(text);
  }

  Color _glowColor() {
    switch (_emotion.currentState) {
      case BimoState.happy:
        return Colors.greenAccent;
      case BimoState.angry:
        return Colors.redAccent;
      case BimoState.sad:
        return Colors.lightBlueAccent;
      case BimoState.thinking:
        return Colors.purpleAccent;
      default:
        return Colors.cyanAccent;
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenH = MediaQuery.of(context).size.height;
    final animScale =
        (_emotion.currentState == BimoState.listening
            ? _pulseAnim.value
            : _breathing.value) *
        _bimoScale;
    final glow = _glowColor();

    Offset currentFacePos = _faceOffset;
    if (_emotion.currentFaceAction == FaceAction.lookAway) {
      currentFacePos = Offset(_faceOffset.dx + 40, _faceOffset.dy);
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 600),
            color: glow.withOpacity(0.04),
          ),
          HologramLayer(color: glow, isActive: _emotion.isAwake),

          // 1. وجه بيمو المتحرك
          AnimatedAlign(
            duration: const Duration(milliseconds: 700),
            curve: Curves.easeInOutBack,
            alignment: Alignment(_bimoAlignX, _bimoAlignY),
            child: Transform.scale(
              scale: animScale,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                transform: BimoAnimations.getFaceTransform(
                  currentFacePos,
                  _emotion.currentFaceAction == FaceAction.spin ? 0.15 : 0.0,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
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
                          currentFacePos,
                          isLaughing:
                              _emotion.currentFaceAction == FaceAction.laugh,
                        ),
                        const SizedBox(width: 50),
                        BimoFacePainter.buildEye(
                          _emotion.currentState,
                          _isBlinking,
                          currentFacePos,
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
                  ],
                ),
              ),
            ),
          ),

          // 2. النوافذ العائمة (معلومات قصيرة)
          if (_floatWins.isNotEmpty)
            FloatingWindowManager(
              windows: _floatWins,
              glowColor: glow,
              onClose: (id) =>
                  setState(() => _floatWins.removeWhere((w) => w.id == id)),
            ),

          // 3. طبقة اليوتيوب والطقس (HudLayer) 🔥 عادت هنا من جديد!
          if (_currentUiAction != 'none')
            HudLayer(
              uiAction: _currentUiAction,
              mediaUrl: _mediaUrl,
              imageUrl: _imageUrl,
              mediaTitle: _mediaTitle,
              glowColor: glow,
            ),

          // 4. لوحة الأخبار المنزلقة (الأخبار الطويلة)
          AnimatedPositioned(
            duration: const Duration(milliseconds: 600),
            curve: Curves.easeOutExpo,
            bottom: _showNews ? 0 : -screenH,
            left: 0,
            right: 0,
            height: screenH * 0.55,
            child: NewsPanel(
              title: _newsTitle,
              body: _newsBody,
              imageUrl: _newsImageUrl,
              color: glow,
              onClose: _closeNewsPanel,
            ),
          ),
        ],
      ),
    );
  }
}
