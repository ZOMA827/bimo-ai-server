import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import 'dart:math';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:camera/camera.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const MaterialApp(debugShowCheckedModeBanner: false, home: BimoProFace()),
  );
}

// 😭 تمت إضافة حالة الحزن (sad)
enum BimoState { idle, happy, angry, sad, listening, dizzy, bored }

class BimoProFace extends StatefulWidget {
  const BimoProFace({super.key});
  @override
  State<BimoProFace> createState() => _BimoProFaceState();
}

class _BimoProFaceState extends State<BimoProFace>
    with TickerProviderStateMixin {
  late AnimationController _breathingController;
  late Animation<double> _breathingAnimation;
  bool _isUserSmiling = false;
  bool _isBlinking = false;
  BimoState _currentState = BimoState.idle;

  Timer? _moodTimer;
  Timer? _roamingTimer;
  Timer? _shakeTimer;
  Timer? _idleTimer;

  final Random _random = Random();
  final SpeechToText _speechToText = SpeechToText();
  final FlutterTts _flutterTts = FlutterTts();

  // 🎤 متغيرات نظام الاستماع الدائم
  bool _speechEnabled = false;
  bool _isSpeaking = false; // لمنع بيمو من الاستماع لنفسه وهو يتحدث

  CameraController? _cameraController;
  FaceDetector? _faceDetector;
  bool _isDetecting = false;
  List<CameraDescription>? _cameras;

  Offset _faceOffset = Offset.zero;
  Offset _lookTarget = Offset.zero;
  double _shakeOffset = 0.0;
  double _headRotation = 0;
  int _musicIndex = 0;
  final List<String> _musicNotes = ["♪", "♫", "♬"];

  @override
  void initState() {
    super.initState();
    _initVoice();
    _initVision();

    _breathingController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _breathingAnimation = Tween<double>(begin: 1.0, end: 1.03).animate(
      CurvedAnimation(parent: _breathingController, curve: Curves.easeInOut),
    );

    Timer.periodic(const Duration(seconds: 4), (timer) {
      if (mounted && _currentState == BimoState.idle) {
        setState(() => _isBlinking = true);
        Future.delayed(const Duration(milliseconds: 150), () {
          if (mounted) setState(() => _isBlinking = false);
        });
      }
    });

    _startRoaming();
    _startIdleWatcher();
  }

  // ... (نفس دوال الكاميرا والرؤية كما هي) ...
  Future<void> _initVision() async {
    _cameras = await availableCameras();
    final frontCamera = _cameras?.firstWhere(
      (camera) => camera.lensDirection == CameraLensDirection.front,
      orElse: () => _cameras!.first,
    );
    if (frontCamera != null) {
      _cameraController = CameraController(
        frontCamera,
        ResolutionPreset.low,
        enableAudio: false,
      );
      await _cameraController?.initialize();
      _faceDetector = FaceDetector(
        options: FaceDetectorOptions(
          enableTracking: true,
          enableClassification: true,
          performanceMode: FaceDetectorMode.fast,
        ),
      );
      _cameraController?.startImageStream(_processCameraImage);
    }
  }

  void _processCameraImage(CameraImage image) async {
    if (_isDetecting || _faceDetector == null) return;
    _isDetecting = true;
    try {
      final WriteBuffer allBytes = WriteBuffer();
      for (final Plane plane in image.planes)
        allBytes.putUint8List(plane.bytes);
      final bytes = allBytes.done().buffer.asUint8List();
      final Size imageSize = Size(
        image.width.toDouble(),
        image.height.toDouble(),
      );
      final InputImageMetadata metadata = InputImageMetadata(
        size: imageSize,
        rotation: InputImageRotation.rotation270deg,
        format: InputImageFormat.nv21,
        bytesPerRow: image.planes[0].bytesPerRow,
      );
      final faces = await _faceDetector!.processImage(
        InputImage.fromBytes(bytes: bytes, metadata: metadata),
      );

      if (faces.isNotEmpty && mounted && _currentState == BimoState.idle) {
        final face = faces.first;
        if (face.smilingProbability != null)
          _isUserSmiling = face.smilingProbability! > 0.6;
        final centerX = face.boundingBox.center.dx;
        final centerY = face.boundingBox.center.dy;
        final dx = -((centerX / imageSize.width) - 0.5) * 120;
        final dy = ((centerY / imageSize.height) - 0.5) * 80;
        setState(() {
          _lookTarget = Offset(dx, dy);
          _faceOffset = Offset(dx * 0.6, dy * 0.6);
        });
        _resetIdleTimer();
      }
    } catch (e) {
      debugPrint("Vision Error: $e");
    } finally {
      _isDetecting = false;
    }
  }

  void _startIdleWatcher() {
    _idleTimer?.cancel();
    _idleTimer = Timer(const Duration(seconds: 8), () {
      if (_currentState == BimoState.idle) _startBoredMode();
    });
  }

  void _startBoredMode() {
    setState(() => _currentState = BimoState.bored);
    Timer.periodic(const Duration(milliseconds: 700), (timer) {
      if (_currentState != BimoState.bored) {
        timer.cancel();
        return;
      }
      setState(() {
        _headRotation = _headRotation == 0.15 ? -0.15 : 0.15;
        _musicIndex = (_musicIndex + 1) % _musicNotes.length;
      });
    });
  }

  void _resetIdleTimer() {
    if (_currentState == BimoState.bored) {
      setState(() {
        _currentState = BimoState.idle;
        _headRotation = 0;
      });
    }
    _startIdleWatcher();
  }

  void _startRoaming() {
    _roamingTimer?.cancel();
    _roamingTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      if (_currentState == BimoState.idle) {
        setState(
          () => _faceOffset = Offset(
            _random.nextDouble() * 20 - 10,
            _random.nextDouble() * 20 - 10,
          ),
        );
      }
    });
  }

  void _setMood(BimoState newState, {int durationSeconds = 4}) {
    setState(() {
      _currentState = newState;
      _shakeOffset = 0;
      _headRotation = 0;
      if (newState == BimoState.listening) {
        _faceOffset = const Offset(50, 0);
        Future.delayed(const Duration(milliseconds: 500), () {
          if (_currentState == BimoState.listening)
            setState(() => _faceOffset = const Offset(-50, 0));
        });
      } else {
        _faceOffset = Offset.zero;
      }
    });

    _moodTimer?.cancel();
    if (newState != BimoState.dizzy &&
        newState != BimoState.bored &&
        newState != BimoState.listening) {
      _moodTimer = Timer(Duration(seconds: durationSeconds), () {
        if (mounted) setState(() => _currentState = BimoState.idle);
      });
    }
    _resetIdleTimer();
  }

  @override
  void dispose() {
    _breathingController.dispose();
    _moodTimer?.cancel();
    _roamingTimer?.cancel();
    _shakeTimer?.cancel();
    _idleTimer?.cancel();
    _cameraController?.dispose();
    _faceDetector?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        // لم نعد بحاجة للنقر للاستماع، لكن سنتركه كخيار إضافي
        onTapDown: (details) => _startListening(),
        child: Container(
          color: Colors.transparent,
          child: Center(
            child: AnimatedContainer(
              duration: _currentState == BimoState.dizzy
                  ? const Duration(milliseconds: 50)
                  : const Duration(milliseconds: 500),
              curve: Curves.easeOutBack,
              transform: Matrix4.identity()
                ..translate(_faceOffset.dx, _faceOffset.dy)
                ..rotateZ(_headRotation),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  AnimatedOpacity(
                    opacity: _currentState == BimoState.bored ? 1 : 0,
                    duration: const Duration(milliseconds: 300),
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 20),
                      child: Text(
                        _musicNotes[_musicIndex],
                        style: const TextStyle(
                          color: Colors.cyanAccent,
                          fontSize: 45,
                        ),
                      ),
                    ),
                  ),
                  AnimatedOpacity(
                    opacity: _currentState == BimoState.angry ? 1 : 0,
                    duration: const Duration(milliseconds: 200),
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 10, left: 100),
                      child: const Text(
                        '💢',
                        style: TextStyle(fontSize: 40, color: Colors.redAccent),
                      ),
                    ),
                  ),
                  ScaleTransition(
                    scale: _breathingAnimation,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _buildDigitalEye(true),
                        const SizedBox(width: 50),
                        _buildDigitalEye(false),
                      ],
                    ),
                  ),
                  const SizedBox(height: 50),
                  _buildDigitalMouth(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDigitalEye(bool leftEye) {
    double width = 80;
    double height = 100;
    Color eyeColor = Colors.cyanAccent;
    BorderRadius borderRadius = BorderRadius.circular(15);

    switch (_currentState) {
      case BimoState.happy:
        height = 45;
        width = 75;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(50),
          topRight: Radius.circular(50),
          bottomLeft: Radius.circular(5),
          bottomRight: Radius.circular(5),
        );
        eyeColor = Colors.greenAccent;
        break;
      case BimoState.angry:
        height = 40;
        width = 90;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(5),
          topRight: Radius.circular(40),
          bottomLeft: Radius.circular(5),
          bottomRight: Radius.circular(5),
        );
        eyeColor = Colors.redAccent;
        break;
      // 😭 شكل العيون الحزينة (تبكي)
      case BimoState.sad:
        height = 50;
        width = 70;
        borderRadius = const BorderRadius.only(
          topLeft: Radius.circular(40),
          topRight: Radius.circular(40),
          bottomLeft: Radius.circular(10),
          bottomRight: Radius.circular(10),
        );
        eyeColor = Colors.lightBlueAccent;
        break;
      case BimoState.listening:
        width = 90;
        height = 110;
        borderRadius = BorderRadius.circular(40);
        eyeColor = Colors.yellowAccent;
        break;
      case BimoState.dizzy:
        width = 65;
        height = 65;
        borderRadius = BorderRadius.circular(50);
        eyeColor = Colors.purpleAccent;
        break;
      case BimoState.bored:
        width = 70;
        height = 70;
        borderRadius = BorderRadius.circular(50);
        eyeColor = Colors.orangeAccent;
        break;
      case BimoState.idle:
      default:
        break;
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.elasticOut,
      width: width,
      height: _isBlinking && _currentState == BimoState.idle ? 2 : height,
      decoration: BoxDecoration(
        color: eyeColor,
        borderRadius: borderRadius,
        boxShadow: [
          BoxShadow(
            color: eyeColor.withOpacity(0.6),
            blurRadius: 25,
            spreadRadius: 2,
          ),
          BoxShadow(
            color: eyeColor.withOpacity(0.3),
            blurRadius: 50,
            spreadRadius: 10,
          ),
        ],
      ),
      child: Transform.translate(
        offset: Offset(_lookTarget.dx * 0.15, _lookTarget.dy * 0.15),
        child: Center(
          child: Container(
            width: 16,
            height: 16,
            decoration: const BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDigitalMouth() {
    double width = 60;
    double height = 6;
    Color mouthColor = Colors.cyanAccent.withOpacity(0.8);
    BorderRadius mouthRadius = BorderRadius.circular(3);

    if (_currentState == BimoState.happy) {
      width = 50;
      height = 30;
      mouthRadius = const BorderRadius.only(
        bottomLeft: Radius.circular(40),
        bottomRight: Radius.circular(40),
        topLeft: Radius.circular(5),
        topRight: Radius.circular(5),
      );
      mouthColor = Colors.greenAccent;
    } else if (_currentState == BimoState.angry) {
      width = 70;
      height = 6;
      mouthColor = Colors.redAccent;
    } else if (_currentState == BimoState.sad) {
      // 😭 شكل الفم الحزين
      width = 40;
      height = 15;
      mouthRadius = const BorderRadius.only(
        topLeft: Radius.circular(30),
        topRight: Radius.circular(30),
        bottomLeft: Radius.circular(5),
        bottomRight: Radius.circular(5),
      );
      mouthColor = Colors.lightBlueAccent;
    } else if (_currentState == BimoState.listening ||
        _currentState == BimoState.dizzy ||
        _currentState == BimoState.bored) {
      width = 40;
      height = 40;
      mouthRadius = BorderRadius.circular(30);
      mouthColor = _currentState == BimoState.bored
          ? Colors.orangeAccent
          : _currentState == BimoState.listening
          ? Colors.yellowAccent
          : Colors.purpleAccent;
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.elasticOut,
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: mouthColor,
        borderRadius: mouthRadius,
        boxShadow: [
          BoxShadow(color: mouthColor.withOpacity(0.5), blurRadius: 10),
        ],
      ),
    );
  }

  // 🎤 تهيئة نظام الاستماع الدائم
  void _initVoice() async {
    _speechEnabled = await _speechToText.initialize(
      onStatus: (status) {
        // إذا توقف عن الاستماع وكان لا يتحدث، أعد تشغيل الميكروفون بصمت
        if (status == 'notListening' && !_isSpeaking) {
          _startListening();
        }
      },
    );
    await _flutterTts.setLanguage("ar-SA");
    await _flutterTts.setPitch(1.5);

    // تشغيل الميكروفون لأول مرة
    if (_speechEnabled) _startListening();
  }

  Future _speak(String text) async {
    _isSpeaking = true; // نمنعه من الاستماع لنفسه
    await _flutterTts.speak(text);
    _isSpeaking = false;
    _startListening(); // نعود للاستماع بعد انتهاء الكلام
  }

  // 👂 الاستماع المستمر (ينتظر كلمة "بيمو")
  void _startListening() async {
    if (!_speechEnabled || _isSpeaking) return;

    await _speechToText.listen(
      onResult: (result) {
        if (result.finalResult) {
          String words = result.recognizedWords.toLowerCase();

          // 👀 هل نادى اسمي؟ (نظام EMO)
          if (words.contains("بيمو")) {
            _processCommand(words);
          }
        }
      },
      localeId: "ar-SA",
      cancelOnError: true,
      listenMode: ListenMode.dictation, // وضع الإملاء يجعله يستمع لفترة أطول
    );
  }

  // 🧠 إرسال الأوامر للعقل
  Future<void> _processCommand(String command) async {
    _setMood(BimoState.listening);

    try {
      final String serverUrl = 'https://bimo-robot-brain.onrender.com/ask_bimo';

      final visionContext = {
        'is_user_smiling': _isUserSmiling,
        'user_distance': 'close',
      };

      final response = await http.post(
        Uri.parse(serverUrl),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
        body: jsonEncode({'message': command, 'vision': visionContext}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));

        final reply = data['reply'] ?? "حسناً";
        final String aiEmotion = data['emotion'] ?? "idle";

        // 🔥 استقبال كل المشاعر بما فيها الحزن
        BimoState nextMood = BimoState.idle;
        if (aiEmotion == 'happy')
          nextMood = BimoState.happy;
        else if (aiEmotion == 'angry')
          nextMood = BimoState.angry;
        else if (aiEmotion == 'sad')
          nextMood = BimoState.sad; // الشعور الجديد
        else if (aiEmotion == 'dizzy')
          nextMood = BimoState.dizzy;
        else if (aiEmotion == 'bored')
          nextMood = BimoState.bored;

        _setMood(nextMood, durationSeconds: 6);
        _speak(reply);
      } else {
        _speak("عذراً، السيرفر فيه خلل بسيط.");
        _setMood(BimoState.dizzy);
      }
    } catch (e) {
      debugPrint("Network Error: $e");
      _speak("لم أتمكن من الاتصال بالإنترنت.");
      _setMood(BimoState.dizzy);
    }
  }
}
