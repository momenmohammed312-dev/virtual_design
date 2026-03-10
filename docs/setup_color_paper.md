Setup Color Complexity and Paper Size (cm)

Overview
- Color Complexity: Auto (0 colors) is the default. You can switch to a fixed color count (1, 2, 4, 8, 16).
- Paper Size: Default is A4. You can choose Custom (cm) to specify exact width and height in centimeters.
- The values for paper width/height are exposed to the processing pipeline as paperWidthCm and paperHeightCm inside ProcessingSettings.

How to use
- Upload an image (PNG, JPG, TIFF supported).
- In Color Complexity, select Auto or a fixed color count. Auto passes 0 to processing so the backend can auto-detect colors.
- In Paper Size, choose Custom (cm) and fill Width (cm) and Height (cm). The values will be sent to the backend as the paper width/height.
- You can adjust Copies as needed.
- Press Process & Preview to run the pipeline.

Developer notes
- ProcessingSettings now includes: paperWidthCm and paperHeightCm.
- SetupController exposes paperWidthCm and paperHeightCm and passes them to ProcessingSettings on startProcessing.
- UI in SetupPage supports Custom(cm) and binds the inputs to the controller values.
- Image loading in Python now robustly reads images using OpenCV first and falls back to PIL if needed.

Known limitations
- Some images with unusual color depths may still require tuning; check logs if issues arise.

End of doc
