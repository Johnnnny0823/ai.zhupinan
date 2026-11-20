import * as THREE from '/vendor/three.module.min.js';

const $ = (s, p = document) => p.querySelector(s);
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const METRICS = {soon: '30 天內到期', week: '本週到期', overdue: '已逾期'};
const COLORS = {soon: 0x5f9a7c, week: 0xc9883a, overdue: 0xb04a3b};
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
let metric = 'soon';

async function load() {
  const [geo, demo] = await Promise.all(['/data/hsinchu-districts.json', '/data/city-demo.json']
    .map(u => fetch(u, {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error(u); return r.json(); })));
  return {geo, demo};
}

function table(geo, demo) {
  const rows = geo.districts.map(d => {
    const v = demo.districts[d.id];
    return `<tr class="${metric}"><th scope="row">${h(d.name)}</th><td>${v.soon}</td><td>${v.week}</td><td>${v.overdue}</td><td>${h(v.top)}</td></tr>`;
  }).join('');
  $('#city-table').innerHTML = `<caption class="visually-hidden">各區件數（合成示範數據）</caption><thead><tr><th scope="col">行政區</th><th scope="col">30 天內</th><th scope="col">本週</th><th scope="col">已逾期</th><th scope="col">最多的事項</th></tr></thead><tbody>${rows}</tbody>`;
}

function build({geo, demo}) {
  const host = $('#city-canvas'), labels = $('#city-labels');
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  host.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 200);
  scene.add(new THREE.HemisphereLight(0xf2efe4, 0x1c2822, 1.1));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-8, 14, 10); scene.add(sun);

  // 經緯度換成以新竹市中心為原點的公里座標。
  const all = geo.districts.flatMap(d => d.polygons.flatMap(p => p[0]));
  const lon0 = all.reduce((s, p) => s + p[0], 0) / all.length, lat0 = all.reduce((s, p) => s + p[1], 0) / all.length;
  const kx = 111.32 * Math.cos(lat0 * Math.PI / 180), ky = 110.57;
  const xy = ([lon, lat]) => [(lon - lon0) * kx, (lat - lat0) * ky];

  const city = new THREE.Group(); scene.add(city);
  const base = new THREE.Mesh(new THREE.CircleGeometry(13, 64), new THREE.MeshStandardMaterial({color: 0x24332c, roughness: 1}));
  base.rotation.x = -Math.PI / 2; base.position.y = -0.02; city.add(base);

  const items = geo.districts.map(d => {
    const shapes = d.polygons.map(poly => {
      const shape = new THREE.Shape(poly[0].map(p => new THREE.Vector2(...xy(p))));
      poly.slice(1).forEach(hole => shape.holes.push(new THREE.Path(hole.map(p => new THREE.Vector2(...xy(p))))));
      return shape;
    });
    const geom = new THREE.ExtrudeGeometry(shapes, {depth: 1, bevelEnabled: false});
    const mat = new THREE.MeshStandardMaterial({color: COLORS[metric], roughness: 0.55, metalness: 0.05});
    const mesh = new THREE.Mesh(geom, mat);
    mesh.rotation.x = -Math.PI / 2;
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom, 75), new THREE.LineBasicMaterial({color: 0xf2efe4, transparent: true, opacity: 0.35}));
    mesh.add(edges);
    city.add(mesh);
    const pts = d.polygons[0][0].map(xy);
    const c = pts.reduce((s, p) => [s[0] + p[0] / pts.length, s[1] + p[1] / pts.length], [0, 0]);
    const label = document.createElement('div'); label.className = 'city-label'; labels.append(label);
    return {d, mesh, mat, centre: new THREE.Vector3(c[0], 0, -c[1]), label, height: 0.01, target: 0.01};
  });

  const max = () => Math.max(...items.map(i => demo.districts[i.d.id][metric]));
  function retarget() {
    const m = max();
    items.forEach(i => {
      const v = demo.districts[i.d.id][metric];
      i.target = 0.3 + 6.5 * v / m;
      const c = new THREE.Color(COLORS[metric]);
      i.mat.color.copy(new THREE.Color(0x26302b).lerp(c, Math.pow(v / m, 1.6)));
      i.label.innerHTML = `<b>${h(i.d.name)}</b><span>${METRICS[metric]} ${v} 件</span>`;
      if (reduced) i.height = i.target;
    });
    table(geo, demo);
  }

  let yaw = -0.6, pitch = 0.55, dragging = null, idle = 0;
  host.addEventListener('pointerdown', e => { dragging = {x: e.clientX, y: e.clientY, yaw, pitch}; host.setPointerCapture(e.pointerId); });
  host.addEventListener('pointermove', e => {
    if (!dragging) return;
    yaw = dragging.yaw - (e.clientX - dragging.x) * 0.006;
    pitch = Math.min(1.25, Math.max(0.35, dragging.pitch + (e.clientY - dragging.y) * 0.004));
    idle = 0;
  });
  const stop = () => { dragging = null; };
  host.addEventListener('pointerup', stop); host.addEventListener('pointercancel', stop);

  function resize() {
    const w = host.clientWidth, hgt = host.clientHeight;
    renderer.setSize(w, hgt, false); camera.aspect = w / hgt; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(host); resize();

  const v = new THREE.Vector3();
  function frame() {
    if (!dragging && !reduced && ++idle > 120) yaw += 0.0012;
    const r = 30;
    camera.position.set(Math.sin(yaw) * Math.cos(pitch) * r, Math.sin(pitch) * r, Math.cos(yaw) * Math.cos(pitch) * r);
    camera.lookAt(0, 0.4, 0);
    const w = host.clientWidth, hgt = host.clientHeight;
    items.forEach(i => {
      i.height += (i.target - i.height) * 0.08;
      i.mesh.scale.z = i.height;
      v.copy(i.centre); v.y = i.height + 0.6; v.project(camera);
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
