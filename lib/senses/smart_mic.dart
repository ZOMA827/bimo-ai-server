// lib/senses/smart_mic.dart
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:http/http.dart' as http;

enum MicState { off, listening, processing, pausedByBimo }

class SmartMic {
  final AudioRecorder _recorder = AudioRecorder();
  MicState _state = MicState.off;
  String? _tmpDir;
  int _counter = 0;
  Function(String)? _onResult;
  Function()? _onLoudNoise; // 🔥 دالة جديدة للتصفيق
  Timer? _ampTimer;

  bool _isAllowedToListen = false;

  static const double _voiceThreshold = -35.0;
  static const int _silenceMs = 1500;
  static const int _minSpeechMs = 800;

  double _lastAmp = -50.0; // 🔥 لتتبع الموجة الصوتية السابقة
  DateTime _lastNoiseTime = DateTime.now(); // 🔥 لمنع التكرار المزعج

  static const String _serverUrl =
      'https://bimo-robot-brain.onrender.com/transcribe';

  // 🔥 تحديث دالة التهيئة لاستقبال حدث الضجيج
  Future<bool> initialize(
    Function(String) onResult, {
    Function()? onLoudNoise,
  }) async {
    _onResult = onResult;
    _onLoudNoise = onLoudNoise;
    if (!await _recorder.hasPermission()) return false;
    _tmpDir = (await getTemporaryDirectory()).path;
    return true;
  }

  void startListening() {
    _isAllowedToListen = true;
    if (_state == MicState.listening || _state == MicState.pausedByBimo) return;
    _startRecording();
  }

  Future<void> _startRecording() async {
    if (!_isAllowedToListen || _state == MicState.pausedByBimo) return;
    if (await _recorder.isRecording()) await _recorder.stop();
    await Future.delayed(const Duration(milliseconds: 300));
    if (_state == MicState.pausedByBimo || !_isAllowedToListen) return;

    _state = MicState.listening;
    _counter++;
    final path = '$_tmpDir/bimo_$_counter.m4a';

    try {
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.aacLc,
          bitRate: 64000,
          sampleRate: 16000,
        ),
        path: path,
      );
      _monitor(path);
    } catch (e) {
      debugPrint('❌ Mic: $e');
      _state = MicState.off;
      if (_isAllowedToListen) {
        Future.delayed(const Duration(seconds: 1), _startRecording);
      }
    }
  }

  void _monitor(String filePath) {
    bool userSpoke = false;
    DateTime? speechStart;
    DateTime? silenceStart;
    _lastAmp = -50.0; // تصفير الموجة

    _ampTimer?.cancel();
    _ampTimer = Timer.periodic(const Duration(milliseconds: 100), (
      timer,
    ) async {
      if (_state != MicState.listening || !_isAllowedToListen) {
        timer.cancel();
        return;
      }

      try {
        if (!await _recorder.isRecording()) return;
        final amp = await _recorder.getAmplitude();
        final currentAmp = amp.current;

        // 🔥 خوارزمية كشف التصفيق أو الضحك العالي (قفزة مفاجئة في الصوت)
        if (currentAmp > -10.0 && (currentAmp - _lastAmp) > 20.0) {
          if (DateTime.now().difference(_lastNoiseTime).inSeconds > 3) {
            _lastNoiseTime = DateTime.now();
            _onLoudNoise?.call(); // إطلاق حدث التصفيق!
          }
        }
        _lastAmp = currentAmp;

        final isVoice = currentAmp > _voiceThreshold;

        if (isVoice) {
          speechStart ??= DateTime.now();
          userSpoke = true;
          silenceStart = null;
        } else if (userSpoke) {
          silenceStart ??= DateTime.now();
          if (DateTime.now().difference(silenceStart!).inMilliseconds >=
              _silenceMs) {
            final speechDur = silenceStart!
                .difference(speechStart!)
                .inMilliseconds;
            timer.cancel();
            if (speechDur >= _minSpeechMs) {
              _processAndSend(filePath);
            } else {
              _discardAndRestart(filePath);
            }
          }
        }
      } catch (_) {}
    });
  }

  Future<void> _discardAndRestart(String path) async {
    if (_state != MicState.listening) return;
    try {
      await _recorder.stop();
    } catch (_) {}
    _deleteFile(path);
    _state = MicState.off;
    if (_isAllowedToListen) _startRecording();
  }

  Future<void> _processAndSend(String filePath) async {
    if (_state != MicState.listening) return;
    _state = MicState.processing;
    try {
      await _recorder.stop();
      final req = http.MultipartRequest('POST', Uri.parse(_serverUrl));
      req.files.add(await http.MultipartFile.fromPath('file', filePath));
      final res = await req.send().timeout(const Duration(seconds: 15));
      final body = await res.stream.bytesToString();

      if (res.statusCode == 200) {
        final text = (jsonDecode(body)['text'] as String?)?.trim() ?? '';
        if (text.isNotEmpty) _onResult?.call(text);
      }
    } catch (e) {
      debugPrint('❌ إرسال: $e');
    } finally {
      _deleteFile(filePath);
      if (_state != MicState.pausedByBimo && _isAllowedToListen) {
        _state = MicState.off;
        _startRecording();
      }
    }
  }

  void pauseForSpeaking() async {
    _state = MicState.pausedByBimo;
    _ampTimer?.cancel();
    try {
      if (await _recorder.isRecording()) await _recorder.stop();
    } catch (_) {}
  }

  void resumeAfterSpeaking() {
    if (_state != MicState.pausedByBimo) return;
    _state = MicState.off;
    if (_isAllowedToListen) _startRecording();
  }

  void stopListening() async {
    _isAllowedToListen = false;
    _state = MicState.off;
    _ampTimer?.cancel();
    try {
      if (await _recorder.isRecording()) await _recorder.stop();
    } catch (_) {}
  }

  void _deleteFile(String path) {
    try {
      File(path).deleteSync();
    } catch (_) {}
  }

  void dispose() {
    _isAllowedToListen = false;
    _state = MicState.off;
    _ampTimer?.cancel();
    _recorder.dispose();
  }
}
