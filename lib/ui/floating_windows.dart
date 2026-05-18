// lib/ui/floating_windows.dart
// 🪟 مدير النوافذ العائمة القابلة للسحب

import 'dart:ui';
import 'package:flutter/material.dart';

// نموذج بيانات النافذة
class FloatWindow {
  final String id;
  final String title;
  final String content;
  double x;
  double y;

  FloatWindow({
    required this.id,
    required this.title,
    required this.content,
    required this.x,
    required this.y,
  });
}

class FloatingWindowManager extends StatefulWidget {
  final List<FloatWindow> windows;
  final Color glowColor;
  final Function(String) onClose;

  const FloatingWindowManager({
    super.key,
    required this.windows,
    required this.glowColor,
    required this.onClose,
  });

  @override
  State<FloatingWindowManager> createState() => _FloatingWindowManagerState();
}

class _FloatingWindowManagerState extends State<FloatingWindowManager> {
  @override
  Widget build(BuildContext context) {
    if (widget.windows.isEmpty) return const SizedBox.shrink();

    return Stack(
      children: widget.windows.map((win) {
        return Positioned(
          left: win.x,
          top: win.y,
          child: GestureDetector(
            onPanUpdate: (details) {
              // تحديث الإحداثيات عند السحب
              setState(() {
                win.x += details.delta.dx;
                win.y += details.delta.dy;
              });
            },
            child: _buildWindow(win),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildWindow(FloatWindow win) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          width: 220,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: widget.glowColor.withOpacity(0.3),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: widget.glowColor.withOpacity(0.1),
                blurRadius: 20,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      win.title,
                      style: TextStyle(
                        color: widget.glowColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  GestureDetector(
                    onTap: () => widget.onClose(win.id),
                    child: const Icon(
                      Icons.close,
                      color: Colors.white54,
                      size: 18,
                    ),
                  ),
                ],
              ),
              const Divider(color: Colors.white24),
              Text(
                win.content,
                style: const TextStyle(color: Colors.white, fontSize: 13),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
