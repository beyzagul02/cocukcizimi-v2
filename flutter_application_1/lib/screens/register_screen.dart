import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

import '../main.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final TextEditingController firstNameController = TextEditingController();
  final TextEditingController lastNameController = TextEditingController();
  final TextEditingController emailController = TextEditingController();
  final TextEditingController phoneController = TextEditingController();
  final TextEditingController passwordController = TextEditingController();

  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  bool isLoading = false;
  bool obscurePassword = true;

  Future<void> registerUser() async {
    if (firstNameController.text.trim().isEmpty ||
        lastNameController.text.trim().isEmpty ||
        emailController.text.trim().isEmpty ||
        phoneController.text.trim().isEmpty ||
        passwordController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Lütfen tüm alanları doldurun")),
      );
      return;
    }

    try {
      if (!mounted) return;

      setState(() {
        isLoading = true;
      });

      UserCredential userCredential = await _auth
          .createUserWithEmailAndPassword(
            email: emailController.text.trim(),
            password: passwordController.text.trim(),
          );

      String uid = userCredential.user!.uid;

      await _firestore.collection("users").doc(uid).set({
        "firstName": firstNameController.text.trim(),
        "lastName": lastNameController.text.trim(),
        "fullName":
            "${firstNameController.text.trim()} ${lastNameController.text.trim()}",
        "name":
            "${firstNameController.text.trim()} ${lastNameController.text.trim()}",
        "email": emailController.text.trim(),
        "phone": phoneController.text.trim(),
        "createdAt": Timestamp.now(),
      });

      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text("Kayıt başarılı!")));

      Navigator.pop(context);
    } on FirebaseAuthException catch (e) {
      if (!mounted) return;

      String message = "Bir hata oluştu";

      if (e.code == 'email-already-in-use') {
        message = "Bu e-posta zaten kayıtlı";
      } else if (e.code == 'weak-password') {
        message = "Şifre çok zayıf";
      } else if (e.code == 'invalid-email') {
        message = "Geçersiz e-posta adresi";
      } else if (e.code == 'operation-not-allowed') {
        message = "Firebase Authentication içinde Email/Password açık değil";
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text("Hata: $e")));
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  Widget authTextField({
    required TextEditingController controller,
    required String hintText,
    required IconData icon,
    bool obscureText = false,
    Widget? suffixIcon,
    TextInputType keyboardType = TextInputType.text,
  }) {
    return TextField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      style: const TextStyle(
        color: AppColors.darkText,
        fontWeight: FontWeight.w500,
      ),
      decoration: InputDecoration(
        prefixIcon: Icon(icon),
        suffixIcon: suffixIcon,
        hintText: hintText,
      ),
    );
  }

  @override
  void dispose() {
    firstNameController.dispose();
    lastNameController.dispose();
    emailController.dispose();
    phoneController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 26),
          child: Column(
            children: [
              const SizedBox(height: 28),

              Container(
                height: 118,
                width: 118,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(32),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withOpacity(0.08),
                      blurRadius: 28,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Padding(
                  padding: const EdgeInsets.all(15),
                  child: Image.asset("assets/images/logo.png"),
                ),
              ),

              const SizedBox(height: 24),

              Text(
                "Kayıt Ol",
                style: Theme.of(context).textTheme.headlineLarge,
              ),

              const SizedBox(height: 10),

              const Text(
                "Çocuk çizimlerini yüklemek ve yapay zeka destekli gelişim raporlarını takip etmek için hesabını oluştur.",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 15,
                  height: 1.45,
                  fontStyle: FontStyle.italic,
                  color: AppColors.descriptionText,
                ),
              ),

              const SizedBox(height: 30),

              Container(
                padding: const EdgeInsets.fromLTRB(22, 20, 22, 24),
                decoration: BoxDecoration(
                  color: AppColors.softPanel,
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Column(
                  children: [
                    authTextField(
                      controller: firstNameController,
                      hintText: "Ad",
                      icon: Icons.person_outline,
                    ),

                    const SizedBox(height: 14),

                    authTextField(
                      controller: lastNameController,
                      hintText: "Soyad",
                      icon: Icons.badge_outlined,
                    ),

                    const SizedBox(height: 14),

                    authTextField(
                      controller: emailController,
                      hintText: "E-posta",
                      icon: Icons.mail_outline,
                      keyboardType: TextInputType.emailAddress,
                    ),

                    const SizedBox(height: 14),

                    authTextField(
                      controller: phoneController,
                      hintText: "Telefon",
                      icon: Icons.phone_outlined,
                      keyboardType: TextInputType.phone,
                    ),

                    const SizedBox(height: 14),

                    authTextField(
                      controller: passwordController,
                      hintText: "Şifre",
                      icon: Icons.lock_outline,
                      obscureText: obscurePassword,
                      suffixIcon: IconButton(
                        icon: Icon(
                          obscurePassword
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                        ),
                        onPressed: () {
                          setState(() {
                            obscurePassword = !obscurePassword;
                          });
                        },
                      ),
                    ),

                    const SizedBox(height: 26),

                    ElevatedButton(
                      onPressed: isLoading ? null : registerUser,
                      child: isLoading
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.5,
                                color: Colors.white,
                              ),
                            )
                          : const Text("Kayıt Ol"),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    "Zaten hesabın var mı?",
                    style: TextStyle(color: AppColors.greyText, fontSize: 15),
                  ),
                  TextButton(
                    onPressed: () {
                      Navigator.pop(context);
                    },
                    child: const Text("Giriş Yap"),
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
