// lib/ui/hud_layer.dart
// ✅ إصلاح: الصور + الروابط + نافذة طقس متحركة + يوتيوب مدمج

import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:youtube_player_flutter/youtube_player_flutter.dart';

class HudLayer extends StatefulWidget {
  final String uiAction;
  final String mediaUrl;
  final String imageUrl;
  final String mediaTitle;
  final Color glowColor;

  const HudLayer({
    super.key,
    required this.uiAction,
    required this.mediaUrl,
    required this.imageUrl,
    required this.mediaTitle,
    required this.glowColor,
  });

  @override
  State<HudLayer> createState() => _HudLayerState();
}

class _HudLayerState extends State<HudLayer>
    with SingleTickerProviderStateMixin {
  YoutubePlayerController? _ytController;
  late AnimationController _cloudCtrl;
  late Animation<double> _cloudAnim;

  @override
  void initState() {
    super.initState();
    // أنيميشن الغيوم للطقس
    _cloudCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat(reverse: true);
    _cloudAnim = Tween<double>(
      begin: -8,
      end: 8,
    ).animate(CurvedAnimation(parent: _cloudCtrl, curve: Curves.easeInOut));
  }

  @override
  void didUpdateWidget(covariant HudLayer oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (widget.uiAction == 'show_youtube' && widget.mediaUrl.isNotEmpty) {
      // استخرج الـ video ID لو وصل كـ URL كامل
      final videoId = _extractVideoId(widget.mediaUrl);
      if (_ytController == null || _ytController!.initialVideoId != videoId) {
        _ytController?.dispose();
        _ytController = YoutubePlayerController(
          initialVideoId: videoId,
          flags: const YoutubePlayerFlags(
            autoPlay: true,
            mute: false,
            disableDragSeek: false,
          ),
        );
      }
    } else {
      _ytController?.pause();
    }
  }

  // ─── استخراج معرف الفيديو من أي صيغة ───
  String _extractVideoId(String input) {
    // لو كان معرف مباشر (11 حرف)
    if (input.length == 11 && !input.contains('/')) return input;

    // لو كان رابط كامل
    final uri = Uri.tryParse(input);
    if (uri != null) {
      if (uri.queryParameters.containsKey('v')) {
        return uri.queryParameters['v']!;
      }
      final segments = uri.pathSegments;
      if (segments.isNotEmpty) return segments.last;
    }
    return input;
  }

  @override
  void dispose() {
    _ytController?.dispose();
    _cloudCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.uiAction == 'none' || widget.uiAction.isEmpty) {
      return const SizedBox.shrink();
    }

    return Positioned(
      top: 60,
      right: 16,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 500),
        opacity: 1.0,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
            child: Container(
              width: widget.uiAction == 'show_youtube' ? 260 : 220,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: widget.glowColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: widget.glowColor.withOpacity(0.5),
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: widget.glowColor.withOpacity(0.25),
                    blurRadius: 24,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: _buildContent(),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildContent() {
    switch (widget.uiAction) {
      case 'show_weather':
        return _buildWeatherWidget();
      case 'show_youtube':
        return _buildYoutubeWidget();
      case 'show_card':
      default:
        return _buildRichCardWidget();
    }
  }

  // ─────────────── نافذة الطقس الذكية ───────────────
  Widget _buildWeatherWidget() {
    // استخراج بيانات الطقس من العنوان (مثال: "الرياض ☀️ 32°C")
    final parts = widget.mediaTitle.split('|');
    final cityLine = parts.isNotEmpty ? parts[0].trim() : widget.mediaTitle;
    final detailLine = parts.length > 1 ? parts[1].trim() : '';

    // تحديد الأيقونة والألوان حسب الطقس
    IconData weatherIcon = Icons.wb_sunny_rounded;
    Color skyColor = const Color(0xFF1E90FF);
    Color iconColor = Colors.amberAccent;

    final lower = widget.mediaTitle.toLowerCase();
    if (lower.contains('cloud') ||
        lower.contains('غائم') ||
        lower.contains('غيوم')) {
      weatherIcon = Icons.cloud_rounded;
      skyColor = const Color(0xFF607D8B);
      iconColor = Colors.white70;
    } else if (lower.contains('rain') || lower.contains('مطر')) {
      weatherIcon = Icons.grain_rounded;
      skyColor = const Color(0xFF37474F);
      iconColor = Colors.lightBlueAccent;
    } else if (lower.contains('thunder') ||
        lower.contains('عاصفة') ||
        lower.contains('رعد')) {
      weatherIcon = Icons.thunderstorm_rounded;
      skyColor = const Color(0xFF263238);
      iconColor = Colors.yellowAccent;
    } else if (lower.contains('snow') || lower.contains('ثلج')) {
      weatherIcon = Icons.ac_unit_rounded;
      skyColor = const Color(0xFFB0BEC5);
      iconColor = Colors.white;
    }

    return AnimatedBuilder(
      animation: _cloudAnim,
      builder: (ctx, child) {
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [skyColor.withOpacity(0.8), Colors.black54],
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // الغيمة / الشمس المتحركة
              Transform.translate(
                offset: Offset(_cloudAnim.value, 0),
                child: Icon(
                  weatherIcon,
                  color: iconColor,
                  size: 52,
                  shadows: [
                    Shadow(color: iconColor.withOpacity(0.7), blurRadius: 20),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              Text(
                cityLine,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              if (detailLine.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  detailLine,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.8),
                    fontSize: 13,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  // ─────────────── نافذة يوتيوب المدمجة ───────────────
  Widget _buildYoutubeWidget() {
    if (_ytController == null) {
      return const SizedBox(
        height: 80,
        child: Center(
          child: CircularProgressIndicator(color: Colors.redAccent),
        ),
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // عنوان يوتيوب
        Row(
          children: [
            const Icon(
              Icons.play_circle_fill,
              color: Colors.redAccent,
              size: 18,
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                widget.mediaTitle.isNotEmpty
                    ? widget.mediaTitle
                    : "جاري التشغيل...",
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        // مشغل اليوتيوب الفعلي
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: YoutubePlayer(
            controller: _ytController!,
            showVideoProgressIndicator: true,
            progressIndicatorColor: Colors.redAccent,
            progressColors: const ProgressBarColors(
              playedColor: Colors.red,
              handleColor: Colors.redAccent,
            ),
            onReady: () {
              _ytController!.play();
            },
          ),
        ),
      ],
    );
  }

  // ─────────────── البطاقة الغنية (مع إصلاح الصور والروابط) ───────────────
  Widget _buildRichCardWidget() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // ─── العنوان ───
        Row(
          children: [
            Icon(
              widget.imageUrl.isNotEmpty
                  ? Icons.image_rounded
                  : Icons.public_rounded,
              color: widget.glowColor,
              size: 16,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                widget.mediaTitle.isNotEmpty
                    ? widget.mediaTitle
                    : "نتيجة البحث",
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),

        // ─── الصورة (مع إصلاح التحميل) ───
        if (widget.imageUrl.isNotEmpty) ...[
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: Image.network(
              widget.imageUrl,
              height: 120,
              width: double.infinity,
              fit: BoxFit.cover,
              // ✅ إصلاح: headers لبعض المواقع التي تحتاج User-Agent
              headers: const {
                'User-Agent':
                    'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
              },
              loadingBuilder: (ctx, child, loadingProgress) {
                if (loadingProgress == null) return child;
                return Container(
                  height: 120,
                  color: Colors.white12,
                  child: Center(
                    child: CircularProgressIndicator(
                      value: loadingProgress.expectedTotalBytes != null
                          ? loadingProgress.cumulativeBytesLoaded /
                                loadingProgress.expectedTotalBytes!
                          : null,
                      color: widget.glowColor,
                      strokeWidth: 2,
                    ),
                  ),
                );
              },
              errorBuilder: (ctx, err, stack) {
                debugPrint('❌ فشل تحميل الصورة: $err');
                return Container(
                  height: 60,
                  decoration: BoxDecoration(
                    color: Colors.white10,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.broken_image_rounded,
                        color: widget.glowColor.withOpacity(0.5),
                        size: 20,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'الصورة غير متاحة',
                        style: TextStyle(color: Colors.white38, fontSize: 11),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],

        // ─── زر الرابط (مع إصلاح الفتح) ───
        if (widget.mediaUrl.isNotEmpty) ...[
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: widget.glowColor.withOpacity(0.25),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                  side: BorderSide(
                    color: widget.glowColor.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                padding: const EdgeInsets.symmetric(vertical: 8),
              ),
              onPressed: () => _openUrl(widget.mediaUrl),
              icon: const Icon(Icons.open_in_new_rounded, size: 15),
              label: const Text("فتح الرابط", style: TextStyle(fontSize: 13)),
            ),
          ),
        ],
      ],
    );
  }

  // ✅ إصلاح جذري لفتح الروابط
  Future<void> _openUrl(String rawUrl) async {
    // تنظيف الرابط وإضافة https لو ناقص
    String cleaned = rawUrl.trim();
    if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://')) {
      cleaned = 'https://$cleaned';
    }

    final uri = Uri.tryParse(cleaned);
    if (uri == null) {
      debugPrint('❌ رابط غير صالح: $rawUrl');
      return;
    }

    debugPrint('🔗 فتح الرابط: $uri');

    try {
      // الطريقة الأولى: فتح في المتصفح الخارجي مباشرة
      final launched = await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );
      if (!launched) {
        // الطريقة الثانية: محاولة بـ inAppWebView
        await launchUrl(uri, mode: LaunchMode.inAppWebView);
      }
    } catch (e) {
      debugPrint('❌ فشل فتح الرابط: $e');
      // الطريقة الأخيرة: platformDefault
      try {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      } catch (e2) {
        debugPrint('❌ فشل نهائي: $e2');
      }
    }
  }
}
