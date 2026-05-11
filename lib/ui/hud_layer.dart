// lib/ui/hud_layer.dart
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:youtube_player_flutter/youtube_player_flutter.dart';

class HudLayer extends StatefulWidget {
  final String uiAction;
  final String mediaUrl;
  final String imageUrl; // 🔥 أضفنا متغير الصورة
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

class _HudLayerState extends State<HudLayer> {
  YoutubePlayerController? _ytController;

  @override
  void didUpdateWidget(covariant HudLayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.uiAction == 'show_youtube' && widget.mediaUrl.isNotEmpty) {
      if (_ytController == null ||
          _ytController!.initialVideoId != widget.mediaUrl) {
        _ytController?.dispose();
        _ytController = YoutubePlayerController(
          initialVideoId: widget.mediaUrl,
          flags: const YoutubePlayerFlags(autoPlay: true, mute: false),
        );
      }
    } else {
      _ytController?.pause();
    }
  }

  @override
  void dispose() {
    _ytController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.uiAction == 'none' || widget.uiAction.isEmpty) {
      return const SizedBox.shrink();
    }

    return Positioned(
      top: 60,
      right: 20,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 500),
        opacity: 1.0,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
            child: Container(
              width: 220,
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
                    color: widget.glowColor.withOpacity(0.2),
                    blurRadius: 20,
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
        return _buildRichCardWidget(); // 🔥 البطاقة الشاملة
    }
  }

  Widget _buildWeatherWidget() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.cloud_queue, color: Colors.white, size: 50),
        const SizedBox(height: 10),
        Text(
          widget.mediaTitle,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildYoutubeWidget() {
    if (_ytController == null) return const CircularProgressIndicator();
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.play_circle_fill, color: Colors.redAccent, size: 20),
            SizedBox(width: 8),
            Text(
              "YouTube",
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: YoutubePlayer(
            controller: _ytController!,
            showVideoProgressIndicator: true,
          ),
        ),
      ],
    );
  }

  // 🔥 البطاقة الشاملة الجبارة (تعرض صورة حقيقية + رابط)
  Widget _buildRichCardWidget() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Icon(
              widget.imageUrl.isNotEmpty ? Icons.image : Icons.public,
              color: Colors.white,
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
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        // عرض الصورة إذا كانت موجودة
        if (widget.imageUrl.isNotEmpty) ...[
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: Image.network(
              widget.imageUrl,
              height: 110,
              width: double.infinity,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) =>
                  const SizedBox.shrink(), // إخفاء عند الخطأ
            ),
          ),
        ],
        // عرض زر الرابط إذا كان موجوداً
        if (widget.mediaUrl.isNotEmpty) ...[
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: widget.glowColor.withOpacity(0.3),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              onPressed: () async {
                try {
                  await launchUrl(
                    Uri.parse(widget.mediaUrl),
                    mode: LaunchMode.externalApplication,
                  );
                } catch (e) {
                  debugPrint("فشل فتح الرابط: $e");
                }
              },
              icon: const Icon(Icons.open_in_new, size: 16),
              label: const Text("فتح الرابط"),
            ),
          ),
        ],
      ],
    );
  }
}
