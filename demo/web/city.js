import * as THREE from '/vendor/three.module.min.js';

const $ = (s, p = document) => p.querySelector(s);
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => n.toLocaleString('zh-TW');
const pct = v => (v.age65 / v.pop * 100).toFixed(1) + '%';
const METRICS = {
  age65: {label: '65 歲以上人口', value: v => v.age65, text: v => fmt(v.age65) + ' 人', color: 0x5f9a7c},
  age80: {label: '80 歲以上人口', value: v => v.age80, text: v => fmt(v.age80) + ' 人', color: 0xc9883a},
  ratio: {label: '65 歲以上比例', value: v => v.age65 / v.pop, text: pct, color: 0xb86a4b},
};
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
let metric = 'age65', selected = null;

async function load() {
  const [geo, stats] = await Promise.all(['/data/hsinchu-districts.json', '/data/hsinchu-age.json']
    .map(u => fetch(u, {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error(u); return r.json(); })));
  return {geo, stats};
}

// 把三區的主軸轉成水平，讓地圖橫著擺，三區都不會被擋住。
function layout(geo) {
  const all = geo.districts.flatMap(d => d.polygons.flatMap(p => p[0]));
  const lon0 = all.reduce((s, p) => s + p[0], 0) / all.length, lat0 = all.reduce((s, p) => s + p[1], 0) / all.length;
  const kx = 111.32 * Math.cos(lat0 * Math.PI / 180), ky = 110.57;
  const raw = ([lon, lat]) => [(lon - lon0) * kx, (lat - lat0) * ky];
  let sxx = 0, syy = 0, sxy = 0;
  all.map(raw).forEach(([x, y]) => { sxx += x * x; syy += y * y; sxy += x * y; });
  const a = -0.5 * Math.atan2(2 * sxy, sxx - syy), ca = Math.cos(a), sa = Math.sin(a);
  return p => { const [x, y] = raw(p); return [x * ca - y * sa, x * sa + y * ca]; };
}

