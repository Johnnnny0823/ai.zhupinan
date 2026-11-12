'use strict';
const $ = id => document.getElementById(id);
const all = sel => [...document.querySelectorAll(sel)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let role = 'employer';
let toastTimer;
let lastExtract = null;

function notify(msg) {
  const t = $('toast'); t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 5000);
}

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  let data = null;
  try { data = await r.json(); } catch { /* ignore */ }
  if (!r.ok) throw new Error((data && data.detail) || `伺服器錯誤（${r.status}）`);
  return data;
}

/* ---------------- navigation ---------------- */
function showView(name) {
  const permitted = role === 'employer' ? ['upload', 'tasks', 'chat', 'line'] : ['review', 'chat'];
  if (!permitted.includes(name)) return;
  all('.view').forEach(v => { v.hidden = v.id !== 'view-' + name; });
  all('.nav-item').forEach(b => {
    const on = b.dataset.view === name;
    b.classList.toggle('active', on);
    if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  window.scrollTo({ top: 0, behavior: 'instant' });
  if (name === 'tasks') loadTodos();
  if (name === 'line') loadLine();
}
all('[data-role]').forEach(btn => btn.addEventListener('click', () => {
  role = btn.dataset.role;
  document.body.classList.toggle('officer', role === 'officer');
  all('[data-role]').forEach(b => { const on = b.dataset.role === role; b.classList.toggle('active', on); b.setAttribute('aria-pressed', String(on)); });
  all('[data-access]').forEach(el => { el.hidden = el.dataset.access !== 'both' && el.dataset.access !== role; });
  const label = role === 'employer' ? '雇主專區' : '市府承辦人專區';
  $('role-label').textContent = label; $('chat-role').textContent = label;
  showView(role === 'employer' ? 'upload' : 'review');
}));
all('[data-view]').forEach(b => b.addEventListener('click', () => showView(b.dataset.view)));
all('[data-goto]').forEach(b => b.addEventListener('click', () => showView(b.dataset.goto)));
document.querySelector('.brand').addEventListener('click', e => { e.preventDefault(); showView(role === 'employer' ? 'upload' : 'review'); });

/* ---------------- health ---------------- */
(async () => {
  const b = $('health-badge');
  try {
    const h = await api('/api/health');
    b.classList.add('health-ok');
    b.innerHTML = `<span></span>系統連線正常・法條 ${h.articles} 條・辦公日曆 ${h.calendar_years.join('、')}`;
    $('cal-years').textContent = h.calendar_years.map(y => `${y - 1911} 年`).join('、');
  } catch {
    b.classList.add('health-bad'); b.innerHTML = '<span></span>後端未連線';
  }
  refreshCount();
})();

/* ---------------- upload & extract ---------------- */
const SAMPLES = [
  ['聘僱許可函_掃描.png', '聘僱許可函（掃描圖片）', '圖片改用較強模型判讀'],
  ['聘僱許可函_國字日期.txt', '聘僱許可函（國字日期）', '例：一一五年…'],
  ['入國通報證明_國字日期.txt', '入國通報受理證明書（國字日期）', ''],
  ['入國通報證明_春節連假.txt', '入國通報受理證明書（遇春節）', '期限遇連假自動順延'],
  ['住宿地點變更_掃描.png', '住宿地點變更表（掃描，2 位移工）', ''],
];
/* samples dated relative to today, so LINE reminders fire immediately during the demo */
const rocDate = d => `${d.getFullYear() - 1911}年${d.getMonth() + 1}月${d.getDate()}日`;
const daysAgo = n => { const d = new Date(); d.setDate(d.getDate() - n); return d; };
const DYNAMIC = {
  'live:entry': () => ['入國通報證明_昨天入國.txt', [
    '【合成測試文件・非真實公文・僅供竹聘安 AI 驗證使用】', '新竹市政府', '受理雇主聘僱外國人入國通報證明書',
    '證明書字號：府勞外字第1159990001號', '雇主名稱：風城精密工業股份有限公司', '雇主地址：新竹市東區光復路一段100號',
    '外國人姓名：PUTRI AYU LESTARI', '國籍：印尼', '護照號碼：C7788123',
    `入國日期：${rocDate(daysAgo(1))}`, `通報日期：${rocDate(daysAgo(0))}`, '住宿地點：新竹市北區中正路200號',
    '', '茲證明上開雇主已依雇主聘僱外國人許可及管理辦法第34條規定辦理入國通報。', '', `中華民國${rocDate(daysAgo(0))}`].join('\n')],
  'live:dorm': () => ['住宿地點變更_前天搬遷.txt', [
    '【合成測試文件・非真實公文・僅供竹聘安 AI 驗證使用】',
    '外國人生活照顧服務計畫書　變更事項表（第五款：住宿地點及生活照顧服務人員）',
    '雇主名稱：竹塹電子材料股份有限公司', `填表日期：${rocDate(daysAgo(1))}`, '',
    '原住宿地點：新竹市香山區西濱路一段50號', '新住宿地點：新竹市東區經國路一段300號',
    `新宿舍租賃契約起租日：${rocDate(daysAgo(15))}`, `外國人遷入新住宿地點日期（變更日）：${rocDate(daysAgo(2))}`,
    '', '異動外國人：', '（1）NGUYEN VAN AN　越南　護照號碼 B5566778', '（2）TRAN THI HONG　越南　護照號碼 B5566779'].join('\n')],
};
SAMPLES.unshift(['live:entry', '★ 昨天剛入國的移工（現場展示用）', '依今天日期產生，期限就在這幾天'],
                ['live:dorm', '★ 前天搬宿舍（現場展示用）', '7 日內須通報，可立即測 LINE 推播']);
$('sample-buttons').innerHTML = SAMPLES.map(([f, t, s]) => `<button type="button" data-sample="${esc(f)}">${esc(t)}${s ? `<small>${esc(s)}</small>` : ''}</button>`).join('');
all('[data-sample]').forEach(b => b.addEventListener('click', async () => {
  const name = b.dataset.sample;
  if (DYNAMIC[name]) {
    const [fname, text] = DYNAMIC[name]();
    uploadDocument(new File([text], fname, { type: 'text/plain' }));
    return;
  }
  const blob = await (await fetch('samples/' + encodeURIComponent(name))).blob();
  uploadDocument(new File([blob], name, { type: blob.type }));
}));
$('document-input').addEventListener('change', e => uploadDocument(e.target.files[0]));
const dz = $('dropzone');
['dragenter', 'dragover'].forEach(n => dz.addEventListener(n, e => { e.preventDefault(); dz.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(n => dz.addEventListener(n, e => {
  e.preventDefault(); dz.classList.remove('dragging');
  if (n === 'drop') uploadDocument(e.dataTransfer.files[0]);
}));

function setStep(n) {
  all('#stepper li').forEach((li, i) => { li.classList.toggle('current', i === n - 1); li.classList.toggle('done', i < n - 1); });
}

async function uploadDocument(file) {
  if (!file) return;
  if (!/\.(jpe?g|png|pdf|txt)$/i.test(file.name)) { notify('請選擇 JPG、PNG、PDF 或 TXT 檔案。'); return; }
  $('uploaded-file').hidden = false;
  $('uploaded-name').textContent = file.name;
  $('upload-description').textContent = `${(file.size / 1024).toFixed(0)} KB`;
  $('upload-status').className = 'status warning'; $('upload-status').textContent = '辨識中';
  $('extract-empty').hidden = true; $('worker-form').hidden = true; $('result-card').hidden = true;
  $('extract-loading').hidden = false;
  const isImg = /\.(jpe?g|png)$/i.test(file.name);
  $('loading-text').textContent = isImg ? 'AI 正在閱讀掃描圖片…（約 20～40 秒）' : 'AI 正在閱讀公文…（約 10～20 秒）';
  $('flag-count').className = 'status neutral'; $('flag-count').textContent = '辨識中';
  setStep(1);
  const fd = new FormData(); fd.append('file', file);
  try {
    const data = await api('/api/extract', { method: 'POST', body: fd });
    lastExtract = data;
    renderExtract(data);
    $('upload-status').className = 'status ok'; $('upload-status').textContent = '已完成辨識';
    setStep(2);
  } catch (err) {
    $('extract-loading').hidden = true; $('extract-empty').hidden = false;
    $('upload-status').className = 'status danger'; $('upload-status').textContent = '辨識失敗';
    $('flag-count').textContent = '辨識失敗';
    notify(err.message);
  }
}

const FIELDS = {
  '聘僱許可函': [['entry_date', '入國日'], ['permit_start', '許可起日'], ['permit_end', '許可迄日']],
  '期滿續聘許可函': [['permit_start', '許可起日'], ['permit_end', '許可迄日']],
  '入國通報受理證明書': [['entry_date', '入國日']],
  '再檢查診斷證明書': [['event_date', '雇主收文日']],
  '住宿地點變更': [['event_date', '遷入新住處日（變更日）']],
  '聘僱關係終止': [['event_date', '聘僱關係終止日']],
};

function renderExtract(data) {
  $('extract-loading').hidden = true;
  $('worker-form').hidden = false;
  const sel = $('doc-type');
  if ([...sel.options].some(o => o.value === data.doc_type)) sel.value = data.doc_type;
  renderWorkerTable();
  const flags = (data.workers || []).reduce((n, w) => n + Object.keys(w.flags || {}).length, 0);
  $('flag-count').className = 'status ' + (flags ? 'warning' : 'ok');
  $('flag-count').textContent = flags ? `${flags} 項請再確認` : '辨識完成';
  $('model-note').textContent = `${data.is_image ? '掃描圖片' : '文字公文'}・使用 Claude ${data.model === 'sonnet' ? 'Sonnet' : 'Haiku'} 判讀・請以原件核對`;
  const btn = document.querySelector('#worker-form button[type=submit]');
  btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
  btn.classList.add('pulse');
  setTimeout(() => btn.classList.remove('pulse'), 4000);
  notify('AI 已讀完公文。請核對日期，再按右下角「確認無誤，產生待辦」。');
}

function renderWorkerTable() {
  const type = $('doc-type').value;
  const fields = FIELDS[type] || [];
  $('worker-head').innerHTML = `<tr><th>移工姓名</th>${fields.map(([, l]) => `<th>${esc(l)}</th>`).join('')}</tr>`;
  const workers = (lastExtract && lastExtract.workers) || [];
  $('worker-rows').innerHTML = workers.map((w, i) => `<tr data-i="${i}">
      <td><input type="text" data-k="name" value="${esc(w.name)}" required><span class="worker-meta">移工 ${String(i + 1).padStart(2, '0')}</span></td>
      ${fields.map(([k]) => {
        const flag = (w.flags || {})[k];
        const src = (w.evidence || {})[k];
        return `<td class="${flag ? 'flagged' : ''}"><input type="date" data-k="${k}" value="${esc(w[k] || '')}">
          ${src ? `<small>原文：「${esc(src)}」</small>` : (w[k] ? '' : '<small>文件中未找到</small>')}
          ${flag ? `<span class="field-warning">${esc(flag)}</span>` : ''}</td>`;
      }).join('')}</tr>`).join('');
}
$('doc-type').addEventListener('change', renderWorkerTable);

$('worker-form').addEventListener('submit', async e => {
  e.preventDefault();
  const type = $('doc-type').value;
  const workers = all('#worker-rows tr').map(tr => {
    const w = { name: '', entry_date: null, permit_start: null, permit_end: null, event_date: null };
    tr.querySelectorAll('input[data-k]').forEach(inp => { w[inp.dataset.k] = inp.value || (inp.dataset.k === 'name' ? '' : null); });
    return w;
  });
  if (workers.some(w => w.permit_start && w.permit_end && w.permit_start > w.permit_end)) { notify('聘僱許可迄日不得早於起日，請再次核對。'); return; }
  if (workers.some(w => (FIELDS[type] || []).every(([k]) => !w[k]))) { notify('請至少填入一個日期。'); return; }
  const btn = e.submitter || document.querySelector('#worker-form button[type=submit]');
  const btnHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner small-spinner"></span>產生中…';
  try {
    const r = await api('/api/obligations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ doc_type: type, workers, save: true }) });
    const total = r.obligations.length;
    const msg = r.added === total ? `已加入 ${total} 項待辦`
      : r.added === 0 ? `這 ${total} 項待辦先前已加入過，未重複新增` : `已新增 ${r.added} 項待辦（${total - r.added} 項先前已加入過）`;
    renderObligations(r.obligations, workers, msg, r.added > 0);
    setStep(3);
    refreshCount(true);
    btn.classList.add('done');
    btn.innerHTML = `✓ ${r.added > 0 ? `已加入 ${r.added} 項待辦` : '先前已加入過'}`;
    notify(msg + '，可到「我的待辦」或「LINE 提醒」查看。');
    setTimeout(() => { btn.classList.remove('done'); btn.innerHTML = btnHtml; btn.disabled = false; }, 3000);
  } catch (err) {
    btn.innerHTML = btnHtml; btn.disabled = false;
    notify('產生待辦失敗：' + err.message);
  }
});

function statusChip(o) {
  const startLeft = o.start ? daysBetween(today(), o.start) : null;
  if (o.days_left < 0) return ['danger', `已逾期 ${-o.days_left} 天`];
  if (startLeft !== null && startLeft > 0) return [startLeft <= 30 ? 'warning' : 'neutral', `${startLeft} 天後開始`];
  if (o.days_left <= 7) return ['danger', `剩 ${o.days_left} 天`];
  if (o.days_left <= 30) return ['warning', `剩 ${o.days_left} 天`];
  return ['neutral', `剩 ${o.days_left} 天`];
}
const today = () => new Date().toISOString().slice(0, 10);
const daysBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);

function renderObligations(list, workers, msg = '', added = true) {
  $('result-card').hidden = false;
  $('result-sub').textContent = workers.map(w => w.name).join('、');
  const banner = msg ? `<div class="success-banner ${added ? '' : 'info'}"><span class="success-icon">${added ? '✓' : 'i'}</span>
      <div><strong>${esc(msg)}</strong><small>${added ? '已存入「我的待辦」，期限快到時會透過 LINE 提醒' : '「我的待辦」中已有這些項目'}</small></div>
      <div class="banner-actions"><button type="button" class="button secondary" data-goto="tasks">前往我的待辦</button><button type="button" class="button primary" data-goto="line">推播到 LINE</button></div></div>` : '';
  $('obligation-list').innerHTML = banner + (list.length ? list.map(o => {
    const [cls, txt] = statusChip(o);
    const when = o.start ? `${o.start} ～ ${o.due}` : `${o.due} 前`;
    return `<div class="obligation"><div class="task-icon"><svg><use href="#i-${o.key.startsWith('health') ? 'shield' : 'file'}"/></svg></div>
      <div class="obligation-name"><strong>${esc(o.title)}</strong><small>${esc(o.worker)}・${esc(o.basis)}</small>${o.note ? `<span class="note">${esc(o.note)}</span>` : ''}</div>
      <div class="deadline"><strong>${esc(when)}</strong><small>${o.start ? '辦理期間' : '最後期限'}</small></div>
      <span class="status ${cls}">${esc(txt)}</span></div>`;
  }).join('') : '<p class="empty-state">這份文件沒有觸發需要追蹤的法定期限。</p>');
  all('#obligation-list [data-goto]').forEach(b => b.addEventListener('click', () => showView(b.dataset.goto)));
  $('result-card').classList.remove('flash'); void $('result-card').offsetWidth; $('result-card').classList.add('flash');
  $('result-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---------------- todos ---------------- */
let todoItems = [];
async function refreshCount(bump = false) {
  try {
    const t = await api('/api/todos');
    const el = $('nav-count');
    el.textContent = t.items.length;
    el.title = '待辦總數';
    if (bump) { el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump'); }
  } catch { /* ignore */ }
}
async function loadTodos() {
  try {
    const t = await api('/api/todos');
    todoItems = t.items;
    $('sum-workers').innerHTML = `${t.workers.length} <small>位</small>`;
    const soon = t.items.filter(o => o.days_left >= 0 && o.days_left <= 30).length;
    const over = t.items.filter(o => o.days_left < 0).length;
    $('sum-soon').innerHTML = `${soon} <small>項</small>`;
    $('sum-overdue').innerHTML = `${over} <small>項</small>`;
    $('sum-overdue').className = over ? 'red' : 'green';
    $('sum-overdue-note').textContent = over ? '請儘速辦理或確認是否已完成' : '目前沒有逾期待辦';
    renderTodoRows('all');
    $('nav-count').textContent = t.items.length;
  } catch (err) { notify(err.message); }
}
function renderTodoRows(filter) {
  const rows = todoItems.filter(o => filter === 'all' || (filter === 'soon' && o.days_left >= 0 && o.days_left <= 30) || (filter === 'overdue' && o.days_left < 0));
  $('task-rows').innerHTML = rows.map(o => {
    const [cls, txt] = statusChip(o);
    return `<tr><td><strong>${esc(o.title)}</strong><small>${esc(o.basis)}</small></td><td>${esc(o.worker)}</td><td>${esc(o.start ? `${o.start} ～ ${o.due}` : o.due)}</td><td><span class="status ${cls}">${esc(txt)}</span></td></tr>`;
  }).join('');
  $('empty-tasks').hidden = rows.length > 0;
}
all('[data-filter]').forEach(b => b.addEventListener('click', () => {
  all('[data-filter]').forEach(x => { const on = x === b; x.classList.toggle('active', on); x.setAttribute('aria-pressed', String(on)); });
  renderTodoRows(b.dataset.filter);
}));
$('clear-todos').addEventListener('click', async () => {
  if (!confirm('確定清除所有展示用待辦資料？')) return;
  await api('/api/todos', { method: 'DELETE' }); loadTodos(); notify('已清除展示資料。');
});

/* ---------------- chat ---------------- */
function mdLite(s) {
  return esc(s).replace(/^#+\s*(.*)$/gm, '<strong>$1</strong>').replace(/\*\*(.+?)\*\*/g, '<strong class="answer-highlight">$1</strong>').replace(/^---$/gm, '');
}
all('[data-question]').forEach(b => b.addEventListener('click', () => { $('question').value = b.dataset.question; $('chat-form').requestSubmit(); }));
$('chat-form').addEventListener('submit', async e => {
  e.preventDefault();
  const q = $('question').value.trim(); if (!q) return;
  const box = $('messages');
  box.insertAdjacentHTML('beforeend', `<div class="message user"><span class="message-label">您</span><div>${esc(q)}</div></div>`);
  const pending = document.createElement('div');
  pending.className = 'message assistant';
  pending.innerHTML = '<span class="message-label">竹聘安 AI</span><div class="assistant-bubble"><span class="spinner" style="width:20px;height:20px"></span> 正在查找相關條文…</div>';
  box.append(pending); box.scrollTop = box.scrollHeight;
  $('question').value = ''; $('ask-btn').disabled = true;
  try {
    const r = await api('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q }) });
    const cites = r.citations.map((c, i) => `<details class="citation" ${i === 0 ? 'open' : ''}><summary>引用條文 <span>${esc(c.law)}${esc(c.no)}</span></summary><div><strong>${esc(c.law)} ${esc(c.no)}</strong><blockquote>${esc(c.text)}</blockquote></div></details>`).join('');
    pending.querySelector('.assistant-bubble').innerHTML = `<div class="answer-text">${mdLite(r.answer)}</div>${cites}<small class="disclaimer">本回答依法條原文產生，非正式法律意見</small>`;
  } catch (err) {
    pending.querySelector('.assistant-bubble').textContent = '抱歉，查詢失敗：' + err.message;
  }
  $('ask-btn').disabled = false; box.scrollTop = box.scrollHeight;
});

/* ---------------- LINE ---------------- */
const lineDays = () => Number((document.querySelector('input[name=days]:checked') || {}).value || 30);
const lineLang = () => (document.querySelector('input[name=language]:checked') || {}).value || 'zh';
async function loadLine() {
  try {
    const s = await api('/api/line/status');
    $('line-status-tag').textContent = s.configured ? `已連接 LINE 官方帳號・好友 ${s.followers} 人` : '尚未連接 LINE（預覽模式）';
    $('line-send').textContent = s.configured ? '產生提醒並推播到 LINE' : '產生提醒預覽';
    $('phone-note').textContent = s.configured ? '實際推播內容預覽' : 'LINE 對話預覽・設定 Messaging API 後即可實際推播';
  } catch { /* ignore */ }
  renderPhone();
}
async function renderPhone() {
  try {
    const p = await api(`/api/line/preview?days=${lineDays()}&lang=${lineLang()}`);
    const d = new Date();
    $('phone-chat').innerHTML = `<div class="phone-date">${d.getMonth() + 1} 月 ${d.getDate()} 日</div>` + (p.count ? `<div class="line-message"><span class="line-avatar">竹</span><div class="line-bubble"><p>${esc(p.text)}</p><div class="line-buttons"><button type="button" class="mark-done">已讀</button><button type="button" data-goto-tasks>查看全部</button></div></div></div>` : '<p class="line-detail">目前範圍內沒有需要提醒的待辦。請先到「上傳公文」產生待辦，或放寬提醒範圍。</p>');
    all('[data-goto-tasks]').forEach(b => b.addEventListener('click', () => showView('tasks')));
    all('.mark-done').forEach(b => b.addEventListener('click', () => { b.textContent = '已標記完成'; b.disabled = true; }));
  } catch (err) { notify(err.message); }
}
all('input[name=days], input[name=language]').forEach(i => i.addEventListener('change', renderPhone));
$('settings-form').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    const r = await api('/api/line/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ days: lineDays(), lang: lineLang() }) });
    $('line-result').textContent = r.note || '';
    loadLine();
    renderPhone();
  } catch (err) { notify(err.message); }
});

/* ---------------- penalty review ---------------- */
$('load-draft').addEventListener('click', async () => {
  const t = await (await fetch('samples/' + encodeURIComponent('裁處書草稿_範例.txt'))).text();
  $('draft').value = t; notify('已載入範例草稿（合成資料）。');
});
const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦'];
$('check-draft').addEventListener('click', async () => {
  const text = $('draft').value.trim();
  if (text.length < 30) { notify('請先貼上裁處書草稿，或載入範例草稿。'); return; }
  $('check-loading').hidden = false; $('checklist').innerHTML = ''; $('suggestion-card').hidden = true;
  $('check-summary').className = 'status neutral'; $('check-summary').textContent = '檢核中'; $('check-draft').disabled = true;
  try {
    const r = await api('/api/check-penalty', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
    const fails = r.items.filter(i => i.ok === false);
    $('checklist').innerHTML = r.items.map((it, i) => `<li class="check-item ${it.ok === false ? 'check-fail' : ''}">
      <div class="check-row"><span>${CIRCLED[i]}</span><strong>${esc(it.name)}</strong>
      ${it.ok === true ? '<span class="check-state check-pass">✓ 符合</span>' : it.ok === false ? '<span class="check-state">✕ 需修正</span>' : '<span class="check-state check-unknown">？未判定</span>'}</div>
      <p class="reason">${esc(it.reason || '')}</p></li>`).join('');
    $('check-progress').style.width = `${Math.round(100 * (7 - fails.length) / 7)}%`;
    $('check-summary').className = 'status ' + (fails.length ? 'danger' : 'ok');
    $('check-summary').textContent = fails.length ? `${fails.length} 項需修正` : '7 項皆符合';
    const fixes = fails.filter(f => f.fix);
    if (fixes.length) {
      $('suggestion-card').hidden = false;
      $('suggestions').innerHTML = fixes.map(f => `<div class="fix-item"><strong>${esc(f.name)}</strong><p>${esc(f.fix)}</p><button class="text-button" type="button" data-copy="${esc(f.fix)}">複製文字</button></div>`).join('');
      all('[data-copy]').forEach(b => b.addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(b.dataset.copy); notify('已複製，請依個案確認後採用。'); } catch { notify('無法自動複製，請手動選取文字。'); }
      }));
    }
  } catch (err) {
    $('check-summary').className = 'status danger'; $('check-summary').textContent = '檢核失敗'; notify(err.message);
  }
  $('check-loading').hidden = true; $('check-draft').disabled = false;
});
