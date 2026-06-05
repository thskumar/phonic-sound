"""Generate interactive HTML5 learning app (HTML, CSS, JS, PWA manifest)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from utils import ensure_dir

logger = logging.getLogger(__name__)


def generate_app(
    output_dir: Path,
    slide_count: int,
    title: str = "Interactive Lesson",
    sound_map: list | None = None,
    enable_pwa: bool = True,
    enable_dark_mode: bool = True,
    enable_autoplay: bool = False,
) -> Path:
    """
    Write index.html, styles/style.css, js/app.js, and optional PWA files.
    Assumes slides/ and audio/ already populated.

    ``sound_map`` is a list (length ``slide_count``) of dicts with web paths:
    ``{"first": "audio/soundX_1.mp3" | None, "second": "audio/soundX_2.mp3" | None}``.
    The "first" sound auto-plays when the slide opens; "second" plays on Speak Out.
    """
    output_dir = ensure_dir(output_dir)
    styles_dir = ensure_dir(output_dir / "styles")
    js_dir = ensure_dir(output_dir / "js")
    assets_dir = ensure_dir(output_dir / "assets")
    ensure_dir(output_dir / "slides")
    ensure_dir(output_dir / "audio")

    if sound_map is None:
        sound_map = [{"first": None, "second": None} for _ in range(slide_count)]
    sounds_json = json.dumps(sound_map)

    (styles_dir / "style.css").write_text(_css(), encoding="utf-8")
    (js_dir / "app.js").write_text(
        _javascript(slide_count, enable_dark_mode, enable_autoplay),
        encoding="utf-8",
    )
    index_path = output_dir / "index.html"
    index_path.write_text(_html(title, slide_count, sounds_json), encoding="utf-8")

    if enable_pwa:
        _write_pwa(output_dir, title)

    # Placeholder favicon note in assets
    readme = assets_dir / "README.txt"
    readme.write_text(
        "Optional: add icon-192.png and icon-512.png for PWA install.\n",
        encoding="utf-8",
    )

    logger.info("Generated HTML app at %s", output_dir)
    return index_path


def _write_pwa(output_dir: Path, title: str) -> None:
    manifest = {
        "name": title,
        "short_name": title[:12],
        "description": "Interactive learning lesson",
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#fff8f0",
        "theme_color": "#6366f1",
        "orientation": "any",
        "icons": [
            {
                "src": "assets/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "assets/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
        ],
    }
    (output_dir / "manifest.webmanifest").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    sw = """
