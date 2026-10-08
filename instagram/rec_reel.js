// node rec_reel.js <rules|engine|system> out.mp4 [--stills t1,t2]
const { chromium } = require('playwright'); const { spawn } = require('child_process'); const path = require('path');
(async () => {
  const [name, out, flag, list] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(__dirname, 'posts.html') + '#reel=' + name);
  await p.evaluate(() => window.ready); await p.waitForFunction(() => window.render && window.DUR); await p.waitForTimeout(300);
  if (flag === '--stills') { for (const t of list.split(',')) { await p.evaluate(t => render(t), +t); await p.screenshot({ path: `${out}_${t}.jpg`, type: 'jpeg', quality: 80 }); } await b.close(); return; }
  const fps = 30, dur = await p.evaluate(() => DUR), n = Math.round(dur * fps);
  console.log(JSON.stringify(await p.evaluate(() => window.beats)));
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) { await p.evaluate(t => render(t), i / fps); const buf = await p.screenshot({ type: 'jpeg', quality: 92 }); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await b.close();
})();
