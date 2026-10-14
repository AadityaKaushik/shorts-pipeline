// DNS explainer scene. Every visual is a pure function of time t (seconds), so
// the renderer can step frame by frame: window.renderAt(t) draws exactly that
// instant. Beat timings come from build/timeline.json (one beat per narration line).
import * as THREE from 'three';

const W = 540, H = 960, DPR = 2;
const STAGE = { top: 226, h: 376 };   // must match #gl in scene.html
const LABEL_MIN_Y = STAGE.top + 54;   // a label's bottom edge; keeps the whole pill inside the stage
const LABEL_MAX_Y = STAGE.top + STAGE.h - 6;
const HEX = {
  cyan: '#4fd1ff', violet: '#a78bfa', amber: '#fbbf24', green: '#34d399',
  pink: '#f472b6', white: '#e8eefc', muted: '#7f8db0', grid: '#2c3a5c',
};

// ---------- small math ----------
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(20261014);
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = x => { x = clamp(x); return x * x * (3 - 2 * x); };
const ease = x => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const ramp = (t, a, b) => smooth((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const lerp3 = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
const add3 = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];

// ---------- glowing dot material ----------
const VERT = `
attribute float aScale; attribute float aSeed; attribute float aAlpha;
uniform float uSize; uniform float uTime; uniform float uTwinkle; uniform float uPR;
varying float vA;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  float tw = 1.0 - uTwinkle * 0.5 * (1.0 + sin(uTime * 2.4 + aSeed * 6.2831));
  gl_PointSize = uSize * aScale * uPR * (11.0 / -mv.z);
  vA = aAlpha * tw;
}`;
const FRAG = `
uniform vec3 uColor; uniform float uOpacity; varying float vA;
void main() {
  float d = length(gl_PointCoord - 0.5);
  if (d > 0.5) discard;
  float core = smoothstep(0.5, 0.0, d);
  vec3 col = mix(uColor, vec3(1.0), smoothstep(0.22, 0.0, d) * 0.5);
  gl_FragColor = vec4(col, core * core * uOpacity * vA);
}`;
const allMats = [];
function dotMat(color, size, twinkle) {
  const m = new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: new THREE.Color(color) }, uOpacity: { value: 1 }, uSize: { value: size },
      uTime: { value: 0 }, uTwinkle: { value: twinkle }, uPR: { value: DPR },
    },
    vertexShader: VERT, fragmentShader: FRAG, transparent: true,
    depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
  });
  allMats.push(m);
  return m;
}
// pts: [x, y, z, scale?, alpha?]
function cloud(pts, color, size, twinkle = 0.15) {
  const n = pts.length;
  const pos = new Float32Array(n * 3), sc = new Float32Array(n), al = new Float32Array(n), sd = new Float32Array(n);
  pts.forEach((p, i) => {
    pos[i * 3] = p[0]; pos[i * 3 + 1] = p[1]; pos[i * 3 + 2] = p[2];
    sc[i] = p[3] ?? 1; al[i] = p[4] ?? 1; sd[i] = rng();
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aScale', new THREE.BufferAttribute(sc, 1));
  g.setAttribute('aAlpha', new THREE.BufferAttribute(al, 1));
  g.setAttribute('aSeed', new THREE.BufferAttribute(sd, 1));
  const p = new THREE.Points(g, dotMat(color, size, twinkle));
  p.frustumCulled = false;
  return p;
}
function setOpacity(obj, o) {
  obj.traverse(c => { if (c.material && c.material.uniforms) c.material.uniforms.uOpacity.value = o; });
}

// ---------- shape samplers ----------
function seg(a, b, step = 0.065, s = 1, al = 1) {
  const d = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
  const n = Math.max(1, Math.round(d / step)), o = [];
  for (let i = 0; i <= n; i++) { const p = lerp3(a, b, i / n); o.push([p[0], p[1], p[2], s, al]); }
  return o;
}
function boxEdges(c, w, h, d, step = 0.065, s = 1, al = 1) {
  const [x, y, z] = c, v = (i, j, k) => [x + i * w / 2, y + j * h / 2, z + k * d / 2];
  const E = [];
  for (const j of [-1, 1]) for (const k of [-1, 1]) E.push([v(-1, j, k), v(1, j, k)]);
  for (const i of [-1, 1]) for (const k of [-1, 1]) E.push([v(i, -1, k), v(i, 1, k)]);
  for (const i of [-1, 1]) for (const j of [-1, 1]) E.push([v(i, j, -1), v(i, j, 1)]);
  return E.flatMap(([a, b]) => seg(a, b, step, s, al));
}
function ringXZ(c, r, step = 0.08, s = 1, al = 1) {
  const n = Math.max(8, Math.round(2 * Math.PI * r / step)), o = [];
  for (let i = 0; i < n; i++) {
    const a = i / n * 2 * Math.PI;
    o.push([c[0] + r * Math.cos(a), c[1], c[2] + r * Math.sin(a), s, al]);
  }
  return o;
}
function ringVert(c, r, phi, step = 0.08, s = 1, al = 1) {
  const n = Math.max(8, Math.round(2 * Math.PI * r / step)), o = [];
  for (let i = 0; i < n; i++) {
    const a = i / n * 2 * Math.PI, h = r * Math.cos(a);
    o.push([c[0] + h * Math.cos(phi), c[1] + r * Math.sin(a), c[2] + h * Math.sin(phi), s, al]);
  }
  return o;
}
const baseRings = () => [...ringXZ([0, 0.01, 0], 0.95, 0.11, 0.8, 0.5), ...ringXZ([0, 0.01, 0], 0.62, 0.11, 0.7, 0.3)];

// ---------- objects ----------
function makeServer(color) {
  const g = new THREE.Group();
  const body = boxEdges([0, 0.85, 0], 0.9, 1.5, 0.7);
  for (const y of [0.45, 0.85, 1.25]) body.push(...seg([-0.45, y, 0.35], [0.45, y, 0.35], 0.07, 0.7, 0.65));
  g.add(cloud(body, color, 3.0));
  g.add(cloud(baseRings(), color, 2.4, 0.3));
  const leds = [];
  for (const y of [0.27, 0.67, 1.07]) for (const x of [-0.3, -0.17]) leds.push([x, y + 0.06, 0.36, 1.5, 1]);
  g.add(cloud(leds, HEX.green, 3.2, 0.9));
  return g;
}
function makeLaptop(color) {
  const g = new THREE.Group(), pts = boxEdges([0, 0.04, 0.15], 1.4, 0.07, 0.9);
  for (let i = 0; i < 9; i++) for (let j = 0; j < 4; j++) pts.push([-0.52 + i * 0.13, 0.09, 0.0 + j * 0.12, 0.55, 0.45]);
  const hl = [-0.7, 0.08, -0.3], hr = [0.7, 0.08, -0.3], tl = [-0.7, 1.0, -0.5], tr = [0.7, 1.0, -0.5];
  pts.push(...seg(hl, hr), ...seg(tl, tr), ...seg(hl, tl), ...seg(hr, tr));
  g.add(cloud(pts, color, 3.0));
  const scr = [];
  [[0.0, 0.55], [0.12, 0.8], [0.12, 0.62], [0.0, 0.4], [0.12, 0.7]].forEach(([ind, len], r) => {
    const y = 0.84 - r * 0.14, k = (y - 0.08) / 0.92, z = -0.3 - 0.2 * k + 0.01;
    for (let x = -0.55 + ind; x < -0.55 + ind + len; x += 0.065) scr.push([x, y, z, 0.6, 0.75]);
  });
  g.add(cloud(scr, HEX.white, 2.4, 0.35));
  g.add(cloud(baseRings(), color, 2.4, 0.3));
  return g;
}
function makeRoot(color) {
  const g = new THREE.Group(), c = [0, 1.06, 0], r = 0.58, pts = [];
  for (const lat of [-60, -30, 0, 30, 60]) {
    const a = lat * Math.PI / 180;
    pts.push(...ringXZ([0, c[1] + r * Math.sin(a), 0], r * Math.cos(a), 0.075, lat === 0 ? 1.1 : 0.85));
  }
  for (let k = 0; k < 6; k++) pts.push(...ringVert(c, r, k * Math.PI / 6, 0.075, 0.75, 0.8));
  pts.push(...seg([0, 0, 0], [0, 0.48, 0], 0.07, 0.8, 0.8));
  g.add(cloud(pts, color, 3.0));
  g.add(cloud(baseRings(), color, 2.4, 0.3));
  return g;
}
function makeCache(color) {
  const g = new THREE.Group(), pts = [];
  for (const y of [0.42, 0.6, 0.78]) pts.push(...boxEdges([0, y, 0], 0.62, 0.08, 0.46, 0.06, 0.85));
  g.add(cloud(pts, color, 2.8, 0.25));
  return g;
}

// ---------- the world ----------
// Left = your side (laptop, resolver); right = the DNS hierarchy as a column
// running back to front (root, .com, google's server); web server front-centre.
const NODE_POS = {
  you: [-2.7, 0, 0.9], you2: [-2.6, 0, -1.3], res: [-0.8, 0, 0.0],
  root: [1.5, 0, -2.0], tld: [2.0, 0, -0.2], auth: [1.6, 0, 1.6], web: [0.4, 0, 2.3],
  cache: [0.15, 0, 0.35],
};
const NODE_TOP = { you: 1.0, you2: 1.0, res: 1.62, root: 1.66, tld: 1.62, auth: 1.62, web: 1.62, cache: 0.84 };

const canvas = document.getElementById('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(DPR);
renderer.setSize(W, STAGE.h, false);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#04060c');
const camera = new THREE.PerspectiveCamera(36, W / STAGE.h, 0.1, 200);

const gridPts = [];
for (let x = -7; x <= 7; x++) gridPts.push(...seg([x, 0, -7], [x, 0, 7], 0.16, 0.7, 0.55));
for (let z = -7; z <= 7; z++) gridPts.push(...seg([-7, 0, z], [7, 0, z], 0.16, 0.7, 0.55));
const grid = cloud(gridPts, HEX.grid, 2.2, 0.0);
scene.add(grid);
const starPts = [];
for (let i = 0; i < 700; i++) {
  const th = rng() * Math.PI * 2, ph = Math.acos(2 * rng() - 1), r = 24 + rng() * 18;
  starPts.push([r * Math.sin(ph) * Math.cos(th), Math.abs(r * Math.cos(ph)) * 0.8 + 2, r * Math.sin(ph) * Math.sin(th), 0.5 + rng() * 0.8, 0.35 + rng() * 0.5]);
}
const stars = cloud(starPts, '#9fb4ff', 2.0, 0.6);
scene.add(stars);

const nodes = {
  you: makeLaptop(HEX.cyan), you2: makeLaptop(HEX.pink), res: makeServer(HEX.cyan),
  root: makeRoot(HEX.violet), tld: makeServer(HEX.violet), auth: makeServer(HEX.amber),
  web: makeServer(HEX.green), cache: makeCache(HEX.green),
};
for (const [k, g] of Object.entries(nodes)) { g.position.set(...NODE_POS[k]); scene.add(g); }
const anchor = (k, extra = 0) => add3(NODE_POS[k], [0, NODE_TOP[k] + extra, 0]);

// ---------- beats ----------
// One entry per narration line. Labels: node -> [title, subtitle, colour].
const BEATS = [
  { comment: '// networking · how DNS works', head: [['Where is ', 'w'], ['google.com', 'cyan'], ['?', 'w']],
    cam: { p: [-0.3, 6.0, 7.9], t: [-0.3, 0.6, 0.1] },
    labels: { you: ['You', 'typing google.com', HEX.cyan] },
    term: ['$', 'dig google.com', HEX.white] },
  { comment: '// computers route by IP address', head: [['Names ', 'w'], ['→ ', 'muted'], ['numbers', 'amber']],
    cam: { p: [-2.6, 3.2, 4.7], t: [-2.7, 0.6, 0.9] },
    labels: { you: ['You', 'needs an IP address', HEX.cyan] },
    term: [';', 'google.com  →  ?.?.?.?', HEX.muted] },
  { comment: '// step 1 · your DNS resolver', head: [['Ask the ', 'w'], ['resolver', 'cyan']],
    cam: { p: [-1.75, 4.1, 5.4], t: [-1.75, 0.7, 0.45] },
    labels: { you: ['You', 'asking for google.com', HEX.cyan], res: ['DNS Resolver', 'run by your ISP', HEX.cyan] },
    term: ['you', '→ resolver  google.com A?', HEX.cyan] },
  { comment: '// step 2 · root server', head: [['Start at the ', 'w'], ['root', 'violet']],
    cam: { p: [0.35, 4.8, 4.8], t: [0.35, 0.8, -1.0] },
    labels: { res: ['DNS Resolver', 'asking the root', HEX.cyan], root: ['Root server', '1 of 13 named roots', HEX.violet] },
    term: ['resolver', '→ root  google.com A?', HEX.cyan] },
  { comment: '// a referral, not an answer', head: [['Root', 'violet'], [' → ask .com', 'w']],
    cam: { p: [0.1, 4.6, 5.0], t: [0.3, 0.8, -1.0] },
    labels: { res: ['DNS Resolver', 'got a referral', HEX.cyan], root: ['Root server', '→ try .com', HEX.violet] },
    term: ['root', '← try .com (a.gtld-servers.net)', HEX.violet] },
  { comment: '// step 3 · top-level domain', head: [['.com', 'violet'], [' points onward', 'w']],
    cam: { p: [0.6, 4.5, 5.3], t: [0.6, 0.8, -0.1] },
    labels: { res: ['DNS Resolver', 'following referrals', HEX.cyan], tld: ['.com server', '→ try ns1.google.com', HEX.violet] },
    term: ['.com', '← try ns1.google.com', HEX.violet] },
  { comment: '// step 4 · authoritative server', head: [['The ', 'w'], ['answer', 'amber']],
    cam: { p: [0.4, 4.5, 6.2], t: [0.4, 0.8, 0.8] },
    labels: { res: ['DNS Resolver', 'got the answer', HEX.amber], auth: ['ns1.google.com', 'authoritative', HEX.amber] },
    term: ['ns1', '← A 142.250.183.14', HEX.amber] },
  { comment: '// only now does the request start', head: [['Now ', 'w'], ['connect', 'green']],
    cam: { p: [-1.1, 4.9, 7.4], t: [-1.1, 0.6, 1.2] },
    labels: { you: ['You', '142.250.183.14', HEX.amber], web: ['Google', 'web server', HEX.green] },
    term: ['you', '→ 142.250.183.14:443  connect', HEX.green] },
  { comment: '// time to live (TTL)', head: [['Cache ', 'green'], ['the answer', 'w']],
    cam: { p: [-0.35, 3.3, 3.7], t: [-0.35, 0.9, 0.2] },
    labels: { res: ['Resolver cache', 'google.com · TTL {ttl}s', HEX.green] },
    term: ['cache', 'google.com  TTL 300s', HEX.green] },
  { comment: '// next lookup · cache hit', head: [['Instant ', 'green'], ['answer', 'w']],
    cam: { p: [-1.7, 4.1, 4.4], t: [-1.7, 0.7, -0.65] },
    labels: { you2: ['Next user', 'google.com?', HEX.pink], res: ['Resolver cache', 'hit · no root trip', HEX.green] },
    term: ['cache', 'hit → 142.250.183.14  0 hops', HEX.green] },
  { comment: '// DNS in one line', head: [["The internet's ", 'w'], ['phonebook', 'cyan']],
    cam: { p: [-0.3, 6.3, 8.4], t: [-0.3, 0.6, 0.1] },
    labels: {},
    term: [';;', 'names → numbers, in milliseconds', HEX.muted] },
];
const CAM_START = { p: [3.6, 8.6, 11.0], t: [-0.3, 0.6, 0.1] };

// hops: [beat, from, to, colour, offset s, duration s]
const HOPS = [
  [2, 'you', 'res', HEX.cyan, 0.35, 1.6],
  [3, 'res', 'root', HEX.cyan, 0.5, 1.7],
  [4, 'root', 'res', HEX.violet, 0.4, 1.7],
  [5, 'res', 'tld', HEX.cyan, 0.15, 1.3], [5, 'tld', 'res', HEX.violet, 1.75, 1.3],
  [6, 'res', 'auth', HEX.cyan, 0.15, 1.2], [6, 'auth', 'res', HEX.amber, 1.6, 1.4],
  [7, 'res', 'you', HEX.amber, 0.15, 1.4],
  [9, 'you2', 'res', HEX.cyan, 0.25, 0.9], [9, 'res', 'you2', HEX.amber, 1.35, 0.75],
];
// node visibility: [beat it appears in, offset s]; dims: beat -> {node: level}
const APPEAR = { you: [0, -0.3], res: [0, 0.5], root: [0, 0.9], tld: [0, 1.2], auth: [0, 1.5],
                 web: [7, 1.4], cache: [8, 0.5], you2: [9, 0.0] };
const DIMS = { 9: { root: 0.22, tld: 0.22, auth: 0.22, web: 0.22 } };

let TL;
const S = i => TL.beats[i].start;
const E = i => (i + 1 < TL.beats.length ? TL.beats[i + 1].start : TL.total);
const beatAt = t => { let i = 0; for (let k = 0; k < TL.beats.length; k++) if (t >= S(k)) i = k; return i; };

// ---------- packets ----------
class Hop {
  constructor(from, to, color, t0, dur, until) {
    Object.assign(this, { t0, dur, until });
    const p0 = anchor(from), p2 = anchor(to), mid = lerp3(p0, p2, 0.5);
    const lift = 1.0 + 0.12 * Math.hypot(p2[0] - p0[0], p2[2] - p0[2]);
    const p1 = [mid[0], Math.max(p0[1], p2[1]) + lift, mid[2]];
    this.at = s => { const u = 1 - s; return [0, 1, 2].map(i => u * u * p0[i] + 2 * u * s * p1[i] + s * s * p2[i]); };
    const N = 90;
    this.route = cloud(Array.from({ length: N + 1 }, (_, i) => [...this.at(i / N), 0.55, 0.6]), color, 2.4, 0.2);
    this.routeN = N + 1;
    this.head = cloud(Array.from({ length: 20 }, (_, i) =>
      [0, 0, 0, i === 0 ? 6 : i === 1 ? 2.4 : 1.7 * (1 - (i - 2) / 18), i === 0 ? 0.22 : i === 1 ? 1 : 0.8 * (1 - (i - 2) / 18)]),
      color, 3.2, 0);
    scene.add(this.route, this.head);
  }
  update(t) {
    const s = ease((t - this.t0) / this.dur);
    this.route.geometry.setDrawRange(0, Math.floor(s * this.routeN));
    setOpacity(this.route, t < this.t0 ? 0 : 1 - ramp(t, this.until - 0.35, this.until));
    const pos = this.head.geometry.attributes.position;
    for (let i = 0; i < 20; i++) {
      const p = this.at(clamp(s - Math.max(0, i - 1) * 0.013));
      pos.setXYZ(i, p[0], p[1], p[2]);
    }
    pos.needsUpdate = true;
    setOpacity(this.head, ramp(t, this.t0, this.t0 + 0.12) * (1 - ramp(t, this.t0 + this.dur, this.t0 + this.dur + 0.3)));
  }
}
// steady data flow you -> web once the connection opens
class Stream {
  constructor(from, to, color, t0, until) {
    Object.assign(this, { t0, until });
    this.hop = new Hop(from, to, color, t0, 0.9, until);
    this.hop.head.visible = false;
    this.flow = cloud(Array.from({ length: 10 }, () => [0, 0, 0, 1.6, 0.9]), color, 3.0, 0);
    scene.add(this.flow);
  }
  update(t) {
    this.hop.update(t);
    const pos = this.flow.geometry.attributes.position;
    for (let k = 0; k < 10; k++) {
      const p = this.hop.at(((t - this.t0) * 0.55 + k / 10) % 1);
      pos.setXYZ(k, p[0], p[1], p[2]);
    }
    pos.needsUpdate = true;
    setOpacity(this.flow, ramp(t, this.t0 + 0.8, this.t0 + 1.2) * (1 - ramp(t, this.until - 0.35, this.until)));
  }
}

// ---------- overlays ----------
const hud = document.getElementById('hud'), labelsEl = document.getElementById('labels');
const linesEl = document.getElementById('lines'), fadeEl = document.getElementById('fade');
let heads = [], labelRuns = [];

function buildOverlays() {
  heads = BEATS.map(b => {
    const c = document.createElement('div'); c.className = 'comment';
    const h = document.createElement('div'); h.className = 'headline';
    const inner = document.createElement('span'); inner.className = 'inner';
    for (const [txt, cls] of b.head) { const s = document.createElement('span'); s.className = cls; s.textContent = txt; inner.appendChild(s); }
    h.appendChild(inner); hud.append(c, h);
    let fs = 40; h.style.fontSize = fs + 'px';
    while (inner.getBoundingClientRect().width > 496 && fs > 24) { fs -= 1; h.style.fontSize = fs + 'px'; }
    return { c, h, text: b.comment };
  });
  // consecutive beats with the same label on the same node form one run (no flicker)
  const names = new Set(BEATS.flatMap(b => Object.keys(b.labels)));
  for (const node of names) {
    let run = null;
    BEATS.forEach((b, i) => {
      const spec = b.labels[node], key = spec && JSON.stringify(spec);
      if (run && run.key === key) { run.b1 = i; return; }
      if (run) labelRuns.push(run);
      run = spec ? { node, spec, key, b0: i, b1: i } : null;
    });
    if (run) labelRuns.push(run);
  }
  for (const r of labelRuns) {
    const el = document.createElement('div'); el.className = 'label';
    el.style.setProperty('--c', r.spec[2]);
    el.innerHTML = `<div class="t"></div><div class="s"></div>`;
    el.querySelector('.t').textContent = r.spec[0];
    r.el = el; r.sub = el.querySelector('.s'); labelsEl.appendChild(el);
  }
}

function nodeOpacity(k, t) {
  const [b, off] = APPEAR[k];
  let o = ramp(t, S(b) + off, S(b) + off + 0.7);
  for (const [bs, levels] of Object.entries(DIMS)) {
    const i = +bs;
    if (levels[k] !== undefined) o *= 1 - (1 - levels[k]) * (ramp(t, S(i), S(i) + 0.6) - ramp(t, E(i) - 0.1, E(i) + 0.5));
  }
  return o;
}

const v3 = new THREE.Vector3();
function project(p) {
  v3.set(p[0], p[1], p[2]).project(camera);
  return [(v3.x + 1) / 2 * W, STAGE.top + (1 - v3.y) / 2 * STAGE.h];
}

// Labels stay inside the stage window and never touch each other: each one is
// clamped to the stage, then nudged clear of labels already placed this frame.
function updateLabels(t) {
  const placed = [];
  for (const r of labelRuns) {
    const t0 = S(r.b0), t1 = E(r.b1);
    const o = ramp(t, t0 + 0.15, t0 + 0.5) * (1 - ramp(t, t1 - 0.3, t1)) * nodeOpacity(r.node, t);
    r.el.style.opacity = o.toFixed(3);
    r.el.style.display = o < 0.005 ? 'none' : 'block';
    if (o < 0.005) continue;
    r.sub.textContent = r.spec[1].replace('{ttl}', String(300 - Math.max(0, Math.floor(t - t0))));
    let [x, y] = project(anchor(r.node, 0.3));
    const w = r.el.offsetWidth, h = r.el.offsetHeight;
    x = clamp(x, w / 2 + 12, W - w / 2 - 12);
    y = clamp(y, LABEL_MIN_Y, LABEL_MAX_Y);
    for (const q of placed) {
      const overlapX = Math.abs(x - q.x) < (w + q.w) / 2 + 6;
      const overlapY = Math.abs(y - q.y) < (h + q.h) / 2 + 6;
      if (overlapX && overlapY) {
        const up = q.y - q.h - 6, down = q.y + h + 6;
        y = up >= LABEL_MIN_Y ? up : Math.min(down, LABEL_MAX_Y);
      }
    }
    placed.push({ x, y, w, h });
    r.el.style.left = x.toFixed(1) + 'px';
    r.el.style.top = (y + (1 - ramp(t, t0 + 0.15, t0 + 0.5)) * 6).toFixed(1) + 'px';
  }
}

function updateHud(t) {
  heads.forEach((hd, i) => {
    const s = i === 0 ? 0.2 : S(i);
    const inn = ramp(t, s, s + 0.45);
    const out = i + 1 < heads.length ? ramp(t, S(i + 1) - 0.05, S(i + 1) + 0.3) : 0;
    const o = inn * (1 - out);
    for (const el of [hd.c, hd.h]) {
      el.style.opacity = o.toFixed(3);
      el.style.display = o < 0.005 ? 'none' : 'block';
    }
    if (o < 0.005) return;
    hd.h.style.filter = `blur(${((1 - inn) * 10 + out * 8).toFixed(2)}px)`;
    hd.h.style.transform = `translateY(${((1 - inn) * 14 - out * 10).toFixed(2)}px)`;
    const n = Math.floor(clamp((t - s) * 42, 0, hd.text.length));
    const typing = n < hd.text.length, blink = Math.floor(t * 2) % 2 === 0;
    hd.c.innerHTML = '';
    hd.c.append(document.createTextNode(hd.text.slice(0, n)));
    if (typing || blink) { const k = document.createElement('span'); k.className = 'caret'; hd.c.append(k); }
  });
}

function updateTerm(t) {
  const lines = BEATS.map((b, i) => ({ who: b.term[0], msg: b.term[1], c: b.term[2], t0: S(i) + 0.3 }))
    .filter(l => t >= l.t0).slice(-4);
  linesEl.innerHTML = '';
  lines.forEach((l, i) => {
    const cur = i === lines.length - 1;
    const div = document.createElement('div');
    div.className = 'line ' + (cur ? 'cur' : 'old');
    div.style.setProperty('--c', l.c);
    const who = document.createElement('span'); who.className = 'who'; who.textContent = l.who;
    const msg = document.createElement('span'); msg.className = 'msg';
    const n = cur ? Math.floor(clamp((t - l.t0) * 38, 0, l.msg.length)) : l.msg.length;
    msg.textContent = l.msg.slice(0, n);
    div.append(who, msg);
    if (cur && (n < l.msg.length || Math.floor(t * 2) % 2 === 0)) {
      const k = document.createElement('span'); k.className = 'cursor'; div.append(k);
    }
    linesEl.appendChild(div);
  });
}

// ---------- camera ----------
function camAt(t) {
  const i = beatAt(t);
  const from = i === 0 ? CAM_START : BEATS[i - 1].cam, to = BEATS[i].cam;
  const k = i === 0 ? ease(t / (S(0) + 2.4)) : ease((t - S(i)) / 1.4);
  let p = lerp3(from.p, to.p, k);
  const tg = lerp3(from.t, to.t, k);
  let ang = 0.045 * Math.sin(t * 0.22);
  if (i === BEATS.length - 1) ang += 0.32 * ease((t - S(i)) / (TL.total - S(i)));
  const dx = p[0] - tg[0], dz = p[2] - tg[2];
  p = [tg[0] + dx * Math.cos(ang) - dz * Math.sin(ang), p[1], tg[2] + dx * Math.sin(ang) + dz * Math.cos(ang)];
  camera.position.set(...p);
  camera.lookAt(...tg);
}

// ---------- frame ----------
let hops = [], stream;
window.renderAt = (t) => {
  for (const m of allMats) m.uniforms.uTime.value = t;
  camAt(t);
  camera.updateMatrixWorld();
  setOpacity(grid, ramp(t, 0, 1.4));
  setOpacity(stars, ramp(t, 0, 1.4));
  for (const k of Object.keys(nodes)) {
    const o = nodeOpacity(k, t);
    setOpacity(nodes[k], o);
    nodes[k].visible = o > 0.003;
    const [b, off] = APPEAR[k];
    nodes[k].scale.setScalar(0.9 + 0.1 * ramp(t, S(b) + off, S(b) + off + 0.8));
  }
  hops.forEach(h => h.update(t));
  stream.update(t);
  renderer.render(scene, camera);
  updateLabels(t); updateHud(t); updateTerm(t);
  fadeEl.style.opacity = Math.max(1 - ramp(t, 0, 0.5), ramp(t, TL.total - 0.7, TL.total)).toFixed(3);
};

(async () => {
  TL = await (await fetch('./build/timeline.json')).json();
  await document.fonts.load("800 40px 'Inter'");
  await document.fonts.load("700 12px 'Inter'");
  await document.fonts.load("500 13px 'JetBrains Mono'");
  await document.fonts.ready;
  hops = HOPS.map(([b, f, to, c, off, dur]) => new Hop(f, to, c, S(b) + off, dur, E(b)));
  stream = new Stream('you', 'web', HEX.green, S(7) + 1.8, E(7));
  buildOverlays();
  window.totalDuration = TL.total;
  window.sceneReady = true;
})();
