# TFLite model assets

Place the following files in this directory before building:

1. mobilenet_v3.tflite
   Source: https://tfhub.dev/google/lite-model/imagenet/mobilenet_v3_small_100_224/classification/5/metadata/1
   Size: ~10 MB
   Input: [1, 224, 224, 3] float32, values 0-1
   Output: [1, 1001] softmax probabilities

2. deeplab_v3.tflite
   Source: https://tfhub.dev/tensorflow/lite-model/deeplabv3/1/metadata/2
   Size: ~8 MB
   Input: [1, 257, 257, 3] float32, values -1 to 1
   Output: [1, 257, 257, 21] class logits (PASCAL VOC)

After downloading, rename files to match exactly:
  - mobilenet_v3.tflite
  - deeplab_v3.tflite

Note: The app runs fine without these files — it falls back to
      a file-size heuristic classifier automatically.
