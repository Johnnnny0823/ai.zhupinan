import * as THREE from '/vendor/three.module.min.js';

const $ = (s, p = document) => p.querySelector(s);
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => Math.round(n).toLocaleString('zh-TW');
const ratio = v => v.age65 / v.pop * 100;
const METRICS = {
  age65: {label: '65 歲以上', value: v => v.age65, show: n => fmt(n), unit: '人', color: 0x6fae8c},
  age80: {label: '80 歲以上', value: v => v.age80, show: n => fmt(n), unit: '人', color: 0xd9a35a},
  ratio: {label: '65 歲以上比例', value: ratio, show: n => n.toFixed(1), unit: '%', color: 0xc97a5a},
};
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
let metric = 'age65', selected = null, hovered = null;

async function load() {
  const [geo, stats] = await Promise.all(['/data/hsinchu-districts.json', '/data/hsinchu-age.json']
    .map(u => fetch(u, {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error(u); return r.json(); })));
  return {geo, stats};
}

// 依三區主軸把地圖轉成橫的，三區都不會被擋住。
function layout(geo) {
  const all = geo.districts.flatMap(d => d.polygons.flatMap(p => p[0]));
  const lon0 = all.reduce((s, p) => s + p[0], 0) / all.length, lat0 = all.reduce((s, p) => s + p[1], 0) / all.length;
  const kx = 111.32 * Math.cos(lat0 * Math.PI / 180), ky = 110.57;
  const raw = ([lon, lat]) => [(lon - lon0) * kx, (lat - lat0) * ky];
  let sxx = 0, syy = 0, sxy = 0;
  all.map(raw).forEach(([x, y]) => { sxx += x * x; syy += y * y; sxy += x * y; });
  const a = -0.5 * Math.atan2(2 * sxy, sxx - syy), ca = Math.cos(a), sa = Math.sin(a);
  const rot = ([x, y]) => [x * ca - y * sa, x * sa + y * ca];
  return {xy: p => rot(raw(p)), north: rot([0, 1])};
}

function inside(pt, ring) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) c = !c;
  }
  return c;
}

