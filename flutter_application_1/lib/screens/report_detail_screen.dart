import 'package:flutter/material.dart';
import '../main.dart';
import 'login_screen.dart';

class ReportDetailScreen extends StatelessWidget {
  final Map<String, dynamic> reportData;

  const ReportDetailScreen({super.key, required this.reportData});

  @override
  Widget build(BuildContext context) {
    final String reportName = reportData["reportName"] ?? reportData["fileName"] ?? "Çizim Raporu";
    final String emotion = reportData["emotion"] ?? "N/A";
    final confidenceVal = reportData["confidence"];
    final String confidence = confidenceVal is num
        ? "%${confidenceVal.toStringAsFixed(1)}"
        : "%$confidenceVal";

    final rawProbs = reportData["probabilities"] ?? {};
    final Map<String, dynamic> probabilities = Map<String, dynamic>.from(rawProbs);

    final rawWarnings = reportData["warnings"] ?? [];
    final List<String> warnings = List<String>.from(rawWarnings);

    final String psychologicalSummary = reportData["psychologicalSummary"] ?? "";
    final String stylePlacement = reportData["stylePlacement"] ?? "N/A";
    final String styleHierarchy = reportData["styleHierarchy"] ?? "N/A";

    final rawColors = reportData["colors"] ?? [];
    final List<dynamic> colors = List<dynamic>.from(rawColors);

    final rawMovement = reportData["movement"] ?? [];
    final List<dynamic> movement = List<dynamic>.from(rawMovement);

    final int personCount = reportData["personCount"] ?? 0;

    return Scaffold(
      backgroundColor: AppColors.background,

      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,

        title: Text(
          reportName,
          style: const TextStyle(
            color: AppColors.darkText,
            fontWeight: FontWeight.w800,
          ),
        ),

        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: AppColors.primary),
          onPressed: () {
            Navigator.pop(context);
          },
        ),

        actions: [
          TextButton.icon(
            onPressed: () {
              Navigator.pushReplacement(
                context,
                MaterialPageRoute(builder: (context) => const LoginScreen()),
              );
            },
            icon: const Icon(Icons.logout, color: AppColors.primary),
            label: const Text("Çıkış Yap"),
          ),
        ],
      ),

      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          ReportSection(
            title: "Duygu Analizi",
            icon: Icons.psychology_outlined,
            children: <String>[
              "Ana Tahmin: $emotion",
              "Güven: $confidence",
              ...probabilities.entries.map<String>((e) {
                final val = e.value;
                final pct = val is num ? val.toStringAsFixed(1) : val;
                return "${e.key}: %$pct";
              }),
            ],
          ),

          ReportSection(
            title: "Uyarılar",
            icon: Icons.warning_amber_rounded,
            children: warnings.isNotEmpty ? warnings : const ["Herhangi bir uyarı bulunamadı."],
          ),

          ReportSection(
            title: "Psikolojik Senaryo",
            icon: Icons.article_outlined,
            children: psychologicalSummary
                .split(". ")
                .where((String s) => s.trim().isNotEmpty)
                .map<String>((String s) => s.endsWith(".") ? s : "$s.")
                .toList(),
          ),

          ReportSection(
            title: "Kompozisyon ve İlişkiler (KFD)",
            icon: Icons.account_tree_outlined,
            children: <String>[
              "Tespit Edilen Kişi Sayısı: $personCount",
              "Yerleşim: $stylePlacement",
              "Hiyerarşi: $styleHierarchy",
              ...movement.map<String>((m) {
                final pair = m['pair'] ?? [];
                final comment = m['comment'] ?? '';
                final dist = m['distance'];
                final distStr = dist is num ? " (Mesafe: ${dist.toStringAsFixed(2)})" : "";
                return "Figür ${pair.isNotEmpty ? pair[0] : '?'} ↔ Figür ${pair.length > 1 ? pair[1] : '?'}: $comment$distStr";
              }),
            ],
          ),

          ReportSection(
            title: "Renk Analizi",
            icon: Icons.palette_outlined,
            children: colors.map<String>((c) {
              final name = c['name'] ?? '';
              final percent = c['percent'] ?? 0;
              final meaning = c['meaning'] ?? '';
              final pctStr = percent is num ? percent.toStringAsFixed(1) : percent;
              return "$name (%$pctStr): $meaning";
            }).toList(),
          ),
        ],
      ),
    );
  }
}

class ReportSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<String> children;

  const ReportSection({
    super.key,
    required this.title,
    required this.icon,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 18),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppColors.primary, size: 26),
              const SizedBox(width: 10),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: AppColors.darkText,
                ),
              ),
            ],
          ),

          const SizedBox(height: 14),

          ...children.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                "• $item",
                style: const TextStyle(
                  fontSize: 14,
                  height: 1.4,
                  color: AppColors.descriptionText,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
