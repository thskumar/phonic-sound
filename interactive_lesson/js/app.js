
(function () {
  'use strict';

  const cfg = window.LESSON_CONFIG || { slideCount: 50 };
  const total = cfg.slideCount;
  const sounds = cfg.sounds || [];
  let current = 0;
  let muted = false;
  let autoplayMode = false;
  let audioUnlocked = false;

  const el = {
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
  };

  function slideName(n) {
    return 'slide' + (n + 1);
  }

  function slideImageUrl(n) {
    return cfg.slidesBase + slideName(n) + '.png';
  }

  function firstSoundUrl(n) {
    const s = sounds[n];
    return s && s.first ? s.first : null;
  }

  function secondSoundUrl(n) {
    const s = sounds[n];
    return s && s.second ? s.second : null;
  }

  function saveProgress() {
    try {
      localStorage.setItem(cfg.storageKey, String(current));
    } catch (e) {}
  }

  function loadProgress() {
    try {
      const v = parseInt(localStorage.getItem(cfg.storageKey), 10);
      if (!isNaN(v) && v >= 0 && v < total) return v;
    } catch (e) {}
    return 0;
  }

  function updateUI() {
    el.counter.textContent = (current + 1) + ' / ' + total;
    el.btnPrev.disabled = current === 0;
    el.btnNext.disabled = current === total - 1;
    // Play button needs a sound (second preferred, otherwise first)
    const hasSpeak = !!(secondSoundUrl(current) || firstSoundUrl(current));
    el.btnSpeak.disabled = !hasSpeak;
    saveProgress();
  }

  function preloadAdjacent() {
    const next = current + 1;
    if (next < total) {
      const nextImg = new Image();
      nextImg.src = slideImageUrl(next);
      const url = firstSoundUrl(next);
      if (url) {
        const a = new Audio();
        a.preload = 'auto';
        a.src = url;
      }
    }
  }

  function stopAudio() {
    [el.audioFirst, el.audioSecond].forEach(function (a) {
      try { a.pause(); a.currentTime = 0; } catch (e) {}
    });
    el.btnSpeak.classList.remove('playing');
  }

  // First sound: plays automatically when a slide opens
  function playFirst() {
    if (muted) return;
    const url = firstSoundUrl(current);
    if (!url) return;
    stopAudio();
    el.audioFirst.src = url;
    const p = el.audioFirst.play();
    if (p && p.catch) {
      p.catch(function () { /* autoplay blocked until user interacts */ });
    }
  }

  // Second sound: plays when Speak Out is pressed (falls back to first)
  function playSecond() {
    if (muted) return;
    const url = secondSoundUrl(current) || firstSoundUrl(current);
    if (!url) return;
    stopAudio();
    el.audioSecond.src = url;
    el.btnSpeak.classList.add('playing');
    const p = el.audioSecond.play();
    if (p && p.catch) {
      p.catch(function () { el.btnSpeak.classList.remove('playing'); });
    }
  }

  // Browsers block audio before a user gesture; play the current first
  // sound on the very first interaction if autoplay was blocked.
  function unlockAudio() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    if (el.audioFirst.paused) playFirst();
  }

  function showSlide(index, direction) {
    if (index < 0 || index >= total) return;
    stopAudio();
    current = index;

    function revealSlide() {
      el.img.classList.remove('transition-out', 'is-loading');
      el.img.classList.add('transition-in');
      setTimeout(function () { el.img.classList.remove('transition-in'); }, 350);
    }

    el.img.classList.add('transition-out', 'is-loading');
    setTimeout(function () {
      el.img.onload = revealSlide;
      el.img.onerror = revealSlide;
      el.img.src = slideImageUrl(current);
      el.img.alt = 'Lesson slide ' + (current + 1);
      if (el.img.complete) revealSlide();
      updateUI();
      preloadAdjacent();
      playFirst();
    }, direction ? 120 : 0);
  }

  function goTo(index) {
    if (index === current) return;
    showSlide(index, true);
  }

  function next() {
    if (current < total - 1) showSlide(current + 1, true);
  }

  function prev() {
    if (current > 0) showSlide(current - 1, true);
  }

  function home() {
    goTo(0);
  }

  /* Touch / swipe */
  let touchStartX = 0;
  let touchStartY = 0;
  const SWIPE_MIN = 50;

  el.viewport.addEventListener('touchstart', function (e) {
    if (!e.touches.length) return;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }, { passive: true });

  el.viewport.addEventListener('touchend', function (e) {
    if (!e.changedTouches.length) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) < SWIPE_MIN || Math.abs(dy) > Math.abs(dx)) return;
    if (dx < 0) next();
    else prev();
  }, { passive: true });

  el.btnNext.addEventListener('click', next);
  el.btnPrev.addEventListener('click', prev);
  el.btnSpeak.addEventListener('click', playSecond);
  el.btnHome.addEventListener('click', home);

  // Unlock audio on first user interaction (in case autoplay was blocked)
  document.addEventListener('pointerdown', unlockAudio, { once: true });
  document.addEventListener('keydown', unlockAudio, { once: true });

  el.btnMute.addEventListener('click', function () {
    muted = !muted;
    el.muteIcon.textContent = muted ? '🔇' : '🔊';
    el.btnMute.setAttribute('aria-label', muted ? 'Unmute sound' : 'Mute sound');
    if (muted) stopAudio();
  });

  // Autoplay mode: advance after the first (auto) sound finishes
  el.audioFirst.addEventListener('ended', function () {
    if (autoplayMode && current < total - 1) {
      setTimeout(next, 600);
    }
  });

  el.audioSecond.addEventListener('ended', function () {
    el.btnSpeak.classList.remove('playing');
  });

  el.audioSecond.addEventListener('pause', function () {
    if (el.audioSecond.currentTime === 0 || el.audioSecond.ended) {
      el.btnSpeak.classList.remove('playing');
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    switch (e.key) {
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
    }
  });

  if (true) {
    el.btnTheme.addEventListener('click', function () {
      document.body.classList.toggle('dark');
      try {
        localStorage.setItem(cfg.storageKey + '-theme', document.body.classList.contains('dark') ? 'dark' : 'light');
      } catch (e) {}
    });
    try {
      if (localStorage.getItem(cfg.storageKey + '-theme') === 'dark') {
        document.body.classList.add('dark');
      }
    } catch (e) {}
  } else {
    el.btnTheme.style.display = 'none';
  }

  /* Preload slide images then reveal app (audio loads on demand) */
  function preloadAll(done) {
    let loaded = 0;
    const need = total;
    function tick() {
      loaded++;
      const pct = Math.min(100, Math.round((loaded / need) * 100));
      el.loadBar.style.width = pct + '%';
      el.loadBar.parentElement.setAttribute('aria-valuenow', String(pct));
      if (loaded >= need) done();
    }
    for (let i = 0; i < total; i++) {
      const im = new Image();
      im.onload = im.onerror = tick;
      im.src = slideImageUrl(i);
    }
  }

  current = loadProgress();
  preloadAll(function () {
    el.loading.classList.add('hidden');
    el.app.classList.remove('hidden');
    el.img.src = slideImageUrl(current);
    el.img.alt = 'Lesson slide ' + (current + 1);
    updateUI();
    preloadAdjacent();
    playFirst();
  });
})();
