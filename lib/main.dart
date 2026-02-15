import 'package:flutter/material.dart';
import 'package:flutter/widget_previews.dart';
import 'package:virtual_design/presentation/dashboard/dashboard.dart';
import 'package:get/get.dart';
import 'package:virtual_design/presentation/preview/preview_page.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Virtua Designer',
      theme: ThemeData(primarySwatch: Colors.blue),
      home:  PreviewPage(),
    );
  }
}
