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

enum BimoState { idle, happy, angry, listening, dizzy, bored }

class BimoProFace extends StatefulWidget {
  const BimoProFace({super.key});

  @override
  State<BimoProFace> createState() => _BimoProFaceState();
}

class _BimoProFaceState extends State<BimoProFace>
    with TickerProviderStateMixin {
  late AnimationController _breathingController;
  late Animation<double> _breathingAnimation;
  bool _isUserSmiling = false; // 👀 متغير الوعي البصري
  bool _isBlinking = false;
  BimoState _currentState = BimoState.idle;

  Timer? _moodTimer;
  Timer? _roamingTimer;
  Timer? _shakeTimer;
  Timer? _idleTimer;

  final Random _random = Random();

  final SpeechToText _speechToText = SpeechToText();
  final FlutterTts _flutterTts = FlutterTts();
  bool _speechEnabled = false;
  String _lastWords = "";

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
      // إعداد كاشف الوجوه
      _faceDetector = FaceDetector(
        options: FaceDetectorOptions(
          enableTracking: true,
          enableClassification:
              true, // 🔥 هذا السطر الجديد ليعرف إذا كنت تبتسم!
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
      for (final Plane plane in image.planes) {
        allBytes.putUint8List(plane.bytes);
      }
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
      final inputImage = InputImage.fromBytes(bytes: bytes, metadata: metadata);
      final faces = await _faceDetector!.processImage(inputImage);

      if (faces.isNotEmpty && mounted && _currentState == BimoState.idle) {
        final face = faces.first;

        // 👀 استخراج الوعي البصري (هل إلياس يبتسم؟)
        if (face.smilingProbability != null) {
          _isUserSmiling = face.smilingProbability! > 0.6;
        }

        final centerX = face.boundingBox.center.dx;
        // ... باقي الكود كما هو

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
      debugPrint("خطأ في الرؤية: $e");
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
        setState(() {
          _faceOffset = Offset(
            _random.nextDouble() * 20 - 10,
            _random.nextDouble() * 20 - 10,
          );
        });
      }
    });
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

  void _trackTouch(Offset localPos, Size screenSize) {
    final dx = ((localPos.dx - screenSize.width / 2) / screenSize.width) * 120;
    final dy = ((localPos.dy - screenSize.height / 2) / screenSize.height) * 80;
    setState(() {
      _lookTarget = Offset(dx, dy);
      _faceOffset = Offset(dx * 0.6, dy * 0.6);
    });
    _resetIdleTimer();
  }

  void _setMood(BimoState newState, {int durationSeconds = 4}) {
    setState(() {
      _currentState = newState;
      _shakeOffset = 0;
      _headRotation = 0;

      if (newState == BimoState.listening) {
        _faceOffset = const Offset(50, 0);
        Future.delayed(const Duration(milliseconds: 500), () {
          if (_currentState == BimoState.listening) {
            setState(() => _faceOffset = const Offset(-50, 0));
          }
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

  void _startDizzy() {
    if (_currentState == BimoState.dizzy) return;
    setState(() => _currentState = BimoState.dizzy);
    _shakeTimer?.cancel();
    _shakeTimer = Timer.periodic(const Duration(milliseconds: 50), (timer) {
      setState(() {
        _shakeOffset = _shakeOffset == 15 ? -15 : 15;
        _faceOffset = Offset(_shakeOffset, _random.nextDouble() * 10 - 5);
      });
    });
    _resetIdleTimer();
  }

  void _stopDizzy() {
    _shakeTimer?.cancel();
    _setMood(BimoState.angry);
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        onTapDown: (details) {
          _trackTouch(details.localPosition, screenSize);
          _startListening();
        },
        onLongPress: () => _setMood(BimoState.happy),
        onDoubleTap: () => _setMood(BimoState.angry),
        onPanUpdate: (details) {
          _trackTouch(details.localPosition, screenSize);
          _startDizzy();
        },
        onPanEnd: (details) => _stopDizzy(),
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

  void _initVoice() async {
    _speechEnabled = await _speechToText.initialize();
    await _flutterTts.setLanguage("ar-SA");
    await _flutterTts.setPitch(1.5);
    setState(() {});
  }

  Future _speak(String text) async {
    await _flutterTts.speak(text);
  }

  // 🚀 التحديث الأسطوري: إجبار الاستماع باللغة العربية بحساسية عالية
  void _startListening() async {
    _flutterTts.stop(); // إيقاف كلام بيمو إذا أردت مقاطعته
    _setMood(BimoState.listening);

    await _speechToText.listen(
      onResult: (result) {
        setState(() {
          _lastWords = result.recognizedWords;
          // ننتظر حتى يتأكد النظام أنك أنهيت الجملة
          if (result.finalResult && _lastWords.isNotEmpty) {
            _processCommand(_lastWords);
          }
        });
      },
      localeId: "ar-SA", // السر هنا: إجباره على فهم العربية بوضوح
      cancelOnError: true,
      listenMode: ListenMode.confirmation,
    );
  }

  // 🧠 التحديث الأسطوري 2: ربط العقل بالمشاعر والوعي البصري!
  Future<void> _processCommand(String command) async {
    _setMood(BimoState.listening);

    try {
      final String serverUrl = 'https://bimo-robot-brain.onrender.com/ask_bimo';

      // 👀 1. تجهيز بيانات الرؤية لإرسالها للعقل
      final visionContext = {
        'is_user_smiling':
            _isUserSmiling, // المتغير الذي يحدد هل أنت تبتسم أم لا
        'user_distance': 'close',
      };

      final response = await http.post(
        Uri.parse(serverUrl),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
        // 🔥 2. هنا التغيير الأهم: نرسل الرسالة + الرؤية معاً
        body: jsonEncode({'message': command, 'vision': visionContext}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));

        // استخراج الكلام
        final reply = data['reply'] ?? "حسناً";
        // استخراج الشعور الذي قرره الذكاء الاصطناعي
        final String aiEmotion = data['emotion'] ?? "idle";

        // تحويل النص القادم من البايثون إلى حالة بيمو الفعلية
        BimoState nextMood = BimoState.idle;
        if (aiEmotion == 'happy') {
          nextMood = BimoState.happy;
        } else if (aiEmotion == 'angry') {
          nextMood = BimoState.angry;
        } else if (aiEmotion == 'dizzy') {
          nextMood = BimoState.dizzy;
        } else if (aiEmotion == 'bored') {
          nextMood = BimoState.bored;
        }

        _setMood(
          nextMood,
          durationSeconds: 6,
        ); // يبقى على هذا الشعور لـ 6 ثوانٍ

        _speak(reply);
      } else {
        _speak("عذراً، السيرفر فيه خلل بسيط.");
        _setMood(BimoState.dizzy);
      }
    } catch (e) {
      debugPrint("Network Error: $e");
      _speak("لم أتمكن من الاتصال بالإنترنت يا مهندسي العزيز.");
      _setMood(BimoState.dizzy);
    }
  }
}
