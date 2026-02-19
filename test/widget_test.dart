// This is a basic Flutter widget test.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Basic widget test', (WidgetTester tester) async {
    // Build a simple widget tree
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Container(
            key: const Key('test-container'),
            child: const Text('Test'),
          ),
        ),
      ),
    );

    // Verify the widget was built
    expect(find.byKey(const Key('test-container')), findsOneWidget);
    expect(find.text('Test'), findsOneWidget);
  });
}
