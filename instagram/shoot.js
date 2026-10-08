const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const p = await b.newPage({ viewport: { width: 1200, height: 1500 } });
  await p.goto('file://' + path.join(__dirname, 'posts.html'));
  await p.evaluate(() => window.ready); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
  for (const [row, name] of [['rowA', 'rules'], ['rowB', 'engine'], ['rowC', 'system']]) {
    fs.mkdirSync(path.join(__dirname, 'out', name), { recursive: true });
    const slides = await p.$$(`#${row} .slide`);
    for (let i = 0; i < slides.length; i++) await slides[i].screenshot({ path: path.join(__dirname, 'out', name, `${String(i + 1).padStart(2, '0')}.png`) });
  }
  await b.close();
})();
