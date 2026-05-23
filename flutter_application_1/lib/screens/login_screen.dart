import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

import '../main.dart';
import 'home_screen.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final emailController = TextEditingController();
  final passwordController = TextEditingController();

  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  bool isPasswordVisible = false;
  bool isLoading = false;

  String? errorMessage;

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  Future<void> loginUser() async {
    final email = emailController.text.trim();
    final password = passwordController.text;

    setState(() {
      errorMessage = null;
    });

    // 🔴 BOŞ KONTROLLER
    if (email.isEmpty && password.isEmpty) {
      setState(() {
        errorMessage = "Lütfen E-posta ve şifre girin";
      });
      return;
    } else if (email.isEmpty) {
      setState(() {
        errorMessage = "Lütfen E-postanızı giriniz";
      });
      return;
    } else if (password.isEmpty) {
      setState(() {
        errorMessage = "Lütfen Şifrenizi yazınız";
      });
      return;
    }

    try {
      setState(() {
        isLoading = true;
      });

      UserCredential userCredential = await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );

      final uid = userCredential.user!.uid;

      final userDoc = await _firestore.collection("users").doc(uid).get();

      if (!userDoc.exists) {
        throw Exception("Kullanıcı bilgileri bulunamadı");
      }

      final userData = userDoc.data()!;

      final String firstName = userData["firstName"] ?? "Kullanıcı";

      final String fullName =
          userData["name"] ??
          userData["fullName"] ??
          "${userData["firstName"] ?? ""} ${userData["lastName"] ?? ""}".trim();
      final String userEmail = userData["email"] ?? email;
      final String userPhone = userData["phone"] ?? "";

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => HomeScreen(
            userName: firstName,
            fullName: fullName,
            email: userEmail,
            phone: userPhone,
          ),
        ),
      );
    } on FirebaseAuthException {
      if (!mounted) return;

      setState(() {
        errorMessage = "E-posta veya şifre hatalı";
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        errorMessage = "Bir hata oluştu";
      });
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  Future<void> resetPassword() async {
    final email = emailController.text.trim();

    if (email.isEmpty) {
      setState(() {
        errorMessage = "Lütfen e-posta adresinizi yazın";
      });
      return;
    }

    try {
      await _auth.sendPasswordResetEmail(email: email);

      if (!mounted) return;

      setState(() {
        errorMessage = "Şifre sıfırlama bağlantısı e-postanıza gönderildi";
      });
    } on FirebaseAuthException catch (e) {
      String message = "Şifre sıfırlama başarısız";

      if (e.code == "user-not-found") {
        message = "Bu e-posta ile kayıtlı kullanıcı yok";
      } else if (e.code == "invalid-email") {
        message = "Geçersiz e-posta adresi";
      } else if (e.code == "too-many-requests") {
        message = "Çok fazla deneme, sonra tekrar deneyin";
      }

      setState(() {
        errorMessage = message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(
            children: [
              const SizedBox(height: 42),

              Container(
                width: 116,
                height: 116,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(30),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withOpacity(0.12),
                      blurRadius: 25,
                      offset: const Offset(0, 12),
                    ),
                  ],
                ),
                child: Center(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(22),
                    child: Image.asset(
                      "assets/images/logo.png",
                      width: 100,
                      height: 100,
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 26),

              Text("Çizim Analizi", style: textTheme.headlineLarge),

              const SizedBox(height: 8),

              const Text(
                "Çocuk çizimlerini yükle, yapay zeka destekli psikolojik değerlendirme raporunu hızlıca görüntüle, istediğin zaman gelişim durumunu kontrol et.",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 15,
                  color: AppColors.descriptionText,
                  fontStyle: FontStyle.italic,
                ),
              ),

              const SizedBox(height: 38),

              Container(
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                decoration: BoxDecoration(
                  color: AppColors.softPanel,
                  borderRadius: BorderRadius.circular(26),
                ),
                child: Column(
                  children: [
                    TextField(
                      controller: emailController,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(
                        hintText: "E-posta",
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                    ),

                    const SizedBox(height: 12),

                    TextField(
                      controller: passwordController,
                      obscureText: !isPasswordVisible,
                      decoration: InputDecoration(
                        hintText: "Şifre",
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          icon: Icon(
                            isPasswordVisible
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                          onPressed: () {
                            setState(() {
                              isPasswordVisible = !isPasswordVisible;
                            });
                          },
                        ),
                      ),
                    ),

                    // 🔴 HATA MESAJI
                    if (errorMessage != null) ...[
                      const SizedBox(height: 10),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: Colors.red,
                            size: 20,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              errorMessage!,
                              style: const TextStyle(
                                color: Colors.red,
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],

                    const SizedBox(height: 22),

                    SizedBox(
                      width: double.infinity,
                      height: 54,
                      child: ElevatedButton(
                        onPressed: isLoading ? null : loginUser,
                        child: isLoading
                            ? const CircularProgressIndicator(
                                color: Colors.white,
                              )
                            : const Text("Giriş Yap"),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 18),

              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: resetPassword,
                  child: const Text("Şifremi unuttum"),
                ),
              ),

              const SizedBox(height: 24),

              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text("Hesabın yok mu?"),
                  TextButton(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => const RegisterScreen(),
                        ),
                      );
                    },
                    child: const Text("Kayıt Ol"),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
