// usage: node rec.js W H out.mp4 [--stills t1,t2,...]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const [W, H, out, flag, list] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
  const page = await browser.newPage({ viewport: { width: +W, height: +H } });
  await page.goto('file://' + path.join(__dirname, 'hype.html'));
  await page.addStyleTag({ content: `:root{--W:${W}px;--H:${H}px}` });
  await page.evaluate(() => window.ready);
  await page.waitForTimeout(300);
  if (flag === '--stills') {
    for (const t of list.split(',')) { await page.evaluate((t) => render(t), +t); await page.screenshot({ path: `${out}_${t}.jpg`, quality: 85, type: 'jpeg' }); }
    await browser.close(); return;
  }
  const fps = 30, dur = await page.evaluate(() => DUR), n = Math.round(fps * dur);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-shortest',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    await page.evaluate((t) => render(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log('frame', i, '/', n);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await browser.close();
})();
