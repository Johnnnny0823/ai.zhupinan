const $ = (s, p = document) => p.querySelector(s);
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DAY = 86400000;
const ms = iso => Date.parse(iso + 'T00:00:00Z');
let shown = 0, total = 0;

function strip(r) {
  // A zoomed view of the deadline window: window band, LINE reminders, the actual date and the gap.
  const lo = ms(r.task.start) - 18 * DAY, hi = ms(r.actual.date) + 14 * DAY;
  const pct = iso => ((ms(iso) - lo) / (hi - lo) * 100).toFixed(2);
  const months = [];
  for (let d = new Date(lo); d.getTime() <= hi; d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1))) {
    const first = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1);
    if (first >= lo) months.push([first, d.getUTCMonth() + 1]);
  }
  return `<div class="strip-axis">${months.map(([t, m]) => `<span class="strip-month" data-left="${((t - lo) / (hi - lo) * 100).toFixed(2)}">${m} 月</span>`).join('')}</div>
    <div class="strip-track">
      <span class="strip-band" data-step="2" data-left="${pct(r.task.start)}" data-width="${(pct(r.task.due) - pct(r.task.start)).toFixed(2)}"><em>可辦理 ${h(r.task.start_roc)}–${h(r.task.due_roc)}</em></span>
      ${r.reminders.map(x => `<span class="strip-ping" data-step="4" data-left="${pct(x.date)}" title="${h(x.roc)}"></span>`).join('')}
      <span class="strip-gap" data-step="5" data-left="${pct(r.task.due)}" data-width="${(pct(r.actual.date) - pct(r.task.due)).toFixed(2)}"><em>逾期 ${h(r.actual.late_days)} 天</em></span>
      <span class="strip-actual" data-step="5" data-left="${pct(r.actual.date)}"></span>
    </div>`;
}

function steps(r) {
  const fine = r.actual.fine.toLocaleString('zh-TW');
  return [
    `<div class="replay-date">${h(r.permit_start.roc)}</div><div><h2>聘僱許可生效</h2><p>上傳許可函，核對生效日。</p></div>`,
    `<div class="replay-date">規則計算</div><div><h2>${h(r.task.start_roc)} – ${h(r.task.due_roc)}</h2><p>${h(r.task.title)}</p><ol class="replay-calc">${r.task.steps.map(s => `<li>${h(s)}</li>`).join('')}</ol><p class="replay-tag">依法條計算</p></div>`,
    `<div class="replay-date">${h(r.task.start_roc)}</div><div><h2>首頁出現待辦</h2><div class="hero hero-calm replay-mini"><div class="hero-count"><span>還有</span><strong>${Math.round((ms(r.task.due) - ms(r.task.start)) / DAY)}</strong><span>天</span></div><div class="hero-body"><div class="hero-kicker">還有時間</div><h3>${h(r.task.title)}</h3><p>期限 <strong>${h(r.task.due_roc)}</strong></p></div></div></div>`,
    `<div class="replay-date">${h(r.reminders[0].roc)}–${h(r.reminders.at(-1).roc)}</div><div><h2>LINE 提醒 ${r.reminders.length} 次</h2><div class="phone"><div class="phone-bar">竹聘安 AI</div>${r.reminders.map(x => `<div class="bubble"><time>${h(x.roc)}</time>${h(x.text).replace('\n', '<br>')}</div>`).join('')}</div></div>`,
    `<div class="replay-date late">${h(r.actual.roc)}</div><div><h2>這天才去健檢</h2><p class="verdict">逾期 <strong>${h(r.actual.late_days)}</strong> 天</p></div>`,
    `<div class="replay-date">結果</div><div class="replay-compare"><section class="was"><h3>當時</h3><p class="big">罰 ${fine} 元</p><p>訴願被駁回</p></section><section class="could"><h3>有竹聘安</h3><p class="big">${h(r.task.due_roc)} 前</p><p>收到 ${r.reminders.length} 次提醒</p></section></div>`,
  ];
}

function render() {
  document.querySelectorAll('.replay-steps > li').forEach((li, i) => li.classList.toggle('on', i < shown));
  document.querySelectorAll('#strip [data-step]').forEach(el => el.classList.toggle('on', +el.dataset.step <= shown));
  $('#next').disabled = shown >= total;
  $('#prev').disabled = shown <= 1;
  const last = document.querySelectorAll('.replay-steps > li.on');
  if (last.length > 1) last[last.length - 1].scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center'});
}
const go = n => { shown = Math.max(1, Math.min(total, n)); render(); };

async function boot() {
  let r;
  try {
    const response = await fetch('/api/demo/replay', {cache: 'no-store', credentials: 'same-origin'});
    if (!response.ok) throw new Error();
    r = await response.json();
  } catch {
    $('#steps').innerHTML = '<li class="error" role="alert">現在連不到規則引擎，請確認示範伺服器有沒有開。</li>';
    return;
  }
  $('#strip').innerHTML = strip(r);
  $('#strip').querySelectorAll('[data-left]').forEach(el => { el.style.left = el.dataset.left + '%'; if (el.dataset.width) el.style.width = el.dataset.width + '%'; });
  const items = steps(r);
  total = items.length;
  $('#steps').innerHTML = items.map(x => `<li>${x}</li>`).join('');
  $('#source').textContent = r.source.title;
  $('#next').onclick = () => go(shown + 1);
  $('#prev').onclick = () => go(shown - 1);
  $('#all').onclick = () => go(total);
  $('#restart').onclick = () => { go(1); window.scrollTo({top: 0}); };
  document.addEventListener('keydown', e => {
    if (e.target.closest('input,textarea,select') || (e.key === ' ' && e.target.closest('button,a'))) return;
    if (['ArrowRight', 'PageDown', ' '].includes(e.key)) { e.preventDefault(); go(shown + 1); }
    if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); go(shown - 1); }
  });
  go(1);
}
boot();