const CACHE = 'lesson-v5';
const ASSETS = ['./', './index.html', './styles/style.css', './js/app.js'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request).catch(() => caches.match('./index.html')))
  );
});
"""
    (output_dir / "sw.js").write_text(sw.strip(), encoding="utf-8")


def _html(title: str, slide_count: int, sounds_json: str = "[]") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="theme-color" content="#6366f1">
  <title>{_esc(title)}</title>
  <link rel="stylesheet" href="styles/style.css">
  <link rel="manifest" href="manifest.webmanifest">
</head>
<body>
  <div id="loading-screen" class="loading-screen" aria-live="polite">
    <div class="loader-spinner" aria-hidden="true"></div>
    <p class="loading-text">Loading lesson…</p>
    <div class="loading-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
      <div id="loading-progress" class="loading-bar-fill"></div>
    </div>
  </div>

  <main id="app" class="app hidden" aria-label="Interactive lesson">
    <header class="top-bar">
      <button type="button" id="btn-home" class="btn btn-icon" title="Home" aria-label="Go to first slide">
        <span class="icon" aria-hidden="true">🏠</span>
      </button>
      <div class="slide-counter" id="slide-counter" aria-live="polite">1 / {slide_count}</div>
      <div class="top-actions">
        <button type="button" id="btn-mute" class="btn btn-icon" title="Mute" aria-label="Mute narration">
          <span class="icon" id="mute-icon" aria-hidden="true">🔊</span>
        </button>
        <button type="button" id="btn-theme" class="btn btn-icon" title="Dark mode" aria-label="Toggle dark mode">
          <span class="icon" aria-hidden="true">🌙</span>
        </button>
      </div>
    </header>

    <section class="slide-viewport" id="slide-viewport">
      <div class="slide-stage" id="slide-stage">
        <img id="slide-image" class="slide-image" src="" alt="Lesson slide" draggable="false">
      </div>
    </section>

    <nav class="controls" aria-label="Lesson controls">
      <button type="button" id="btn-prev" class="btn btn-control" aria-label="Previous slide">
        <span class="icon" aria-hidden="true">◀</span>
        <span class="label">Previous</span>
      </button>
      <button type="button" id="btn-speak" class="btn btn-speak" aria-label="Play sound">
        <span class="icon" aria-hidden="true">🔈</span>
        <span class="label">Play</span>
      </button>
      <button type="button" id="btn-next" class="btn btn-control" aria-label="Next slide">
        <span class="icon" aria-hidden="true">▶</span>
        <span class="label">Next</span>
      </button>
    </nav>
  </main>

  <audio id="audio-first" preload="auto" playsinline></audio>
  <audio id="audio-second" preload="auto" playsinline></audio>

  <script>
    window.LESSON_CONFIG = {{
      slideCount: {slide_count},
      slidesBase: 'slides/',
      audioBase: 'audio/',
      sounds: {sounds_json},
      storageKey: 'lesson-progress'
    }};
  </script>
  <script src="js/app.js"></script>
  <script>
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('sw.js').catch(function() {{}});
    }}
  </script>
</body>
</html>
"""


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _css() -> str:
    return """
:root {
  --bg: #fff8f0;
  --surface: #ffffff;
  --text: #2d3748;
  --accent: #6366f1;
  --accent-dark: #4f46e5;
  --speak: #10b981;
  --speak-dark: #059669;
  --radius: 16px;
  --shadow: 0 8px 32px rgba(99, 102, 241, 0.15);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-top: env(safe-area-inset-top, 0px);
}

body.dark {
  --bg: #1a202c;
  --surface: #2d3748;
  --text: #f7fafc;
  --shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

*, *::before, *::after { box-sizing: border-box; }

html, body {
  margin: 0;
  height: 100%;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  overflow: hidden;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.hidden { display: none !important; }

/* Loading */
.loading-screen {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  z-index: 1000;
  padding: 24px;
}

.loader-spinner {
  width: 56px;
  height: 56px;
  border: 5px solid rgba(99, 102, 241, 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-text {
  margin-top: 20px;
  font-size: 1.25rem;
  font-weight: 600;
}

.loading-bar {
  width: min(280px, 80vw);
  height: 8px;
  background: rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  margin-top: 16px;
  overflow: hidden;
}

.loading-bar-fill {
  height: 100%;
  width: 0%;
  background: var(--accent);
  border-radius: 8px;
  transition: width 0.2s ease;
}

/* App layout */
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
  height: 100dvh;
  padding-top: var(--safe-top);
  padding-bottom: var(--safe-bottom);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--surface);
  box-shadow: var(--shadow);
  flex-shrink: 0;
  z-index: 10;
}

.slide-counter {
  font-weight: 700;
  font-size: 1rem;
  color: var(--accent);
}

.top-actions { display: flex; gap: 8px; }

.slide-viewport {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px;
  position: relative;
}

.slide-stage {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  position: relative;
}

.slide-image {
  display: block;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  min-height: 120px;
  object-fit: contain;
  transition: opacity 0.35s ease, transform 0.35s ease;
  user-select: none;
  -webkit-user-drag: none;
}

.slide-image.is-loading {
  opacity: 0.35;
}

.slide-image.transition-out {
  opacity: 0;
  transform: scale(0.98);
}

.slide-image.transition-in {
  opacity: 1;
  transform: scale(1);
}

/* Controls */
.controls {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1fr;
  gap: 10px;
  padding: 12px 16px calc(12px + var(--safe-bottom));
  background: var(--surface);
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.btn {
  border: none;
  border-radius: var(--radius);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 52px;
  padding: 12px 16px;
  transition: transform 0.15s, background 0.15s, box-shadow 0.15s;
  -webkit-touch-callout: none;
}

.btn:active { transform: scale(0.96); }

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  min-height: 44px;
  min-width: 44px;
  padding: 8px;
  background: transparent;
  font-size: 1.35rem;
}

.btn-control {
  background: rgba(99, 102, 241, 0.12);
  color: var(--accent);
}

.btn-control:active {
  background: rgba(99, 102, 241, 0.22);
}

.btn-speak {
  background: var(--speak);
  color: #fff;
  font-size: 1.05rem;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.35);
  /* Hug the label and sit centered (oval pill, not stretched) */
  justify-self: center;
  width: auto;
  border-radius: 999px;
  padding: 12px 28px;
}

.btn-speak.playing {
  background: var(--speak-dark);
  animation: pulse 1.2s ease infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 4px 16px rgba(16, 185, 129, 0.35); }
  50% { box-shadow: 0 4px 24px rgba(16, 185, 129, 0.6); }
}

.btn-speak .icon { font-size: 1.4rem; }

@media (max-width: 480px) {
  .btn .label { font-size: 0.85rem; }
  .controls { gap: 8px; padding: 10px 12px; }
}

@media (orientation: landscape) and (max-height: 500px) {
  .slide-viewport { padding: 6px; }
  .controls { padding: 8px 12px; }
  .btn { min-height: 44px; }
}
"""


