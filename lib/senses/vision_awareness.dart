// lib/senses/vision_awareness.dart
// ✅ Lazy Init: الكاميرا "ميتة" حتى تُطلب — تفتح وتغلق في ثوانٍ

import 'package:camera/camera.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'dart:convert';
import 'dart:io';

class VisionAwareness {
  CameraDescription? _frontCamera;
  FaceDetector? _faceDetector;
  bool _disposed = false;
  bool _busy = false; // يمنع استدعائين متزامنين

  Offset lastFaceOffset = Offset.zero;

  // ─────────────────────────────────────────
  // التهيئة: نكتشف الكاميرات فقط — لا نفتح أي stream
  // ─────────────────────────────────────────
  Future<bool> initialize(Function(Face) onFaceDetected) async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        debugPrint('❌ لا توجد كاميرات على هذا الجهاز');
        return false;
      }

      try {
        _frontCamera = cameras.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.front,
        );
      } catch (_) {
        _frontCamera = cameras.first;
      }

      _faceDetector = FaceDetector(
        options: FaceDetectorOptions(
          enableClassification: true,
          performanceMode: FaceDetectorMode.fast,
        ),
      );

      debugPrint('📷 كاميرا جاهزة (مغلقة — Lazy)');
      return true;
    } catch (e) {
      debugPrint('❌ خطأ في اكتشاف الكاميرا: $e');
      return false;
    }
  }

  // ─────────────────────────────────────────
  // التقاط صورة: افتح → صوّر → أغلق
  // ─────────────────────────────────────────
  Future<String?> takeSnapshotBase64() async {
    if (_disposed || _frontCamera == null || _busy) return null;
    _busy = true;

    CameraController? ctrl;
    try {
      debugPrint('📸 فتح الكاميرا...');
      ctrl = CameraController(
        _frontCamera!,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await ctrl.initialize();

      debugPrint('📸 التقاط...');
      final XFile file = await ctrl.takePicture();
      final bytes = await file.readAsBytes();

      try {
        File(file.path).deleteSync();
      } catch (_) {}

      debugPrint('✅ صورة (${bytes.length} bytes)');
      return base64Encode(bytes);
    } catch (e) {
      debugPrint('❌ خطأ في التصوير: $e');
      return null;
    } finally {
      // ✅ أغلق دائماً — سواء نجح أو فشل
      try {
        await ctrl?.dispose();
      } catch (_) {}
      _busy = false;
      debugPrint('📷 الكاميرا مغلقة');
    }
  }

  // ─────────────────────────────────────────
  // مسح سريع للوجه: افتح → قرأ frames → أغلق
  // ─────────────────────────────────────────
  Future<void> quickFaceScan(Function(Offset) onPosition) async {
    if (_disposed || _frontCamera == null || _busy) return;
    _busy = true;

    CameraController? ctrl;
    try {
      ctrl = CameraController(
        _frontCamera!,
        ResolutionPreset.low,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.yuv420,
      );
      await ctrl.initialize();

      int frameCount = 0;
      const maxFrames = 6;
      bool found = false;

      await ctrl.startImageStream((CameraImage image) async {
        if (frameCount >= maxFrames || found) return;
        frameCount++;
        try {
          final inputImage = _buildInputImage(image);
          if (inputImage == null) return;
          final faces = await _faceDetector!.processImage(inputImage);
          if (faces.isNotEmpty && !found) {
            found = true;
            final face = faces.first;
            const w = 320.0, h = 240.0;
            final dx = -((face.boundingBox.center.dx / w) - 0.5) * 120;
            final dy = ((face.boundingBox.center.dy / h) - 0.5) * 80;
            lastFaceOffset = Offset(dx * 0.7, dy * 0.7);
            onPosition(lastFaceOffset);
          }
        } catch (_) {}
      });

      await Future.delayed(const Duration(milliseconds: 1000));
    } catch (e) {
      debugPrint('quickFaceScan error: $e');
    } finally {
      try {
        if (ctrl?.value.isStreamingImages == true) {
          await ctrl?.stopImageStream();
        }
        await ctrl?.dispose();
      } catch (_) {}
      _busy = false;
    }
  }

  InputImage? _buildInputImage(CameraImage image) {
    try {
      final WriteBuffer buf = WriteBuffer();
      for (final p in image.planes) {
        buf.putUint8List(p.bytes);
      }
      return InputImage.fromBytes(
        bytes: buf.done().buffer.asUint8List(),
        metadata: InputImageMetadata(
          size: Size(image.width.toDouble(), image.height.toDouble()),
          rotation: InputImageRotation.rotation270deg,
          format: InputImageFormat.nv21,
          bytesPerRow: image.planes[0].bytesPerRow,
        ),
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> pause() async {}
  Future<void> resume() async {}

  void dispose() {
    _disposed = true;
    _faceDetector?.close();
  }
}
