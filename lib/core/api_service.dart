// lib/core/api_service.dart
// ✅ 3 سيرفرات منفصلة — كل سيرفر يخدم فص واحد

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';

class ApiService {
  // ─── الفص الأول: الحوار السريع ───
  static const String _chatServer = 'https://bimo-robot-brain.onrender.com';

  // ─── الفص الثاني: الرؤية ───
  static const String _visionServer = 'https://bimo2-ai-server.onrender.com';

  // ─── الفص الثالث: العقل الباطن ───
  static const String _subconsciousServer =
      'https://bimo3-ai-server.onrender.com';

  // ─────────────────────────────────────────
  // الطلب الرئيسي — يوجَّه تلقائياً حسب وجود صورة
  // ─────────────────────────────────────────
  Future<Map<String, dynamic>?> askBimo(
    String userMessage, {
    Map<String, dynamic>? visionData,
    int retries = 2,
  }) async {
    final hasImage = visionData != null && visionData['image'] != null;

    // لو في صورة → سيرفر الرؤية، غير ذلك → سيرفر الحوار
    final url = hasImage ? '$_visionServer/ask_bimo' : '$_chatServer/ask_bimo';

    for (int attempt = 0; attempt <= retries; attempt++) {
      try {
        final response = await http
            .post(
              Uri.parse(url),
              headers: {'Content-Type': 'application/json; charset=UTF-8'},
              body: jsonEncode({
                'message': userMessage,
                'vision': visionData ?? {},
              }),
            )
            .timeout(const Duration(seconds: 20));

        if (response.statusCode == 200) {
          final data = jsonDecode(utf8.decode(response.bodyBytes));
          debugPrint('🤖 [${hasImage ? "Vision" : "Chat"}] $data');
          return _parse(data);
        } else {
          debugPrint('Server error ${response.statusCode}: ${response.body}');
        }
      } catch (e) {
        debugPrint('Attempt $attempt error: $e');
        if (attempt == retries) {
          return {
            'reply': 'معذرة، ما قدرت أتواصل مع عقلي.',
            'emotion': 'sad',
            'face_action': 'none',
          };
        }
        await Future.delayed(Duration(seconds: attempt + 1));
      }
    }
    return null;
  }

  // ─────────────────────────────────────────
  // العقل الباطن — من السيرفر الثالث
  // ─────────────────────────────────────────
  Future<Map<String, dynamic>?> checkSpontaneous() async {
    try {
      final response = await http
          .get(Uri.parse('$_subconsciousServer/spontaneous'))
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data['speak'] == true) return data;
      }
    } catch (_) {}
    return null;
  }

  // ─────────────────────────────────────────
  // Parse آمن
  // ─────────────────────────────────────────
  Map<String, dynamic> _parse(dynamic content) {
    try {
      if (content is Map<String, dynamic>) return content;
      final clean = content
          .toString()
          .replaceAll('```json', '')
          .replaceAll('```', '')
          .trim();
      return jsonDecode(clean);
    } catch (e) {
      debugPrint('Parse error: $e');
      return {
        'reply': content.toString().trim(),
        'emotion': 'idle',
        'face_action': 'none',
      };
    }
  }

  // ─────────────────────────────────────────
  void clearHistory() {
    debugPrint('🌙 السيرفر سيمسح التاريخ عند النوم');
  }
}
