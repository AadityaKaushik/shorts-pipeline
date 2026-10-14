// Step scene.html frame by frame in headless Chrome and encode with ffmpeg.
//   node render.mjs preview   -> build/preview_*.png (a few key instants)
//   node render.mjs full      -> build/video_silent.mp4 (every frame, 30 fps)
import puppeteer from 'puppeteer';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import fs from 'node:fs';

const MODE = process.argv[2] || 'preview';
const FPS = 30;
const tl = JSON.parse(fs.readFileSync('build/timeline.json', 'utf8'));

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
         '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars'],
});
const page = await browser.newPage();
await page.setViewport({ width: 540, height: 960, deviceScaleFactor: 2 });
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => { console.error('[page error]', e); process.exit(1); });
await page.goto('http://localhost:8080/scene.html', { waitUntil: 'networkidle0' });
await page.waitForFunction('window.sceneReady === true', { timeout: 90000 });

const shot = async t => {
  await page.evaluate(x => window.renderAt(x), t);
  return page.screenshot({ type: 'png', optimizeForSpeed: true });
};

if (MODE === 'preview') {
  const times = [];
  tl.beats.forEach((b, i) => {
    times.push([`b${String(i).padStart(2, '0')}a`, b.start + 0.9]);
    times.push([`b${String(i).padStart(2, '0')}b`, b.start + Math.max(1.0, b.dur - 0.3)]);
  });
  times.push(['end', tl.total - 1.0]);
  for (const [name, t] of times) {
    fs.writeFileSync(`build/preview_${name}.png`, await shot(t));
    console.log(`preview ${name} @ ${t.toFixed(2)}s`);
  }
} else {
  const n = Math.ceil(tl.total * FPS);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
    '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', 'build/video_silent.mp4'],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const started = Date.now();
  for (let f = 0; f < n; f++) {
    const buf = await shot(f / FPS);
    if (!ff.stdin.write(buf)) await once(ff.stdin, 'drain');
    if (f % 150 === 0) console.log(`frame ${f}/${n}  ${((Date.now() - started) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  const [code] = await once(ff, 'close');
  if (code !== 0) { console.error('ffmpeg failed', code); process.exit(1); }
  console.log(`encoded ${n} frames in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}
await browser.close();
