# 🚀 Quick Start — Virtual Design

**تحكم سريع** | **اختبار العرض** | **القوائم السريعة**

---

## ⚡ 30-Second Setup

### Windows
```bash
cd virtual_design
install_deps.bat
flutter run -d windows
```

### Linux/macOS
```bash
cd virtual_design
chmod +x install_deps.sh && ./install_deps.sh
flutter run
```

### Web
```bash
flutter run -d chrome
```

---

## ✅ Verify Everything Works

```bash
# Check Python dependencies
python python/test_imports.py

# Run full pipeline test
python python/test_pipeline.py

# Run Flutter tests
flutter test

# Analyze code
flutter analyze
```

**Expected Output:** ✅ All green

---

## 📁 Key Files at a Glance

| File | Purpose |
|------|---------|
| [README_SETUP.md](README_SETUP.md) | Full installation guide |
| [TESTING.md](TESTING.md) | All testing procedures |
| [PROGRESS.md](PROGRESS.md) | Current status (60% done) |
| [SOP_CHECKLIST.md](SOP_CHECKLIST.md) | Phase-by-phase details |
| [PHASE_7_PLAN.md](PHASE_7_PLAN.md) | Next: License implementation |

---

## 🧪 Test the Image Pipeline

1. **Import an image:**
   ```bash
   flutter run -d windows
   # Dashboard → Upload → Select test_simple.jpg
   ```

2. **Start processing:**
   - Color count: 3-4
   - Click "Process"

3. **Watch progress:**
   - Real-time "Step 1/9", "Step 2/9", etc.
   - ~5-10 seconds for 200×200 image

4. **Check output:**
   - Films saved in `output_test/`
   - film_0_k.png, film_1_cyan.png, etc.

---

## 📊 Project Status

```
Phase 1-6:   ████████████░░░░░░░░░░  60% COMPLETE
Next (7-9):  Phase 7 — License Service
Total (1-12): Expected release Q2 2026
```

**Latest Commits:**
- `f0c7b78` Fix tests to match PythonConfig API
- `021e3de` Add PROGRESS.md (60% complete)
- `3fc6524` Update SOP_CHECKLIST
- `606b5ca` Phase 4-6 test infrastructure

---

## 🐛 Troubleshooting

### Python not found
```bash
python --version
# If fails: Install Python 3.8+ from python.org
# Add to PATH: C:\Python311 (Windows)
```

### Missing dependencies
```bash
pip install -r python/requirements.txt
# Or use install script: install_deps.bat/sh
```

### Flutter build error
```bash
flutter clean
flutter pub get
flutter analyze
```

### Port already in use
```bash
# Kill process on port 8080:
lsof -i :8080 | grep LISTEN | awk '{print $2}' | xargs kill
# Windows: netstat -ano | findstr :8080
```

---

## 🎯 Common Commands

```bash
# Development
flutter run -d windows          # Run on Windows
flutter run -d android          # Run on Android
flutter run -d chrome           # Run on Web
flutter analyze                 # Check code quality
flutter test                    # Run tests

# Python
python python/main.py --input test.jpg --output out --colors 4
python python/test_pipeline.py  # Full pipeline test
python -m pytest python/tests   # Run pytest

# Git
git branch -a                   # See all branches
git log --oneline               # View commits
git checkout fix/python-bridge-sop  # Switch branch
```

---

## 📈 Performance

| Image Size | Colors | Time | Status |
|-----------|--------|------|--------|
| 200×200 | 3-4 | 0.5-1.0s | ✅ Fast |
| 800×600 | 3-4 | 2-3s | ✅ Good |
| 2K | 4-6 | 5-10s | ✅ Okay |
| 4K | 6-8 | 15-30s | ⚠️ Slow |

---

## 🔐 License Status

**Current:** Demo mode (no license required)  
**Next Phase:** License validation (Phase 7)  
**Future:** Offline SHA-256 validation

---

## 📚 Documentation

- **Getting Started:** [README_SETUP.md](README_SETUP.md)
- **Testing Guide:** [TESTING.md](TESTING.md)
- **Progress Tracker:** [PROGRESS.md](PROGRESS.md)
- **Phase Details:** [SOP_CHECKLIST.md](SOP_CHECKLIST.md)
- **Next Phase:** [PHASE_7_PLAN.md](PHASE_7_PLAN.md)

---

## 🆘 Need Help?

1. Check the [TESTING.md](TESTING.md) troubleshooting section
2. Review [PROGRESS.md](PROGRESS.md) for current status
3. Inspect [SOP_CHECKLIST.md](SOP_CHECKLIST.md) for phase details
4. Look at commit messages: `git log --oneline`

---

## 🎯 Next Steps

- [ ] Try the app on your device
- [ ] Run `python test_pipeline.py`
- [ ] Check `flutter test`
- [ ] Continue with [Phase 7: License Service](PHASE_7_PLAN.md)

---

**Version:** 0.6.0  
**Status:** Stable (Phases 1-6 complete)  
**Next Release:** 0.7.0 (Phases 7-9)  
**Target:** 1.0.0 (All phases)

---

**Happy silk screening! 🎨**
