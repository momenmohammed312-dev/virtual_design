import 'dart:io';
import 'package:image/image.dart' as img;

// Note: Add 'image: ^4.1.4' to pubspec.yaml dependencies

/// Utility for normalizing images to a consistent format before processing.
/// This ensures compatibility with the print processor and prevents
/// "Invalid Image Format" errors.
class ImageProcessor {
  /// Supported file extensions
  static const List<String> supported = [
    'png',
    'jpg',
    'jpeg',
    'tiff',
    'tif',
    'bmp',
    'webp',
  ];

  /// Check if a file path has a supported extension
  static bool isSupported(String filePath) {
    final ext = filePath.split('.').last.toLowerCase();
    return supported.contains(ext);
  }

  /// Normalize any supported image format to PNG.
  /// This decodes the image using the appropriate decoder and re-encodes as PNG.
  /// Returns the path to the temporary normalized PNG file.
  ///
  /// Throws [Exception] if the image cannot be decoded.
  static Future<String> normalizeImage(String filePath) async {
    if (!isSupported(filePath)) {
      final ext = filePath.split('.').last.toLowerCase();
      if (ext == 'png') {
        return filePath;
      }
      if (!isSupported(filePath)) {
        throw Exception('Unsupported image format: .$ext');
      }
    }

    final bytes = await File(filePath).readAsBytes();
    img.Image? decoded;

    // Try generic decoder first (handles PNG, JPG, GIF, etc.)
    decoded = img.decodeImage(bytes);

    // If generic decoder fails, try format-specific decoders
    if (decoded == null) {
      final ext = filePath.split('.').last.toLowerCase();

      if (ext == 'tiff' || ext == 'tif') {
        decoded = img.decodeTiff(bytes);
      } else if (ext == 'bmp') {
        decoded = img.decodeBmp(bytes);
      } else if (ext == 'png') {
        decoded = img.decodePng(bytes);
      } else if (ext == 'jpg' || ext == 'jpeg') {
        decoded = img.decodeJpg(bytes);
      } else if (ext == 'webp') {
        // WebP support may require additional package
        // For now, try generic decoder again or skip
        decoded = img.decodeImage(bytes); // retry
      }
    }

    if (decoded == null) {
      throw Exception('Could not decode image: $filePath');
    }

    print(
      'Original image channels: ${decoded.numChannels}, width: ${decoded.width}, height: ${decoded.height}',
    );

    // Convert to RGB to remove alpha channel for better compatibility
    img.Image rgbImage = decoded;
    if (decoded.numChannels > 3) {
      print('Converting to RGB...');
      rgbImage = img.Image(width: decoded.width, height: decoded.height);
      for (int y = 0; y < decoded.height; y++) {
        for (int x = 0; x < decoded.width; x++) {
          final pixel = decoded.getPixel(x, y);
          final a = pixel.a;
          final r = a == 0 ? 0 : (pixel.r * 255) ~/ a;
          final g = a == 0 ? 0 : (pixel.g * 255) ~/ a;
          final b = a == 0 ? 0 : (pixel.b * 255) ~/ a;
          rgbImage.setPixel(x, y, img.ColorRgb8(r, g, b));
        }
      }
      print('Converted to RGB, channels: ${rgbImage.numChannels}');
    }

    // Create temporary PNG file
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final tmpPath = '${Directory.systemTemp.path}/vd_normalized_$timestamp.png';
    final tmpFile = File(tmpPath);

    // Encode as PNG (lossless, widely supported)
    final pngBytes = img.encodePng(rgbImage);
    await tmpFile.writeAsBytes(pngBytes);

    print(
      'Normalized image saved to: $tmpPath, size: ${pngBytes.length} bytes',
    );

    return tmpPath;
  }

  /// Clean up temporary normalized files (call after processing is complete)
  static Future<void> cleanupTempFile(String tempPath) async {
    try {
      final file = File(tempPath);
      if (await file.exists()) {
        await file.delete();
      }
    } catch (e) {
      // Log but don't throw - cleanup is best effort
      print('Warning: Could not delete temp file $tempPath: $e');
    }
  }
}
