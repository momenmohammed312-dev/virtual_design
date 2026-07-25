import 'dart:io';
import 'package:get/get.dart';
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

  /// Default background color for alpha compositing (white = paper)
  static const int defaultBgR = 255;
  static const int defaultBgG = 255;
  static const int defaultBgB = 255;

  /// Check if a file path has a supported extension
  static bool isSupported(String filePath) {
    final ext = filePath.split('.').last.toLowerCase();
    return supported.contains(ext);
  }

  /// Normalize any supported image format to PNG.
  /// This decodes the image using the appropriate decoder and re-encodes as PNG.
  /// Returns the path to the temporary normalized PNG file.
  ///
  /// [bgR], [bgG], [bgB] — compositing background color for transparent images.
  /// Defaults to white (255,255,255) for screen printing on white paper.
  ///
  /// Throws [Exception] if the image cannot be decoded.
  static Future<String> normalizeImage(
    String filePath, {
    int bgR = defaultBgR,
    int bgG = defaultBgG,
    int bgB = defaultBgB,
  }) async {
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
        // MEDIUM #3 FIX: Use dedicated WebP decoder instead of retrying generic
        decoded = img.decodeWebP(bytes);
      }
    }

    if (decoded == null) {
      throw Exception('Could not decode image: $filePath');
    }

    Get.log(
      'Original image channels: ${decoded.numChannels}, width: ${decoded.width}, height: ${decoded.height}',
    );

    // FATAL #2 FIX: Convert RGBA to RGB by compositing onto configurable background
    // (default: white for screen printing). Transparent pixels become background color,
    // not black. This prevents all-black film output.
    img.Image rgbImage = decoded;
    if (decoded.numChannels > 3) {
      Get.log('Converting RGBA to RGB (compositing on bg: $bgR,$bgG,$bgB)...');
      // Use built-in compositeImage — أأمن من manual loop
      final background = img.Image(
        width: decoded.width,
        height: decoded.height,
      );
      // fill background with white
      img.fill(background, color: img.ColorRgb8(bgR, bgG, bgB));
      img.compositeImage(background, decoded);
      rgbImage = background;
      Get.log('Converted to RGB, channels: ${rgbImage.numChannels}');
    }

    // Create temporary PNG file
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final tmpPath = '${Directory.systemTemp.path}/vd_normalized_$timestamp.png';
    final tmpFile = File(tmpPath);

    // Senior Fix: Force RGB (3 channels) output + low compression.
    // The 'image' library (Dart) automatically optimizes simple black & white
    // images into 1-channel Grayscale PNGs to save space.
    // This optimization confuses the Python K-Means color separator.
    // By forcing uint8 format and 3 channels, we ensure Python reads
    // a consistent (H, W, 3) shape even for simple logos.
    final rgbForced = rgbImage.convert(
      format: img.Format.uint8,
      numChannels: 3,
    );

    // Encode as PNG (level: 1 = Low compression, prevents extra transformations)
    final pngBytes = img.encodePng(rgbForced, level: 1);
    await tmpFile.writeAsBytes(pngBytes);

    Get.log(
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
        Get.log('Cleaned up temp file: $tempPath');
      }
    } catch (e) {
      // Log but don't throw - cleanup is best effort
      Get.log('Warning: Could not delete temp file $tempPath: $e');
    }
  }

  /// Clean up ALL old temp files from previous sessions.
  /// Call this at app startup to prevent accumulation.
  static Future<int> cleanupOldTempFiles() async {
    int deleted = 0;
    try {
      final tempDir = Directory.systemTemp;
      await for (final entity in tempDir.list()) {
        if (entity is File && entity.path.contains('vd_normalized_')) {
          try {
            // Only delete files older than 1 hour to avoid active processing
            final stat = await entity.stat();
            final age = DateTime.now().difference(stat.modified);
            if (age.inHours >= 1) {
              await entity.delete();
              deleted++;
            }
          } catch (_) {
            // Skip files that can't be deleted
          }
        }
      }
      if (deleted > 0) {
        Get.log('[ImageProcessor] Cleaned up $deleted old temp files');
      }
    } catch (e) {
      Get.log('[ImageProcessor] Warning: Temp cleanup scan failed: $e');
    }
    return deleted;
  }
}
