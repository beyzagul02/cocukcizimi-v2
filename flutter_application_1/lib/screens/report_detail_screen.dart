import 'package:flutter/material.dart';
import '../main.dart';
import 'login_screen.dart';

class ReportDetailScreen extends StatelessWidget {
  final String fileName;

  const ReportDetailScreen({super.key, required this.fileName});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,

      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,

        title: Text(
          "$fileName Raporu",
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
        children: const [
          ReportSection(
            title: "Duygu Analizi",
            icon: Icons.psychology_outlined,
            children: [
              "Ana Tahmin: HAPPY",
              "Güven: %90.5",
              "Happy: %90.5",
              "Sad: %4.5",
              "Angry: %3.9",
              "Fear: %1.1",
            ],
          ),

          ReportSection(
            title: "Uyarılar",
            icon: Icons.warning_amber_rounded,
            children: ["Resimde hiç kişi bulunamadı."],
          ),

          ReportSection(
            title: "Psikolojik Senaryo",
            icon: Icons.article_outlined,
            children: [
              "Çizim genel olarak Happy yani Mutlu kategorisinde değerlendirilmiştir.",
              "Resimde insan figürü tespit edilememiştir.",
              "Bu durum çocuğun insan ilişkilerinden kaçınma eğilimi veya çizim tarzıyla ilgili olabilir.",
              "Renk kullanımı tespit edilen duygu durumuyla uyumludur.",
            ],
          ),

          ReportSection(
            title: "Kompozisyon ve İlişkiler",
            icon: Icons.account_tree_outlined,
            children: ["Yerleşim: N/A", "Hiyerarşi: N/A"],
          ),

          ReportSection(
            title: "Renk Analizi",
            icon: Icons.palette_outlined,
            children: [
              "Yeşil (%75.8): Denge, büyüme, duygusal huzur",
              "Kahverengi (%19.9): Topraklanma, güven arayışı veya katılık",
              "Siyah (%2.3): Endişe, korku, bastırılmış duygular veya güç isteği",
              "Gri (%2.1): Nötr, belirsizlik veya içe kapanma",
            ],
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
