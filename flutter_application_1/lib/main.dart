import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:http/http.dart' as http;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();

  // Uygulama açıldığı an Render sunucusunu arka planda uyandır
  // Await kullanılmıyor ki uygulama açılışı gecikmesin (fire and forget)
  http.get(Uri.parse('https://cocukcizimi-v2.onrender.com/health'))
      .timeout(const Duration(seconds: 5))
      .catchError((_) => http.Response('Error', 500));

  runApp(const MyApp());
}

class AppColors {
  static const Color primary = Color(0xFF7B61FF);
  static const Color background = Color(0xFFFFFCF8);
  static const Color darkText = Color(0xFF1F2937);
  static const Color softPanel = Color(0xFFF4EFFF);
  static const Color hintText = Color(0xFF7C8191);
  static const Color descriptionText = Color.fromARGB(255, 53, 43, 67);
  static const Color greyText = Color(0xFF8A8A8A);
  static const Color borderGrey = Color(0xFF9CA3AF);
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'RGB',
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: AppColors.background,

        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primary,
          primary: AppColors.primary,
        ),

        textTheme: const TextTheme(
          headlineLarge: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w800,
            color: AppColors.darkText,
          ),
          bodyMedium: TextStyle(fontSize: 15, color: AppColors.hintText),
          labelLarge: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),

        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color.fromARGB(255, 54, 36, 143),
            foregroundColor: Colors.white,
            elevation: 0,
            minimumSize: const Size(double.infinity, 54),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(28),
            ),
            textStyle: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),

        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppColors.primary,
            textStyle: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),

        inputDecorationTheme: const InputDecorationTheme(
          prefixIconColor: Color.fromARGB(255, 147, 134, 210),
          suffixIconColor: Color.fromARGB(255, 156, 142, 224),
          hintStyle: TextStyle(color: AppColors.hintText),
          border: UnderlineInputBorder(
            borderSide: BorderSide(color: AppColors.borderGrey),
          ),
          enabledBorder: UnderlineInputBorder(
            borderSide: BorderSide(color: AppColors.borderGrey),
          ),
          focusedBorder: UnderlineInputBorder(
            borderSide: BorderSide(color: AppColors.primary, width: 1.6),
          ),
        ),
      ),
      home: const LoginScreen(),
    );
  }
}
