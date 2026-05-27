import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../main.dart';
import 'report_detail_screen.dart';
import 'login_screen.dart';

class ReportScreen extends StatelessWidget {
  final String userName;

  const ReportScreen({super.key, required this.userName});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,

        title: const Text(
          "Raporlarım",
          style: TextStyle(
            color: AppColors.darkText,
            fontWeight: FontWeight.w800,
          ),
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
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Analiz Raporların",
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: AppColors.darkText,
              ),
            ),

            const SizedBox(height: 8),

            const Text(
              "Yüklediğin resimlere ait analiz sonuçlarını buradan inceleyebilirsin.",
              style: TextStyle(fontSize: 14, color: AppColors.hintText),
            ),

            const SizedBox(height: 24),

            Expanded(
              child: StreamBuilder<QuerySnapshot>(
                stream: FirebaseFirestore.instance
                    .collection('reports')
                    .where('userId', isEqualTo: FirebaseAuth.instance.currentUser?.uid ?? 'anonymous')
                    .snapshots(),
                builder: (context, snapshot) {
                  if (snapshot.hasError) {
                    return Center(
                      child: Text(
                        "Hata oluştu: ${snapshot.error}",
                        style: const TextStyle(color: Colors.red, fontSize: 16),
                      ),
                    );
                  }

                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }

                  if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
                    return const Center(
                      child: Text(
                        "Henüz kayıtlı raporunuz bulunmamaktadır.",
                        style: TextStyle(color: AppColors.hintText, fontSize: 16),
                      ),
                    );
                  }

                  final docs = snapshot.data!.docs;

                  // Sort locally by timestamp descending
                  final sortedDocs = List<QueryDocumentSnapshot>.from(docs);
                  sortedDocs.sort((a, b) {
                    final aData = a.data() as Map<String, dynamic>;
                    final bData = b.data() as Map<String, dynamic>;

                    final aTimestamp = aData['timestamp'] as Timestamp?;
                    final bTimestamp = bData['timestamp'] as Timestamp?;

                    if (aTimestamp == null && bTimestamp == null) return 0;
                    if (aTimestamp == null) return -1; // New documents (null timestamp locally) at the top
                    if (bTimestamp == null) return 1;

                    return bTimestamp.compareTo(aTimestamp);
                  });

                  return ListView.builder(
                    itemCount: sortedDocs.length,
                    itemBuilder: (context, index) {
                      final doc = sortedDocs[index];
                      final report = doc.data() as Map<String, dynamic>;
                      report['id'] = doc.id;

                      final reportName = report["reportName"] ?? report["fileName"] ?? "Çizim Raporu";
                      final emotion = report["emotion"] ?? "N/A";
                      final confidenceVal = report["confidence"];
                      final confidence = confidenceVal is num
                          ? "%${confidenceVal.toStringAsFixed(1)}"
                          : "%$confidenceVal";

                      return InkWell(
                        borderRadius: BorderRadius.circular(22),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) =>
                                  ReportDetailScreen(reportData: report),
                            ),
                          );
                        },
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 14),
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(22),
                            border: Border.all(color: const Color(0xFFE5E7EB)),
                          ),
                          child: Row(
                            children: [
                              Container(
                                width: 56,
                                height: 56,
                                decoration: BoxDecoration(
                                  color: AppColors.softPanel,
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: const Icon(
                                  Icons.description_outlined,
                                  color: AppColors.primary,
                                  size: 30,
                                ),
                              ),

                              const SizedBox(width: 14),

                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      "$reportName",
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w800,
                                        color: AppColors.darkText,
                                      ),
                                    ),
                                    const SizedBox(height: 5),
                                    Text(
                                      "Ana Tahmin: $emotion",
                                      style: const TextStyle(
                                        fontSize: 13.5,
                                        color: AppColors.descriptionText,
                                      ),
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      "Güven: $confidence",
                                      style: const TextStyle(
                                        fontSize: 13,
                                        color: AppColors.hintText,
                                      ),
                                    ),
                                  ],
                                ),
                              ),

                              const Icon(
                                Icons.arrow_forward_ios,
                                color: AppColors.hintText,
                                size: 16,
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
