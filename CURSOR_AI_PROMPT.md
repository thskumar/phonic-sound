# Complete Cursor AI Prompt — PPTX → Interactive HTML5 Learning App

Copy everything below into Cursor when extending or regenerating this project.

---

## Prompt

Build a complete Python-based system that converts a PowerPoint presentation (`.pptx`) into a mobile-friendly interactive HTML5 learning application for parents and children.

### Core requirements

- Read `.pptx`, extract all slides, convert to images, generate HTML5 interactive presentation
- Buttons: **Speak Out**, **Next**, **Previous**, **Home** (optional)
- Support Android, iPhone, tablets, laptops, desktop browsers
- Work **offline** after build
- Distributable as ZIP, hosted site, or local folder

### Input

```
lesson.pptx
audio/              # optional
  slide1.mp3
  slide2.mp3
```

**Recommended (Option A):** Auto-generate narration from slide text via TTS (`edge-tts`, fallback `gTTS`). No manual MP3 recording required.

### Output structure

```
interactive_lesson/
├── index.html
├── styles/style.css
├── js/app.js
├── slides/slide1.png …
├── audio/slide1.mp3 …
├── assets/
├── manifest.webmanifest
└── sw.js
```

### Slide rendering

- **Preferred (Windows):** PowerPoint COM (`comtypes`) export slides as PNG
- **Fallback:** `python-pptx` + Pillow approximate slides with text and embedded images

### JavaScript features

- Slide navigation, audio control, swipe gestures, keyboard (← → Space Home M)
- Preload next image and audio; loading screen; progress indicator; mute; dark mode
- Save progress in localStorage; optional autoplay mode
- Vanilla JS only; no heavy frameworks

### Python modules

- `app.py` — CLI
- `ppt_processor.py` — PPTX → PNG + text
- `audio_manager.py` — external MP3 or TTS
- `html_generator.py` — HTML/CSS/JS/PWA
- `utils.py` — logging, ZIP, paths

### Do NOT

- Generate video output
- Require Python or PowerPoint on the playback device

### Optional

- PWA install, dark mode, autoplay, Capacitor/Cordova APK wrapper

---

Use this repository as the reference implementation.
