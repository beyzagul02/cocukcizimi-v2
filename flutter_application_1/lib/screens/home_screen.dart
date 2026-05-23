import 'package:flutter/material.dart';
import '../main.dart';
import 'login_screen.dart';
import 'upload_image_screen.dart';
import 'report_screen.dart';
import 'profile_screen.dart';
import 'package:firebase_auth/firebase_auth.dart';

class HomeScreen extends StatelessWidget {
  final String userName;
  final String fullName;
  final String email;
  final String phone;

  const HomeScreen({
    super.key,
    required this.userName,
    required this.fullName,
    required this.email,
    required this.phone,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,

      // ❌ AppBar kaldırıldı
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              /// 🔴 ÜST BAR (artık body içinde)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    "@2026 RGB ürünüdür",
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: AppColors.primary,
                    ),
                  ),

                  TextButton.icon(
                    onPressed: () async {
                      await FirebaseAuth.instance.signOut();

                      if (!context.mounted) return;

                      Navigator.pushAndRemoveUntil(
                        context,
                        MaterialPageRoute(
                          builder: (context) => const LoginScreen(),
                        ),
                        (route) => false,
                      );
                    },
                    icon: const Icon(Icons.logout, color: AppColors.primary),
                    label: const Text("Çıkış Yap"),
                  ),
                ],
              ),

              const SizedBox(height: 12),

              /// 🔵 BAŞLIK
              Text(
                "Merhaba $userName",
                style: Theme.of(context).textTheme.headlineLarge,
              ),

              const SizedBox(height: 20),

              /// 🟡 TANITIM KARTI
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 18,
                ),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(26),
                  border: Border.all(
                    color: AppColors.primary.withOpacity(0.18),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.035),
                      blurRadius: 12,
                      offset: const Offset(0, 5),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Image.asset(
                      "assets/images/homeresim2.png",
                      width: double.infinity,
                      height: 180,
                      fit: BoxFit.contain,
                    ),

                    const SizedBox(height: 12),

                    const Text(
                      "Bizi Anlatan Bir Tanıtım",
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: AppColors.darkText,
                      ),
                    ),

                    const SizedBox(height: 6),

                    const Text(
                      "Çocukların çizimlerinden anlamlı analizler oluşturarak gelişim süreçlerini daha anlaşılır hale getiriyoruz.",
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 13.5,
                        color: AppColors.hintText,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              /// 🔵 İŞLEMLER
              const Text(
                "İşlemler",
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: AppColors.darkText,
                ),
              ),

              const SizedBox(height: 14),

              /// 🔲 GRID
              Expanded(
                child: GridView.count(
                  crossAxisCount: 2,
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                  children: [
                    HomeActionCard(
                      icon: Icons.image_outlined,
                      title: "Resim Yükle",
                      subtitle: "Yeni analiz",
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const UploadImageScreen(),
                          ),
                        );
                      },
                    ),
                    HomeActionCard(
                      icon: Icons.description_outlined,
                      title: "Raporlarım",
                      subtitle: "Geçmiş kayıtlar",
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) =>
                                ReportScreen(userName: userName),
                          ),
                        );
                      },
                    ),
                    HomeActionCard(
                      icon: Icons.trending_up,
                      title: "Gelişim",
                      subtitle: "Süreç takibi",
                      onTap: () {},
                    ),
                    HomeActionCard(
                      icon: Icons.person_outline,
                      title: "Profil",
                      subtitle: "Hesap bilgileri",
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => ProfileScreen(
                              userName: fullName,
                              email: email,
                              phone: phone,
                            ),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 🔲 KART WIDGET
class HomeActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const HomeActionCard({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: const Color(0xFFE5E7EB)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.035),
              blurRadius: 12,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: AppColors.primary, size: 32),
            const SizedBox(height: 12),
            Text(
              title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.darkText,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 13, color: AppColors.hintText),
            ),
          ],
        ),
      ),
    );
  }
}