def _javascript(slide_count: int, dark_mode: bool, autoplay: bool) -> str:
    return f"""
(function () {{
  'use strict';

  const cfg = window.LESSON_CONFIG || {{ slideCount: {slide_count} }};
  const total = cfg.slideCount;
  const sounds = cfg.sounds || [];
  let current = 0;
  let muted = false;
  let autoplayMode = {str(autoplay).lower()};
  let audioUnlocked = false;

  const el = {{
    app: document.getElementById('app'),
    loading: document.getElementById('loading-screen'),
    loadBar: document.getElementById('loading-progress'),
    img: document.getElementById('slide-image'),
    counter: document.getElementById('slide-counter'),
    audioFirst: document.getElementById('audio-first'),
    audioSecond: document.getElementById('audio-second'),
    btnPrev: document.getElementById('btn-prev'),
    btnNext: document.getElementById('btn-next'),
    btnSpeak: document.getElementById('btn-speak'),
    btnHome: document.getElementById('btn-home'),
    btnMute: document.getElementById('btn-mute'),
    btnTheme: document.getElementById('btn-theme'),
    muteIcon: document.getElementById('mute-icon'),
    viewport: document.getElementById('slide-viewport'),
  }};

  function slideName(n) {{
    return 'slide' + (n + 1);
  }}

  function slideImageUrl(n) {{
    return cfg.slidesBase + slideName(n) + '.png';
  }}

  function firstSoundUrl(n) {{
    const s = sounds[n];
    return s && s.first ? s.first : null;
  }}

  function secondSoundUrl(n) {{
    const s = sounds[n];
    return s && s.second ? s.second : null;
  }}

  function saveProgress() {{
    try {{
      localStorage.setItem(cfg.storageKey, String(current));
    }} catch (e) {{}}
  }}

  function loadProgress() {{
    try {{
      const v = parseInt(localStorage.getItem(cfg.storageKey), 10);
      if (!isNaN(v) && v >= 0 && v < total) return v;
    }} catch (e) {{}}
    return 0;
  }}

  function updateUI() {{
    el.counter.textContent = (current + 1) + ' / ' + total;
    el.btnPrev.disabled = current === 0;
    el.btnNext.disabled = current === total - 1;
    // Play button needs a sound (second preferred, otherwise first)
    const hasSpeak = !!(secondSoundUrl(current) || firstSoundUrl(current));
    el.btnSpeak.disabled = !hasSpeak;
    saveProgress();
  }}

  function preloadAdjacent() {{
    const next = current + 1;
    if (next < total) {{
      const nextImg = new Image();
      nextImg.src = slideImageUrl(next);
      const url = firstSoundUrl(next);
      if (url) {{
        const a = new Audio();
        a.preload = 'auto';
        a.src = url;
      }}
    }}
  }}

  function stopAudio() {{
    [el.audioFirst, el.audioSecond].forEach(function (a) {{
      try {{ a.pause(); a.currentTime = 0; }} catch (e) {{}}
    }});
    el.btnSpeak.classList.remove('playing');
  }}

  // First sound: plays automatically when a slide opens
  function playFirst() {{
    if (muted) return;
    const url = firstSoundUrl(current);
    if (!url) return;
    stopAudio();
    el.audioFirst.src = url;
    const p = el.audioFirst.play();
    if (p && p.catch) {{
      p.catch(function () {{ /* autoplay blocked until user interacts */ }});
    }}
  }}

  // Second sound: plays when Speak Out is pressed (falls back to first)
  function playSecond() {{
    if (muted) return;
    const url = secondSoundUrl(current) || firstSoundUrl(current);
    if (!url) return;
    stopAudio();
    el.audioSecond.src = url;
    el.btnSpeak.classList.add('playing');
    const p = el.audioSecond.play();
    if (p && p.catch) {{
      p.catch(function () {{ el.btnSpeak.classList.remove('playing'); }});
    }}
  }}

  // Browsers block audio before a user gesture; play the current first
  // sound on the very first interaction if autoplay was blocked.
  function unlockAudio() {{
    if (audioUnlocked) return;
    audioUnlocked = true;
    if (el.audioFirst.paused) playFirst();
  }}

  function showSlide(index, direction) {{
    if (index < 0 || index >= total) return;
    stopAudio();
    current = index;

    function revealSlide() {{
      el.img.classList.remove('transition-out', 'is-loading');
      el.img.classList.add('transition-in');
      setTimeout(function () {{ el.img.classList.remove('transition-in'); }}, 350);
    }}

    el.img.classList.add('transition-out', 'is-loading');
    setTimeout(function () {{
      el.img.onload = revealSlide;
      el.img.onerror = revealSlide;
      el.img.src = slideImageUrl(current);
      el.img.alt = 'Lesson slide ' + (current + 1);
      if (el.img.complete) revealSlide();
      updateUI();
      preloadAdjacent();
      playFirst();
    }}, direction ? 120 : 0);
  }}

  function goTo(index) {{
    if (index === current) return;
    showSlide(index, true);
  }}

  function next() {{
    if (current < total - 1) showSlide(current + 1, true);
  }}

  function prev() {{
    if (current > 0) showSlide(current - 1, true);
  }}

  function home() {{
    goTo(0);
  }}

  /* Touch / swipe */
  let touchStartX = 0;
  let touchStartY = 0;
  const SWIPE_MIN = 50;

  el.viewport.addEventListener('touchstart', function (e) {{
    if (!e.touches.length) return;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }}, {{ passive: true }});

  el.viewport.addEventListener('touchend', function (e) {{
    if (!e.changedTouches.length) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) < SWIPE_MIN || Math.abs(dy) > Math.abs(dx)) return;
    if (dx < 0) next();
    else prev();
  }}, {{ passive: true }});

  el.btnNext.addEventListener('click', next);
  el.btnPrev.addEventListener('click', prev);
  el.btnSpeak.addEventListener('click', playSecond);
  el.btnHome.addEventListener('click', home);

  // Unlock audio on first user interaction (in case autoplay was blocked)
  document.addEventListener('pointerdown', unlockAudio, {{ once: true }});
  document.addEventListener('keydown', unlockAudio, {{ once: true }});

  el.btnMute.addEventListener('click', function () {{
    muted = !muted;
    el.muteIcon.textContent = muted ? '🔇' : '🔊';
    el.btnMute.setAttribute('aria-label', muted ? 'Unmute sound' : 'Mute sound');
    if (muted) stopAudio();
  }});

  // Autoplay mode: advance after the first (auto) sound finishes
  el.audioFirst.addEventListener('ended', function () {{
    if (autoplayMode && current < total - 1) {{
      setTimeout(next, 600);
    }}
  }});

  el.audioSecond.addEventListener('ended', function () {{
    el.btnSpeak.classList.remove('playing');
  }});

  el.audioSecond.addEventListener('pause', function () {{
    if (el.audioSecond.currentTime === 0 || el.audioSecond.ended) {{
      el.btnSpeak.classList.remove('playing');
    }}
  }});

  document.addEventListener('keydown', function (e) {{
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    switch (e.key) {{
      case 'ArrowRight':
      case 'PageDown':
        e.preventDefault();
        next();
        break;
      case 'ArrowLeft':
      case 'PageUp':
        e.preventDefault();
        prev();
        break;
      case ' ':
        e.preventDefault();
        playSecond();
        break;
      case 'Home':
        e.preventDefault();
        home();
        break;
      case 'm':
      case 'M':
        el.btnMute.click();
        break;
    }}
  }});

  if ({str(dark_mode).lower()}) {{
    el.btnTheme.addEventListener('click', function () {{
      document.body.classList.toggle('dark');
      try {{
        localStorage.setItem(cfg.storageKey + '-theme', document.body.classList.contains('dark') ? 'dark' : 'light');
      }} catch (e) {{}}
    }});
    try {{
      if (localStorage.getItem(cfg.storageKey + '-theme') === 'dark') {{
        document.body.classList.add('dark');
      }}
    }} catch (e) {{}}
  }} else {{
    el.btnTheme.style.display = 'none';
  }}

  /* Preload slide images then reveal app (audio loads on demand) */
  function preloadAll(done) {{
    let loaded = 0;
    const need = total;
    function tick() {{
      loaded++;
      const pct = Math.min(100, Math.round((loaded / need) * 100));
      el.loadBar.style.width = pct + '%';
      el.loadBar.parentElement.setAttribute('aria-valuenow', String(pct));
      if (loaded >= need) done();
    }}
    for (let i = 0; i < total; i++) {{
      const im = new Image();
      im.onload = im.onerror = tick;
      im.src = slideImageUrl(i);
    }}
  }}

  current = loadProgress();
  preloadAll(function () {{
    el.loading.classList.add('hidden');
    el.app.classList.remove('hidden');
    el.img.src = slideImageUrl(current);
    el.img.alt = 'Lesson slide ' + (current + 1);
    updateUI();
    preloadAdjacent();
    playFirst();
  }});
}})();
"""