function build({geo, stats}) {
  const host = $('#city-canvas'), labels = $('#city-labels');
  $('#city-source').textContent = `人口：${stats.source}。區界：${geo.source}。`;
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  host.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 300);
  scene.add(new THREE.HemisphereLight(0xf2efe4, 0x1c2822, 1.1));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-6, 14, 12); scene.add(sun);

  const xy = layout(geo);
  const city = new THREE.Group(); scene.add(city);
  const items = geo.districts.map(d => {
    const shapes = d.polygons.map(poly => {
      const shape = new THREE.Shape(poly[0].map(p => new THREE.Vector2(...xy(p))));
      poly.slice(1).forEach(hole => shape.holes.push(new THREE.Path(hole.map(p => new THREE.Vector2(...xy(p))))));
      return shape;
    });
    const geom = new THREE.ExtrudeGeometry(shapes, {depth: 1, bevelEnabled: false});
    const mat = new THREE.MeshStandardMaterial({color: 0x5f9a7c, roughness: 0.55, metalness: 0.05, emissive: 0x000000});
    const mesh = new THREE.Mesh(geom, mat);
    mesh.rotation.x = -Math.PI / 2;
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geom, 75), new THREE.LineBasicMaterial({color: 0xf2efe4, transparent: true, opacity: 0.35})));
    city.add(mesh);
    const pts = d.polygons[0][0].map(xy);
    const c = pts.reduce((s, p) => [s[0] + p[0] / pts.length, s[1] + p[1] / pts.length], [0, 0]);
    const label = document.createElement('button');
    label.className = 'city-label'; label.type = 'button';
    label.onclick = () => select(d.id);
    labels.append(label);
    mesh.userData.id = d.id;
    return {d, v: stats.districts[d.id], mesh, mat, centre: new THREE.Vector3(c[0], 0, -c[1]), label, height: 0.01, target: 0.01};
  });

  function detail() {
    const box = $('#city-detail');
    const i = items.find(x => x.d.id === selected);
    if (!i) { box.innerHTML = `<p class="city-tip">新竹市 65 歲以上 ${fmt(stats.city.age65)} 人（${(stats.city.age65 / stats.city.pop * 100).toFixed(1)}%），家庭看護工 ${fmt(stats.city.family_caregivers)} 人。點一個區看細節。</p>`; return; }
    const top = [...items].sort((a, b) => b.v.age65 / b.v.pop - a.v.age65 / a.v.pop)[0];
    box.innerHTML = `<h2>${h(i.d.name)}</h2><dl><dt>總人口</dt><dd>${fmt(i.v.pop)} 人</dd><dt>65 歲以上</dt><dd>${fmt(i.v.age65)} 人（${pct(i.v)}）</dd><dt>80 歲以上</dt><dd>${fmt(i.v.age80)} 人</dd><dt>里數</dt><dd>${i.v.villages} 里</dd></dl>${i === top ? '<p class="city-flag">這一區 65 歲以上的比例是全市最高。</p>' : ''}`;
  }
  function select(id) {
    selected = selected === id ? null : id;
    items.forEach(i => { i.mat.emissive.setHex(i.d.id === selected ? 0x3a3020 : 0x000000); i.label.classList.toggle('on', i.d.id === selected); });
    table(); detail();
  }
  function table() {
    const m = METRICS[metric];
    const rows = items.map(i => `<tr data-id="${h(i.d.id)}" class="${i.d.id === selected ? 'on' : ''}"><th scope="row">${h(i.d.name)}</th><td>${fmt(i.v.pop)}</td><td>${fmt(i.v.age65)}</td><td>${fmt(i.v.age80)}</td><td>${pct(i.v)}</td></tr>`).join('');
    $('#city-table').innerHTML = `<caption class="visually-hidden">各區人口（${h(stats.as_of)}），目前以${h(m.label)}排序顯示於地圖</caption><thead><tr><th scope="col">行政區</th><th scope="col">總人口</th><th scope="col">65 歲以上</th><th scope="col">80 歲以上</th><th scope="col">比例</th></tr></thead><tbody>${rows}</tbody>`;
    $('#city-table').querySelectorAll('tr[data-id]').forEach(tr => tr.onclick = () => select(tr.dataset.id));
  }
  function retarget() {
    const m = METRICS[metric], max = Math.max(...items.map(i => m.value(i.v))), min = Math.min(...items.map(i => m.value(i.v)));
    items.forEach(i => {
      const r = m.value(i.v) / max, spread = max === min ? 1 : (m.value(i.v) - min) / (max - min);
      i.target = 0.4 + 5.5 * (metric === 'ratio' ? 0.35 + 0.65 * spread : r);
      i.mat.color.copy(new THREE.Color(0x2c3a33).lerp(new THREE.Color(m.color), 0.25 + 0.75 * (metric === 'ratio' ? spread : Math.pow(r, 1.4))));
      i.label.innerHTML = `<b>${h(i.d.name)}</b><span>${h(m.label)} ${h(m.text(i.v))}</span>`;
      if (reduced) i.height = i.target;
    });
    table(); detail();
  }

  // 拖曳轉動；移動很少就當成點選。
  let yaw = 0, pitch = 0.82, drag = null;
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  host.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, yaw, pitch, moved: false}; host.setPointerCapture(e.pointerId); });
  host.addEventListener('pointermove', e => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 5) drag.moved = true;
    yaw = Math.max(-0.9, Math.min(0.9, drag.yaw - dx * 0.005));
    pitch = Math.min(1.3, Math.max(0.45, drag.pitch + dy * 0.004));
  });
  host.addEventListener('pointerup', e => {
    if (drag && !drag.moved) {
      const r = host.getBoundingClientRect();
      mouse.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
      ray.setFromCamera(mouse, camera);
      const hit = ray.intersectObjects(items.map(i => i.mesh), false)[0];
      if (hit) select(hit.object.userData.id);
    }
    drag = null;
  });
  host.addEventListener('pointercancel', () => { drag = null; });

  function resize() {
    const w = host.clientWidth, hgt = host.clientHeight;
    renderer.setSize(w, hgt, false); camera.aspect = w / hgt; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(host); resize();

  const v = new THREE.Vector3();
  function frame() {
    const r = camera.aspect < 1 ? 46 : 38;
    camera.position.set(Math.sin(yaw) * Math.cos(pitch) * r, Math.sin(pitch) * r, Math.cos(yaw) * Math.cos(pitch) * r);
    camera.lookAt(0, 0.6, 0);
    const w = host.clientWidth, hgt = host.clientHeight;
    items.forEach(i => {
      i.height += (i.target - i.height) * 0.08;
      i.mesh.scale.z = i.height;
      v.copy(i.centre); v.y = i.height + 0.4; v.project(camera);
      i.label.style.transform = `translate(${((v.x + 1) / 2 * w).toFixed(1)}px, ${((1 - v.y) / 2 * hgt).toFixed(1)}px) translate(-50%, -100%)`;
    });
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  document.querySelectorAll('[data-metric]').forEach(b => b.onclick = () => {
    metric = b.dataset.metric;
    document.querySelectorAll('[data-metric]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    retarget();
  });
  retarget(); frame();
  document.body.dataset.ready = '1';
}

load().then(build).catch(() => {
  $('#city-canvas').innerHTML = '<p class="error" role="alert">地圖資料讀不到，請確認示範伺服器有沒有開。</p>';
});