function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const g = c.getContext('2d'), grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, 'rgba(111,174,140,0.35)'); grad.addColorStop(0.55, 'rgba(111,174,140,0.08)'); grad.addColorStop(1, 'rgba(111,174,140,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

function countTo(el, from, to, show, ms = 700) {
  if (reduced) { el.textContent = show(to); return; }
  const t0 = performance.now();
  const step = t => {
    const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
    el.textContent = show(from + (to - from) * e);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function build({geo, stats}) {
  const host = $('#city-canvas'), labels = $('#city-labels');
  $('#city-source').textContent = `資料：內政部（${stats.as_of}）`;
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  host.append(renderer.domElement);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x16201b, 40, 90);
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 300);
  scene.add(new THREE.HemisphereLight(0xf2efe4, 0x1c2822, 1.1));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-6, 14, 12); scene.add(sun);

  // 地面：光暈、同心圓格線、慢慢轉的外環。
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(46, 46), new THREE.MeshBasicMaterial({map: glowTexture(), transparent: true, depthWrite: false}));
  glow.rotation.x = -Math.PI / 2; glow.position.y = -0.03; scene.add(glow);
  const grid = new THREE.PolarGridHelper(19, 24, 7, 96, 0x3f584b, 0x2a3a32); grid.position.y = -0.02; scene.add(grid);
  const halo = new THREE.Mesh(new THREE.RingGeometry(19.4, 19.6, 160, 1, 0, Math.PI * 1.6), new THREE.MeshBasicMaterial({color: 0xd9a35a, transparent: true, opacity: 0.55, side: THREE.DoubleSide}));
  halo.rotation.x = -Math.PI / 2; scene.add(halo);
  const ticks = new THREE.Group();
  for (let i = 0; i < 72; i++) {
    const a = i / 72 * Math.PI * 2, len = i % 6 ? 0.35 : 0.9;
    const g = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(Math.cos(a) * 20.2, 0, Math.sin(a) * 20.2), new THREE.Vector3(Math.cos(a) * (20.2 + len), 0, Math.sin(a) * (20.2 + len))]);
    ticks.add(new THREE.Line(g, new THREE.LineBasicMaterial({color: 0x5f7d6d, transparent: true, opacity: 0.6})));
  }
  scene.add(ticks);

  const {xy, north} = layout(geo);
  const items = geo.districts.map((d, n) => {
    const rings = d.polygons.map(poly => poly.map(r => r.map(xy)));
    const shapes = rings.map(poly => {
      const shape = new THREE.Shape(poly[0].map(p => new THREE.Vector2(...p)));
      poly.slice(1).forEach(hole => shape.holes.push(new THREE.Path(hole.map(p => new THREE.Vector2(...p)))));
      return shape;
    });
    const geom = new THREE.ExtrudeGeometry(shapes, {depth: 1, bevelEnabled: false});
    const mat = new THREE.MeshStandardMaterial({color: 0x6fae8c, roughness: 0.5, metalness: 0.05, emissive: 0x000000});
    const mesh = new THREE.Mesh(geom, mat);
    mesh.rotation.x = -Math.PI / 2;
    const edge = new THREE.LineSegments(new THREE.EdgesGeometry(geom, 75), new THREE.LineBasicMaterial({color: 0xf2efe4, transparent: true, opacity: 0.35}));
    mesh.add(edge);
    scene.add(mesh);
    const outer = rings[0][0];
    const c = outer.reduce((s, p) => [s[0] + p[0] / outer.length, s[1] + p[1] / outer.length], [0, 0]);
    // 地面上的脈衝圓環
    const pulse = new THREE.Mesh(new THREE.RingGeometry(0.5, 0.62, 48), new THREE.MeshBasicMaterial({color: 0xf2efe4, transparent: true, opacity: 0.6, side: THREE.DoubleSide}));
    pulse.rotation.x = -Math.PI / 2; pulse.position.set(c[0], 0.01, -c[1]); scene.add(pulse);
    // 從地面往上飄的光點，數量依該區人口比例
    const count = Math.round(40 + 140 * stats.districts[d.id].age65 / stats.city.age65);
    const xs = [], ys = [], zs = [];
    const [minx, maxx] = [Math.min(...outer.map(p => p[0])), Math.max(...outer.map(p => p[0]))];
    const [miny, maxy] = [Math.min(...outer.map(p => p[1])), Math.max(...outer.map(p => p[1]))];
    while (xs.length < count) {
      const p = [minx + Math.random() * (maxx - minx), miny + Math.random() * (maxy - miny)];
      if (inside(p, outer)) { xs.push(p[0]); zs.push(-p[1]); ys.push(Math.random()); }
    }
    const pos = new Float32Array(count * 3);
    const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const dots = new THREE.Points(pg, new THREE.PointsMaterial({color: 0xfff3dc, size: 0.14, transparent: true, opacity: 0.85, depthWrite: false}));
    scene.add(dots);
    const label = document.createElement('button');
    label.className = 'city-label'; label.type = 'button';
    label.onclick = () => select(d.id);
    label.onmouseenter = () => hover(d.id); label.onmouseleave = () => hover(null);
    labels.append(label);
    mesh.userData.id = d.id;
    return {d, v: stats.districts[d.id], mesh, mat, edge, pulse, phase: n / 3, dots, xs, ys, zs, pos,
            centre: new THREE.Vector3(c[0], 0, -c[1]), label, height: 0.01, target: 0.01};
  });

  const statValue = $('#stat-value');
  let shown = 0;
  function stat() {
    const m = METRICS[metric];
    const i = items.find(x => x.d.id === selected);
    const value = i ? m.value(i.v) : m.value(stats.city);
    $('#stat-label').textContent = m.label;
    $('#stat-where').textContent = `${m.unit} · ${i ? i.d.name : '新竹市'}`;
    countTo(statValue, shown, value, m.show); shown = value;
  }
  function detail() {
    const box = $('#city-detail');
    const i = items.find(x => x.d.id === selected);
    if (!i) { box.innerHTML = '<p class="city-tip">點地圖上的區</p>'; box.classList.remove('open'); return; }
    const top = [...items].sort((a, b) => ratio(b.v) - ratio(a.v))[0];
    box.classList.add('open');
    box.innerHTML = `<h2>${h(i.d.name)}${i === top ? '<span class="city-badge">比例最高</span>' : ''}</h2><dl><dt>總人口</dt><dd>${fmt(i.v.pop)}</dd><dt>65 歲以上</dt><dd>${fmt(i.v.age65)}</dd><dt>80 歲以上</dt><dd>${fmt(i.v.age80)}</dd><dt>比例</dt><dd>${ratio(i.v).toFixed(1)}%</dd></dl>`;
  }
  function table() {
    const rows = items.map(i => `<tr data-id="${h(i.d.id)}" class="${i.d.id === selected ? 'on' : ''}"><th scope="row">${h(i.d.name)}</th><td>${fmt(i.v.age65)}</td><td>${fmt(i.v.age80)}</td><td>${ratio(i.v).toFixed(1)}%</td></tr>`).join('');
    $('#city-table').innerHTML = `<caption class="visually-hidden">各區人口</caption><thead><tr><th scope="col">區</th><th scope="col">65+</th><th scope="col">80+</th><th scope="col">比例</th></tr></thead><tbody>${rows}</tbody>`;
    $('#city-table').querySelectorAll('tr[data-id]').forEach(tr => {
      tr.onclick = () => select(tr.dataset.id);
      tr.onmouseenter = () => hover(tr.dataset.id); tr.onmouseleave = () => hover(null);
    });
  }
  function paint() {
    items.forEach(i => {
      const on = i.d.id === selected, over = i.d.id === hovered;
      i.mat.emissive.setHex(on ? 0x4a3418 : over ? 0x24382d : 0x000000);
      i.edge.material.opacity = on || over ? 0.9 : 0.35;
      i.label.classList.toggle('on', on); i.label.classList.toggle('hover', over && !on);
    });
    host.style.cursor = hovered ? 'pointer' : 'grab';
  }
  function hover(id) { if (hovered !== id) { hovered = id; paint(); } }
  function select(id) {
    selected = selected === id ? null : id;
    paint(); table(); detail(); stat();
  }
  function retarget() {
    const m = METRICS[metric], vals = items.map(i => m.value(i.v)), max = Math.max(...vals), min = Math.min(...vals);
    items.forEach(i => {
      const v = m.value(i.v), r = v / max, spread = max === min ? 1 : (v - min) / (max - min);
      i.target = 0.4 + 5.5 * (metric === 'ratio' ? 0.35 + 0.65 * spread : r);
      i.mat.color.copy(new THREE.Color(0x2c3a33).lerp(new THREE.Color(m.color), 0.25 + 0.75 * (metric === 'ratio' ? spread : Math.pow(r, 1.4))));
      i.label.innerHTML = `<b>${h(i.d.name)}</b><span>${h(m.show(v))}${m.unit === '%' ? '%' : ' 人'}</span>`;
      if (reduced) i.height = i.target;
    });
    table(); detail(); stat();
  }

  // 拖曳轉動；幾乎沒移動就算點選。點一區鏡頭會靠過去。
  let yaw = 0, pitch = 0.8, drag = null;
  const focus = new THREE.Vector3(0, 0.6, 0), aim = new THREE.Vector3(0, 0.6, 0);
  let dist = 40;
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  const pick = e => {
    const r = host.getBoundingClientRect();
    mouse.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObjects(items.map(i => i.mesh), false)[0];
    return hit ? hit.object.userData.id : null;
  };
  host.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, yaw, pitch, moved: false}; host.setPointerCapture(e.pointerId); });
  host.addEventListener('pointermove', e => {
    if (!drag) { hover(pick(e)); return; }
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 5) drag.moved = true;
    yaw = Math.max(-1, Math.min(1, drag.yaw - dx * 0.005));
    pitch = Math.min(1.3, Math.max(0.45, drag.pitch + dy * 0.004));
  });
  host.addEventListener('pointerup', e => {
    if (drag && !drag.moved) { const id = pick(e); select(id && id !== selected ? id : null); }
    drag = null;
  });
  host.addEventListener('pointercancel', () => { drag = null; });
  host.addEventListener('pointerleave', () => hover(null));

  function resize() {
    const w = host.clientWidth, hgt = host.clientHeight;
    renderer.setSize(w, hgt, false); camera.aspect = w / hgt; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(host); resize();

  const compass = $('.city-compass'), v = new THREE.Vector3(), w2 = new THREE.Vector3();
  let last = performance.now() / 1000;
  function frame() {
    const t = performance.now() / 1000, dt = Math.min(t - last, 0.05); last = t;
    const sel = items.find(x => x.d.id === selected);
    aim.set(sel ? sel.centre.x * 0.45 : 0, 0.6, sel ? sel.centre.z * 0.45 : 0);
    focus.lerp(aim, 0.06);
    const want = (camera.aspect < 1 ? 58 : 40) * (sel ? 0.86 : 1);
    dist += (want - dist) * 0.06;
    camera.position.set(focus.x + Math.sin(yaw) * Math.cos(pitch) * dist, Math.sin(pitch) * dist, focus.z + Math.cos(yaw) * Math.cos(pitch) * dist);
    camera.lookAt(focus);
    const W = host.clientWidth, H = host.clientHeight;
    if (!reduced) { halo.rotation.z = t * 0.05; ticks.rotation.y = -t * 0.02; }
    items.forEach(i => {
      i.height += (i.target - i.height) * 0.08;
      i.mesh.scale.z = i.height;
      // 脈衝圓環
      const k = reduced ? 0.4 : (t * 0.45 + i.phase) % 1;
      i.pulse.scale.setScalar(1 + k * 5); i.pulse.material.opacity = 0.55 * (1 - k);
      // 光點往上飄，飄出區塊頂端就回到底部
      for (let j = 0; j < i.xs.length; j++) {
        if (!reduced) i.ys[j] = (i.ys[j] + dt * 0.12) % 1;
        i.pos[j * 3] = i.xs[j]; i.pos[j * 3 + 1] = i.height + 0.1 + i.ys[j] * 3.2; i.pos[j * 3 + 2] = i.zs[j];
      }
      i.dots.geometry.attributes.position.needsUpdate = true;
      i.dots.material.opacity = 0.75 * (i.d.id === selected || !selected ? 1 : 0.35);
      v.copy(i.centre); v.y = i.height + 0.4; v.project(camera);
      i.label.style.transform = `translate(${((v.x + 1) / 2 * W).toFixed(1)}px, ${((1 - v.y) / 2 * H).toFixed(1)}px) translate(-50%, -100%)`;
    });
    // 指北針跟著鏡頭轉
    v.set(0, 0, 0).project(camera); w2.set(north[0] * 5, 0, -north[1] * 5).project(camera);
    compass.style.transform = `rotate(${Math.atan2(w2.x - v.x, w2.y - v.y)}rad)`;
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  document.querySelectorAll('[data-metric]').forEach(b => b.onclick = () => {
    metric = b.dataset.metric;
    document.querySelectorAll('[data-metric]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    retarget();
  });
  retarget(); paint(); frame();
  document.body.dataset.ready = '1';
}

load().then(build).catch(() => {
  $('#city-canvas').innerHTML = '<p class="error" role="alert">地圖讀不到，請確認伺服器有開。</p>';
});
