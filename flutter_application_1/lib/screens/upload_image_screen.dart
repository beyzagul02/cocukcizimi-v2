import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../main.dart';
import 'login_screen.dart';
import 'report_detail_screen.dart';

class UploadImageScreen extends StatefulWidget {
  const UploadImageScreen({super.key});

  @override
  State<UploadImageScreen> createState() => _UploadImageScreenState();
}

class _UploadImageScreenState extends State<UploadImageScreen> {
  File? selectedImage;
  bool isLoading = false;

  Future<void> pickImage(ImageSource source) async {
    final picker = ImagePicker();

    final XFile? image = await picker.pickImage(
      source: source,
      imageQuality: 80,
    );

    if (image != null) {
      setState(() {
        selectedImage = File(image.path);
      });
    }
  }

  Future<void> startAnalysis() async {
    if (selectedImage == null) return;

    setState(() {
      isLoading = true;
    });

    try {
      // standard Android emulator uses 10.0.2.2 to connect to local host machine
      String url = "http://10.0.2.2:5000/analyze";
      
      // Fallback for Windows desktop and other non-mobile platforms
      if (Theme.of(context).platform == TargetPlatform.windows || 
          Theme.of(context).platform == TargetPlatform.macOS ||
          Theme.of(context).platform == TargetPlatform.linux) {
        url = "http://localhost:5000/analyze";
      }

      var request = http.MultipartRequest('POST', Uri.parse(url));
      request.files.add(
        await http.MultipartFile.fromPath(
          'image',
          selectedImage!.path,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      print("Analiz isteği gönderiliyor: $url");
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        var data = json.decode(utf8.decode(response.bodyBytes));
        print("Analiz sonucu alındı: $data");

        // Save to Firestore
        final user = FirebaseAuth.instance.currentUser;
        final reportMap = {
          "userId": user?.uid ?? "anonymous",
          "timestamp": FieldValue.serverTimestamp(),
          "fileName": selectedImage!.path.split(Platform.pathSeparator).last,
          "emotion": data["prediction"],
          "confidence": data["confidence"],
          "probabilities": data["probabilities"],
          "psychologicalSummary": data["psychological_summary"],
          "stylePlacement": data["style"]?["placement"] ?? "N/A",
          "styleHierarchy": data["style"]?["hierarchy"] ?? "N/A",
          "warnings": data["warnings"] ?? [],
          "personCount": data["person_count"] ?? 0,
          "colors": data["colors"] ?? [],
          "movement": data["movement"] ?? [],
        };

        // Add to firestore
        var docRef = await FirebaseFirestore.instance.collection("reports").add(reportMap);
        reportMap["id"] = docRef.id;

        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Analiz başarıyla tamamlandı!")),
        );

        // Go to report detail screen
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => ReportDetailScreen(reportData: reportMap),
          ),
        );
      } else {
        var errMessage = "Bir hata oluştu (${response.statusCode})";
        try {
          var errData = json.decode(response.body);
          if (errData["error"] != null) {
            errMessage = errData["error"];
          }
        } catch (_) {}
        throw Exception(errMessage);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Hata: $e")),
      );
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          "Resim Yükle ",
          style: TextStyle(
            fontSize: 25, // 🔥 burayı artır
            fontWeight: FontWeight.bold,
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: AppColors.darkText,
        actions: [
          TextButton.icon(
            onPressed: () {
              Navigator.pushReplacement(
                context,
                MaterialPageRoute(builder: (context) => const LoginScreen()),
              );
            },
            icon: const Icon(Icons.logout, color: AppColors.primary),
            label: const Text(
              "Çıkış Yap",
              style: TextStyle(color: AppColors.primary),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              Container(
                width: double.infinity,
                height: 300,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(26),
                  border: Border.all(
                    color: AppColors.primary.withOpacity(0.22),
                  ),
                ),
                child: selectedImage == null
                    ? const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.image_outlined,
                            size: 76,
                            color: AppColors.primary,
                          ),
                          SizedBox(height: 16),
                          Text(
                            "Henüz resim seçilmedi",
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              color: AppColors.darkText,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            "Galeriden resim yükleyebilir\nveya fotoğraf çekebilirsin.",
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 13.5,
                              color: AppColors.hintText,
                              height: 1.35,
                            ),
                          ),
                        ],
                      )
                    : ClipRRect(
                        borderRadius: BorderRadius.circular(26),
                        child: Image.file(
                          selectedImage!,
                          width: double.infinity,
                          height: double.infinity,
                          fit: BoxFit.cover,
                        ),
                      ),
              ),

              const SizedBox(height: 28),

              UploadOptionCard(
                icon: Icons.photo_library_outlined,
                title: "Galeriden Resim Yükle",
                subtitle: "Telefonundan mevcut bir resim seç",
                onTap: () {
                  pickImage(ImageSource.gallery);
                },
              ),

              const SizedBox(height: 14),

              UploadOptionCard(
                icon: Icons.camera_alt_outlined,
                title: "Fotoğraf Çek",
                subtitle: "Kamera ile yeni bir fotoğraf çek",
                onTap: () {
                  pickImage(ImageSource.camera);
                },
              ),

              const SizedBox(height: 20),

              if (selectedImage != null)
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton.icon(
                    onPressed: isLoading ? null : startAnalysis,
                    icon: isLoading
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Icon(Icons.analytics_outlined),
                    label: Text(
                      isLoading ? "Analiz Ediliyor..." : "Analize Başla",
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class UploadOptionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const UploadOptionCard({
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
        width: double.infinity,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: AppColors.primary.withOpacity(0.16)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.035),
              blurRadius: 12,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 25,
              backgroundColor: AppColors.softPanel,
              child: Icon(icon, color: AppColors.primary, size: 27),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: AppColors.darkText,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 13.5,
                      color: AppColors.hintText,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.hintText),
          ],
        ),
      ),
    );
  }
}
