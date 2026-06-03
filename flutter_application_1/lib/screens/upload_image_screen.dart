import 'dart:io';
import 'dart:convert';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
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
  bool isSuccess = false;
  bool hasError = false;
  String errorMessage = "";

  Future<void> pickImage(ImageSource source) async {
    final picker = ImagePicker();

    final XFile? image = await picker.pickImage(
      source: source,
    );

    if (image != null) {
      setState(() {
        selectedImage = File(image.path);
      });
    }
  }

  Future<void> _showNameInputDialog() async {
    final TextEditingController nameController = TextEditingController();
    String? dialogError;
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              backgroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(22),
              ),
              title: const Text(
                "Rapor Kayıt Adı",
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  color: AppColors.darkText,
                ),
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "Bu analiz raporunu kaydetmek için bir isim belirleyin:",
                    style: TextStyle(fontSize: 14, color: AppColors.hintText),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: nameController,
                    autofocus: true,
                    decoration: const InputDecoration(
                      hintText: "Örn: Ahmet'in Aile Çizimi",
                    ),
                  ),
                  if (dialogError != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      dialogError!,
                      style: const TextStyle(
                        color: Colors.red,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ],
              ),
              actions: <Widget>[
                TextButton(
                  child: const Text("İptal"),
                  onPressed: () {
                    Navigator.of(context).pop();
                  },
                ),
                TextButton(
                  child: const Text("Analiz Et"),
                  onPressed: () {
                    final enteredName = nameController.text.trim();
                    if (enteredName.isNotEmpty) {
                      Navigator.of(context).pop();
                      startAnalysis(enteredName);
                    } else {
                      setState(() {
                        dialogError = "Lütfen geçerli bir isim girin.";
                      });
                    }
                  },
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<String> _resolveServerUrl() async {
    if (kReleaseMode) {
      print("Uygulama release modunda: Doğrudan Render bulut sunucusu seçildi.");
      return "https://cocukcizimi-v2.onrender.com/analyze";
    }

    final candidates = [
      "https://cocukcizimi-v2.onrender.com",
      "http://10.0.2.2:5000",
      "http://localhost:5000",
      "http://172.27.21.21:5000",
      "http://192.168.1.26:5000",
      "http://192.168.1.106:5000",
    ];

    final completer = Completer<String>();
    int failedCount = 0;

    for (var candidate in candidates) {
      final isHttps = candidate.startsWith("https://");
      final timeoutDuration = isHttps ? const Duration(seconds: 75) : const Duration(milliseconds: 1000);

      http.get(Uri.parse(candidate)).timeout(timeoutDuration).then((response) {
        if (!completer.isCompleted) {
          print("Sunucu bulundu ve seçildi: $candidate");
          completer.complete(candidate);
        }
      }).catchError((error) {
        failedCount++;
        if (failedCount == candidates.length && !completer.isCompleted) {
          completer.completeError("Hiçbir sunucuya bağlanılamadı.");
        }
      });
    }

    try {
      final base = await completer.future;
      return "$base/analyze";
    } catch (e) {
      print("Dinamik sunucu tespiti başarısız oldu: $e");
      // Fallback
      return "http://10.0.2.2:5000/analyze";
    }
  }

  Future<void> startAnalysis(String reportName) async {
    if (selectedImage == null) return;

    setState(() {
      isLoading = true;
      isSuccess = false;
      hasError = false;
      errorMessage = "";
    });

    try {
      String url = await _resolveServerUrl();

      var request = http.MultipartRequest('POST', Uri.parse(url));
      request.files.add(
        await http.MultipartFile.fromPath(
          'image',
          selectedImage!.path,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      print("Analiz isteği gönderiliyor: $url");
      var streamedResponse = await request.send().timeout(const Duration(seconds: 75));
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
          "reportName": reportName,
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
        var docRef = await FirebaseFirestore.instance
            .collection("reports")
            .add(reportMap);
        reportMap["id"] = docRef.id;

        if (!mounted) return;

        // Trigger success transition overlay
        setState(() {
          isLoading = false;
          isSuccess = true;
        });

        // 2.4 second playful transition delay
        await Future.delayed(const Duration(milliseconds: 2400));

        if (!mounted) return;

        // Reset success state for next time
        setState(() {
          isSuccess = false;
        });

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
      
      String friendlyMsg = "Sunucuyla veya veritabanıyla bağlantı kurulamadı. Lütfen internet bağlantınızı kontrol edip tekrar deneyin.";
      final errStr = e.toString().toLowerCase();
      if (!errStr.contains("exception") && 
          !errStr.contains("socket") && 
          !errStr.contains("http") && 
          !errStr.contains("connection") && 
          !errStr.contains("database") && 
          !errStr.contains("firebase") && 
          !errStr.contains("firestore") &&
          !errStr.contains("refused") &&
          !errStr.contains("timeout")) {
        friendlyMsg = e.toString().replaceAll("Exception: ", "");
      }

      setState(() {
        isLoading = false;
        isSuccess = false;
        hasError = true;
        errorMessage = friendlyMsg;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Scaffold(
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
                        onPressed: isLoading ? null : _showNameInputDialog,
                        icon: isLoading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
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
        ),
        if (isLoading || isSuccess || hasError)
          Positioned.fill(
            child: Scaffold(
              backgroundColor: Colors.white.withOpacity(0.96),
              body: PlayfulTransitionOverlay(
                isSuccess: isSuccess,
                hasError: hasError,
                errorMessage: errorMessage,
                onClose: () {
                  setState(() {
                    hasError = false;
                  });
                },
              ),
            ),
          ),
      ],
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

class PlayfulTransitionOverlay extends StatefulWidget {
  final bool isSuccess;
  final bool hasError;
  final String errorMessage;
  final VoidCallback? onClose;

  const PlayfulTransitionOverlay({
    super.key,
    required this.isSuccess,
    this.hasError = false,
    this.errorMessage = "",
    this.onClose,
  });

  @override
  State<PlayfulTransitionOverlay> createState() => _PlayfulTransitionOverlayState();
}

class _PlayfulTransitionOverlayState extends State<PlayfulTransitionOverlay> with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _bounceController;
  int _messageIndex = 0;
  Timer? _messageTimer;
  Timer? _noticeTimer;
  bool _showWakeupNotice = false;

  final List<String> _loadingMessages = [
    "Çizimin inceleniyor... 🕵️‍♂️🎨",
    "Renklerin büyüsü taranıyor... 🌈✨",
    "Çizgiler birleştiriliyor... ✏️🧩",
    "Harika bir rapor hazırlanıyor... 📝❤️",
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    )..repeat(reverse: true);

    _bounceController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);

    _messageTimer = Timer.periodic(const Duration(milliseconds: 1800), (timer) {
      if (mounted && !widget.isSuccess) {
        setState(() {
          _messageIndex = (_messageIndex + 1) % _loadingMessages.length;
        });
      }
    });

    _noticeTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) {
        setState(() {
          _showWakeupNotice = true;
        });
      }
    });
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _bounceController.dispose();
    _messageTimer?.cancel();
    _noticeTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    Widget content;
    if (widget.hasError) {
      content = _buildErrorContent();
    } else if (widget.isSuccess) {
      content = _buildSuccessContent();
    } else {
      content = _buildLoadingContent();
    }

    return Container(
      color: Colors.white.withOpacity(0.96),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 500),
            child: content,
          ),
        ),
      ),
    );
  }

  Widget _buildLoadingContent() {
    return Column(
      key: const ValueKey("loading"),
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Playful pulsing illustration
        ScaleTransition(
          scale: Tween<double>(begin: 0.9, end: 1.1).animate(
            CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
          ),
          child: Container(
            width: 140,
            height: 140,
            decoration: BoxDecoration(
              color: AppColors.softPanel,
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.primary.withOpacity(0.3), width: 3),
            ),
            child: const Icon(
              Icons.palette_outlined,
              size: 70,
              color: AppColors.primary,
            ),
          ),
        ),
        const SizedBox(height: 40),
        const CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
          strokeWidth: 4,
        ),
        const SizedBox(height: 32),
        // Playful changing text
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: Text(
            _loadingMessages[_messageIndex],
            key: ValueKey(_messageIndex),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: AppColors.descriptionText,
            ),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          "Yapay zeka çocuğunun dünyasını anlamlandırıyor...",
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 13,
            color: AppColors.hintText,
          ),
        ),
        if (_showWakeupNotice) ...[
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF9C4), // Soft yellow
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFFFF176)),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.hourglass_empty, color: Color(0xFFE65100), size: 18),
                SizedBox(width: 8),
                Flexible(
                  child: Text(
                    "Bulut sunucu uyandırılıyor...\n(İlk kullanımda 1 dk sürebilir)",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFFE65100),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildSuccessContent() {
    return Column(
      key: const ValueKey("success"),
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Bouncing paint brush / checkmark icon
        SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, -0.1),
            end: const Offset(0, 0.1),
          ).animate(
            CurvedAnimation(parent: _bounceController, curve: Curves.easeInOut),
          ),
          child: Container(
            width: 160,
            height: 160,
            decoration: const BoxDecoration(
              color: Color(0xFFE8F5E9), // Light green
              shape: BoxShape.circle,
            ),
            child: const Stack(
              alignment: Alignment.center,
              children: [
                Icon(
                  Icons.auto_awesome,
                  size: 110,
                  color: Color(0x334CAF50), // Subtle star
                ),
                Icon(
                  Icons.draw_outlined,
                  size: 60,
                  color: Color(0xFF4CAF50), // Green brush/draw icon
                ),
                Positioned(
                  bottom: 30,
                  right: 30,
                  child: Icon(
                    Icons.check_circle,
                    size: 40,
                    color: Color(0xFF2E7D32),
                  ),
                )
              ],
            ),
          ),
        ),
        const SizedBox(height: 40),
        const Text(
          "Analiz Hazır! 🎉",
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w900,
            color: Color(0xFF2E7D32),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          "Çizim başarıyla çözümlendi.\nHarika detaylar bulduk! 🎨✨",
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: AppColors.descriptionText,
            height: 1.4,
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          "Rapor yükleniyor...",
          style: TextStyle(
            fontSize: 13,
            fontStyle: FontStyle.italic,
            color: AppColors.hintText,
          ),
        ),
      ],
    );
  }

  Widget _buildErrorContent() {
    return Column(
      key: const ValueKey("error"),
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: 140,
          height: 140,
          decoration: BoxDecoration(
            color: const Color(0xFFFFEBEE), // Soft red
            shape: BoxShape.circle,
            border: Border.all(color: Colors.red.withOpacity(0.3), width: 3),
          ),
          child: const Icon(
            Icons.error_outline_rounded,
            size: 70,
            color: Colors.red,
          ),
        ),
        const SizedBox(height: 40),
        const Text(
          "İşlem Başarısız ⚠️",
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w900,
            color: Colors.red,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          widget.errorMessage,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w500,
            color: AppColors.descriptionText,
            height: 1.4,
          ),
        ),
        const SizedBox(height: 32),
        ElevatedButton(
          onPressed: widget.onClose,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.red,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
          ),
          child: const Text(
            "Ana Menüye Dön",
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }
}
