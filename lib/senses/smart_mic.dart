// lib/senses/smart_mic.dart
// ✅ آلة حالة صارمة — فقط صوت حقيقي ≥ 0.8 ثانية يُرسل

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
  Timer? _ampTimer;

  static const double _voiceThreshold = -35.0; // dB — صوت بشري
  static const int _silenceMs = 1500; // صمت قبل الإرسال
  static const int _minSpeechMs = 800; // أقل مدة للكلام المقبول

  static const String _serverUrl =
      'https://bimo-robot-brain.onrender.com/transcribe';

  Future<bool> initialize(Function(String) onResult) async {
    _onResult = onResult;
    if (!await _recorder.hasPermission()) return false;
    _tmpDir = (await getTemporaryDirectory()).path;
    return true;
  }

  void startListening() {
    if (_state == MicState.listening || _state == MicState.pausedByBimo) return;
    _startRecording();
  }

  Future<void> _startRecording() async {
    if (_state == MicState.pausedByBimo) return;
    if (await _recorder.isRecording()) await _recorder.stop();
    await Future.delayed(const Duration(milliseconds: 300));
    if (_state == MicState.pausedByBimo) return;

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
      Future.delayed(const Duration(seconds: 1), _startRecording);
    }
  }

  void _monitor(String filePath) {
    bool userSpoke = false;
    DateTime? speechStart;
    DateTime? silenceStart;

    _ampTimer?.cancel();
    _ampTimer = Timer.periodic(const Duration(milliseconds: 100), (
      timer,
    ) async {
      if (_state != MicState.listening) {
        timer.cancel();
        return;
      }

      try {
        if (!await _recorder.isRecording()) return;
        final amp = await _recorder.getAmplitude();
        final isVoice = amp.current > _voiceThreshold;

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
              debugPrint('⚠️ ضجيج عابر (${speechDur}ms) — تجاهل');
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
    _startRecording();
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
      if (_state != MicState.pausedByBimo) {
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
    _startRecording();
  }

  void _deleteFile(String path) {
    try {
      File(path).deleteSync();
    } catch (_) {}
  }

  void dispose() {
    _state = MicState.off;
    _ampTimer?.cancel();
    _recorder.dispose();
  }
}
