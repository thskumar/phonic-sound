# PPTX → Interactive HTML5 Learning App

Convert PowerPoint lessons into a **mobile-friendly, offline HTML5 learning app** for parents and children. Each slide plays your recorded narration automatically, and a **Speak Out** button plays a second recorded sound. Works without installing Python or PowerPoint on the device that plays the lesson.

## Features

| Feature | Description |
|--------|-------------|
| **Slide viewer** | One slide at a time, fullscreen responsive layout |
| **Auto first sound** | `soundX_1.mp3` plays automatically when slide X opens |
| **Speak Out** | Plays `soundX_2.mp3` for the current slide (falls back to the first sound) |
| **Navigation** | Next, Previous, Home; swipe left/right on mobile |
| **Recorded audio** | Uses your own MP3 recordings from a `sound/` folder — no TTS |
| **Offline** | All assets local — works without internet |
| **PWA** | Installable on phones (manifest + service worker) |
| **Extras** | Loading screen, progress dots, mute, dark mode, keyboard shortcuts |

## Sound naming convention

Place your recordings in a `sound/` folder using `soundX_Y.mp3`:

- `X` = slide (page) number, 1-based
- `Y = 1` → **first** sound, plays automatically when the slide opens
- `Y = 2` → **second** sound, plays when **Speak Out** is pressed

```
sound/
  sound1_1.mp3   # slide 1, auto-play
  sound1_2.mp3   # slide 1, Speak Out
  sound2_1.mp3   # slide 2, auto-play
  ...
```

A slide may have only a first sound, only a second sound, both, or none. Files that don't match the pattern (and duplicates like `sound1_1(1).mp3`) are ignored.

## Quick start

### 1. Install dependencies

```bash
cd project-meraki-teaching
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

**Windows (best slide quality):** Install Microsoft PowerPoint. The tool exports pixel-perfect PNGs via COM. Without PowerPoint, slides are rendered by compositing the embedded images.

### 2. Build from PPTX + recorded sounds

```bash
python app.py lesson.pptx --sound ./sound
```

Output:

```
interactive_lesson/
├── index.html
├── styles/style.css
├── js/app.js
├── slides/slide1.png …
├── audio/sound1_1.mp3, sound1_2.mp3 …   ← copied from ./sound
├── assets/
├── manifest.webmanifest
└── sw.js
```

### 3. Open the lesson

Double-click `interactive_lesson/index.html` or host the folder on any static server. Copy the folder to a phone — it works offline.

> **Tip:** To swap or add recordings later without re-rendering slides, update the `sound/` folder and run:
>
> ```bash
> python app.py lesson.pptx --audio-only
> ```

## CLI reference

```bash
python app.py lesson.pptx [options]

  -o, --output DIR       Output folder (default: interactive_lesson)
  -a, --audio DIR        External narration folder
  --no-tts               Require complete external audio; no TTS
  --voice VOICE          Edge TTS voice (default: en-US-AnaNeural)
  --lang CODE            gTTS language fallback (default: en)
  --title "My Lesson"    HTML / PWA title
  -s, --sound DIR        Folder with soundX_1.mp3 / soundX_2.mp3 (default: ./sound)
  --zip                  Also create interactive_lesson.zip
  --force-fallback       Skip PowerPoint COM; use Pillow slides
  --no-pwa               Disable manifest and service worker
  --autoplay             Auto-advance to next slide after the first sound ends
  --clean                Delete output folder before build
  --audio-only           Reuse existing slides; only re-copy sounds + rebuild HTML
  -v, --verbose          Debug logging
```

## Generated app controls

| Control | Action |
|---------|--------|
| **(slide opens)** | First sound (`soundX_1.mp3`) plays automatically |
| **Speak Out / Space** | Play second sound (`soundX_2.mp3`) |
| **Next / Previous** | Change slides |
| **Home** | First slide |
| **Swipe left / right** | Next / Previous slide |
| **→ / ←** | Next / Previous (keyboard) |
| **M** | Mute / unmute |

Progress is saved in `localStorage` so returning learners resume where they left off.

> **Browser autoplay note:** Mobile browsers block audio until the first tap. The first slide's sound starts on your first interaction; every slide after that auto-plays normally.

## Architecture

```
lesson.pptx                       sound/soundX_Y.mp3
     │                                   │
     ▼                                   ▼
ppt_processor.py ──► slides/slideN.png   audio_manager.py ──► audio/soundX_Y.mp3
     │                                   │
     └─────────────► html_generator.py ◄─┘
                            │
                            ▼
                 index.html, CSS, JS, PWA
```

| Module | Role |
|--------|------|
| `app.py` | CLI entry point |
| `ppt_processor.py` | PPTX → PNG (PowerPoint COM / image composite) |
| `audio_manager.py` | Copy recorded `soundX_Y.mp3` files |
| `html_generator.py` | Interactive HTML5 app |
| `utils.py` | Logging, ZIP, paths |

## Distribution

- **ZIP folder:** `python app.py lesson.pptx --zip`
- **Local folder:** Copy `interactive_lesson/` to USB or device
- **Hosted website:** Upload the folder to Netlify, GitHub Pages, S3, etc.

## Optional: Android APK

The HTML app can be wrapped with [Capacitor](https://capacitorjs.com/) or Cordova. Build the lesson first, then point the wrapper at `interactive_lesson/` as the web root.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| COM export fails | Install PowerPoint, or use `--force-fallback` |
| TTS fails offline | Edge TTS needs internet **during build** only; playback is offline |
| No sound on iOS | User must tap Speak Out (browser policy) |
| Blank slides (fallback) | Add text in PowerPoint placeholders |

## Requirements

- Python 3.10+
- See `requirements.txt`
- Windows + PowerPoint for best slide images (optional)

## License

Use freely for educational projects.
