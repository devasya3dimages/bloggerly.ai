// Reel mode for posts.html: open posts.html#reel=rules|engine|system at 1080x1920.
(function () {
  const m = location.hash.match(/reel=(\w+)/); if (!m) return;
  const CFG = { rules: { row: 'rowA', bpm: 100, beats: 4, bg: '#f4efe3', long: [] },
                engine: { row: 'rowB', bpm: 128, beats: 5, bg: '#0f2a1f', long: [0, 7] },
                system: { row: 'rowC', bpm: 90, beats: 4, bg: '#f6f3ec', long: [4] } }[m[1]];
  const BT = 60 / CFG.bpm;
  const slides = [...document.querySelectorAll(`#${CFG.row} .slide`)];
  const BG = slides.map(s => { const c = getComputedStyle(s); return [c.backgroundColor, c.backgroundImage]; });
  document.body.innerHTML = ''; document.body.style.cssText = `margin:0;padding:0;width:1080px;height:1920px;overflow:hidden;background:${CFG.bg};display:block`;
  const stage = document.createElement('div'); stage.style.cssText = 'position:absolute;inset:0;overflow:hidden';
  document.body.append(stage);
  // per-slide duration in beats, start times
  const durs = slides.map((_, i) => (CFG.long.includes(i) ? 2 : 1) * CFG.beats * BT + (i === slides.length - 1 ? 2 * BT : 0));
  const starts = durs.reduce((a, d, i) => (a.push(i ? a[i - 1] + durs[i - 1] : 0), a), []);
  slides.forEach((s, i) => {
    const wrap = document.createElement('div');
    const bg = getComputedStyle(s).backgroundImage !== 'none' ? getComputedStyle(s).background : getComputedStyle(s).backgroundColor;
    wrap.style.cssText = `position:absolute;inset:0;background-color:${BG[i][0]};opacity:0`;
    if (BG[i][1] !== 'none') { wrap.style.backgroundImage = BG[i][1].replace('120% 80% at 50% 0%', '140% 60% at 50% 10%'); wrap.style.backgroundColor = '#0b1f16'; s.style.background = 'transparent'; }
    s.style.position = 'absolute'; s.style.left = '0'; s.style.top = '285px';
    wrap.append(s); stage.append(wrap);
    s._parts = [...s.children].filter(c => !c.classList.contains('ghost'));
  });
  const cl = (x) => Math.max(0, Math.min(1, x)), eo = (x) => 1 - Math.pow(1 - cl(x), 3);
  window.DUR = starts[starts.length - 1] + durs[durs.length - 1];
  window.render = (t) => {
    slides.forEach((s, i) => {
      const w = s.parentNode, a = starts[i], b = a + durs[i], tr = 0.32;
      if (t < a - 0.001 || t > b + tr) { w.style.opacity = 0; return; }
      const enter = eo((t - a) / tr), exit = i < slides.length - 1 ? eo((t - b) / tr) : 0;
      w.style.opacity = 1; w.style.zIndex = i;
      const x = (1 - enter) * 1080 * (i ? 1 : 0) - exit * 220;
      w.style.transform = `translateX(${x}px) scale(${1 - exit * 0.04})`;
      w.style.filter = exit ? `blur(${exit * 6}px) brightness(${1 - exit * 0.3})` : 'none';
      const lt = t - a;
      s._parts.forEach((p, k) => {
        const e = eo((lt - 0.12 - k * 0.11) / 0.45);
        p.style.opacity = e; p.style.translate = `0 ${(1 - e) * 36}px`; p.style.filter = e < 1 ? `blur(${(1 - e) * 8}px)` : '';
      });
      // gentle push on the whole slide while it holds
      s.style.transform = `scale(${1 + 0.025 * cl(lt / durs[i])})`; s.style.transformOrigin = '50% 50%';
    });
  };
  window.beats = { bpm: CFG.bpm, starts, durs };
})();
