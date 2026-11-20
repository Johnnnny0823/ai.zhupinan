const $ = (s, p = document) => p.querySelector(s);
const main = $('#main');
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state = {account:null, page:'tasks', cases:[], tasks:[], caseId:'', filter:'all', draft:null, proof:null, selected:null};
const labels = {todo:'待辦理',delegated:'已委任',proof_submitted:'待雇主確認',done:'已完成',needs_review:'需人工確認'};
const fieldLabels = {entry_date:'入國日期',permit_start:'聘僱許可起日',permit_end:'聘僱許可迄日',event_date:'事件／收受日期',notify_date:'實際通報日期'};
let busy = false;

async function api(path, options = {}) {
  let headers = {...options.headers};
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(options.body);
  }
  let response;
  try { response = await fetch(path, {...options,headers,cache:'no-store',credentials:'same-origin'}); }
  catch { throw new Error('目前無法讀取個案資料。請檢查網路，或開啟公開的預存展示頁。'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.account) { clearState(); loginPage(); }
    const failure = new Error(typeof data.detail === 'string' ? data.detail : '欄位格式有誤，請核對後再試。');
    failure.status = response.status;
    failure.unchecked = Array.isArray(data.unchecked) ? data.unchecked : [];
    throw failure;
  }
  return data;
}
function notice(text) {
  const toast = $('#toast'); toast.textContent = text; toast.hidden = false;
  clearTimeout(notice.timer); notice.timer = setTimeout(() => toast.hidden = true,5000);
}
function error(message, target = main) {
  $('.error',target)?.remove();
  const el=document.createElement('div');el.className='error';el.setAttribute('role','alert');el.tabIndex=-1;
  el.innerHTML=`<h2>這一步還沒完成</h2><p>${h(message)}</p><p><a href="/local-demo.html">開啟預存展示頁</a></p>`;
  target.prepend(el);el.focus();
}
function clearState() {
  state={account:null,page:'tasks',cases:[],tasks:[],caseId:'',filter:'all',draft:null,proof:null,selected:null};
  $('#navigation').hidden=true; $('#identity').replaceChildren();main.replaceChildren();
}
function heading(eyebrow,title,description='') {
  return `<div class="page-heading"><div><div class="eyebrow">${h(eyebrow)} · 合成示範</div><h1>${h(title)}</h1><p>${h(description)}</p></div></div>`;
}
function focusPage() { main.focus(); window.scrollTo({top:0,behavior:'instant'}); }
function identity() {
  $('#identity').innerHTML=`<span>${h(state.account.display_name)}</span><button class="quiet" id="logout">登出 ↗</button>`;
  $('#logout').onclick=async()=>{
    try { await api('/api/session',{method:'DELETE'}); }
    catch(e) { error(e.message); return; }
    clearState();loginPage();
  };
}
function navigation() {
  const officer=state.account.role==='officer';
  const items=officer?[['penalty','草稿檢核'],['qa','法規問答']]:[['tasks','今日待辦'],['documents','讀取文件'],['missing','聯絡確認'],['line','LINE提醒'],['qa','法規問答']];
  const nav=$('#navigation');nav.hidden=false;
  nav.innerHTML=`<div class="nav-eyebrow">${officer?'承辦人工作桌':'雇主的辦理索引'}</div><nav aria-label="主要功能">${items.map(([id,title],i)=>`<button data-page="${id}" aria-current="${state.page===id?'page':'false'}"><span class="nav-index">0${i+1}</span>${title}</button>`).join('')}${officer?'<a class="nav-link" href="/city.html">市府視角地圖 ↗</a>':''}</nav>`;
  nav.querySelectorAll('[data-page]').forEach(el=>el.onclick=async()=>{
    if(state.draft) { await api('/api/documents/drafts/'+encodeURIComponent(state.draft.draft_id),{method:'DELETE'}).catch(()=>{}); state.draft=null; }
    await go(el.dataset.page);
  });
}
function loginPage() {
  main.innerHTML=`<section class="login"><div class="eyebrow">一本手帖，安心辦妥</div><h1>把期限理清楚，<br>下一步就有方向。</h1><p class="muted">以合成文件走一遍辦理流程。沒有真實個資，也不作正式辦案使用。</p><form id="login-form"><label for="account">示範帳號</label><select id="account" name="account"><option value="employer-a">家庭看護雇主 A</option><option value="employer-b">產業雇主 B</option><option value="officer">市府承辦人／示範管理員</option></select><label for="code">一次性登入碼</label><input id="code" name="code" type="password" autocomplete="one-time-code" required aria-describedby="code-hint"><p id="code-hint" class="hint">請使用展示者提供的登入碼；有效24小時，使用一次後失效。</p><button type="submit">打開我的案件手帖 →</button></form><div class="note">網路或模型無法使用時，可開啟明確標示的<a href="/local-demo.html">預存展示頁</a>。</div><a class="login-replay" href="/replay.html">不用登入也能看：新竹一件裁罰案的重播 →</a><a class="login-replay" href="/city.html">市府視角：新竹市三區的高齡人口地圖 →</a></section>`;
  $('#login-form').onsubmit=async e=>{
    e.preventDefault();const button=$('button[type=submit]',e.target);button.disabled=true;
    try { const r=await api('/api/session',{method:'POST',body:{account_id:$('#account').value,code:$('#code').value}});$('#code').value='';state.account=r.account;await enter(); }
    catch(err) { error(err.message,$('.login')); }
    finally {button.disabled=false;}
  };
}
async function loadCases() {
  const r=await api('/api/cases');state.cases=r.items;
  if(!state.caseId || !state.cases.some(c=>c.id===state.caseId)) state.caseId=state.cases[0]?.id || '';
  const details=await Promise.all(state.cases.map(c=>api('/api/cases/'+encodeURIComponent(c.id))));
  state.tasks=details.flatMap(d=>d.tasks);
}
async function enter() { identity();if(state.account.role==='employer')await loadCases();await go(state.account.role==='officer'?'penalty':'tasks'); }
async function go(page) {
  state.page=page;navigation();main.innerHTML='<div class="loading" role="status">正在讀取…</div>';
  try {
    if(page==='tasks') {await loadCases();tasksPage();}
    else if(page==='documents')await documentsPage();
    else if(page==='line')await linePage();
    else if(page==='missing')missingPage();
    else if(page==='qa')qaPage();
    else if(page==='penalty')penaltyPage();
    focusPage();
  } catch(e) { main.innerHTML=heading('稍後再試','資料暫時無法讀取');error(e.message);const b=document.createElement('button');b.textContent='重新讀取';b.onclick=()=>go(page);main.append(b); }
}
function caseSelect() {
  return `<div class="case-select"><label for="case-select">案件</label><select id="case-select">${state.cases.map(c=>`<option value="${h(c.id)}" ${c.id===state.caseId?'selected':''}>${h(c.display_code)} · 合成</option>`).join('')}</select></div>`;
}
function wireCase() { const select=$('#case-select');if(select)select.onchange=()=>state.caseId=select.value; }
const DAY=86400000;
function urgency(t){if(t.status==='done')return 'done';if(t.days_left===null||t.status==='needs_review')return 'review';if(t.overdue)return 'overdue';if(t.days_left<=3)return 'urgent';if(t.days_left<=14)return 'soon';return 'calm';}
function countdown(t){if(t.days_left===null)return '需人工確認';if(t.days_left<0)return `已逾期 ${-t.days_left} 天`;if(t.days_left===0)return '今天到期';return `還有 ${t.days_left} 天`;}
function todayOf(t){return new Date(Date.parse(t.due_date+'T00:00:00Z')-t.days_left*DAY);}
function heroCard(){
  const t=state.tasks.filter(x=>x.status!=='done'&&x.status!=='needs_review'&&x.days_left!==null).sort((a,b)=>a.days_left-b.days_left)[0];
  if(!t)return '';
  const u=urgency(t),n=Math.abs(t.days_left);
  const kicker={overdue:'已經過了期限，請盡快到辦理窗口補辦',urgent:'這幾天就要辦好',soon:'兩週內到期，現在就可以先安排',calm:'還有時間，可以先記在行事曆上'}[u];
  const opens=t.start_date?Math.round((Date.parse(t.start_date+'T00:00:00Z')-todayOf(t))/DAY):null;
  const windowText=opens!==null&&opens>0?`${h(t.start_date)} 起就可以辦（${opens} 天後）`:t.start_date?`辦理期間 ${h(t.start_date)} 至 ${h(t.due_date)}，現在就可以去辦`:'在期限前辦完就可以';
  return `<section class="hero hero-${u}" aria-label="最近的期限"><div class="hero-count" aria-hidden="true"><span>${t.overdue?'已逾期':t.days_left===0?'今天':'還有'}</span><strong>${t.days_left===0?'到期':n}</strong>${t.days_left===0?'':'<span>天</span>'}</div><div class="hero-body"><div class="hero-kicker">${h(kicker)}</div><h2>${h(t.title)}</h2><p class="visually-hidden">${h(countdown(t))}</p><p>期限 <strong>${h(t.due_date)}</strong> · ${h(t.display_code)}<br>${windowText}</p><button data-task="${h(t.id)}">查看怎麼辦 →</button></div></section>`;
}
function timelines(){
  const byCase=state.cases.map(c=>({c,tasks:state.tasks.filter(t=>t.case_id===c.id&&t.due_date)})).filter(x=>x.tasks.length>=2);
  return byCase.map(({c,tasks})=>{
    tasks=[...tasks].sort((a,b)=>(a.start_date||a.due_date).localeCompare(b.start_date||b.due_date));
    const today=todayOf(tasks[0]).getTime();
    let lo=Math.min(today,...tasks.map(t=>Date.parse((t.start_date||t.due_date)+'T00:00:00Z'))),hi=Math.max(today,...tasks.map(t=>Date.parse(t.due_date+'T00:00:00Z')));
    const pad=(hi-lo)*.04||30*DAY;lo-=pad;hi+=pad;
    const pct=ms=>((ms-lo)/(hi-lo)*100).toFixed(2);
    const years=[];for(let y=new Date(lo).getUTCFullYear()+1;Date.UTC(y,0,1)<=hi;y++)if(Math.abs(Date.UTC(y,0,1)-today)/(hi-lo)>.07)years.push(y);
    return `<section class="atlas" aria-label="${h(c.display_code)} 期限地圖"><div class="eyebrow">期限地圖 · ${h(c.display_code)}</div><h2>這份聘僱接下來要辦的事</h2><p class="muted">每一列是一項法定義務。色帶是可以去辦的期間，圓點是期限，虛線是今天。</p><div class="atlas-axis" aria-hidden="true">${years.map(y=>`<span class="atlas-year" data-left="${pct(Date.UTC(y,0,1))}">${y}</span>`).join('')}<span class="atlas-today-label" data-left="${pct(today)}">今天</span></div><ol class="atlas-rows">${tasks.map(t=>{const s=Date.parse((t.start_date||t.due_date)+'T00:00:00Z'),e=Date.parse(t.due_date+'T00:00:00Z');return `<li class="atlas-row atlas-${urgency(t)}"><button class="atlas-label" data-task="${h(t.id)}"><span>${h(t.title)}</span><small>${t.start_date?h(t.start_date)+' 至 ':''}${h(t.due_date)} · ${h(t.status==='done'?'已完成':countdown(t))}</small></button><div class="atlas-track" aria-hidden="true"><span class="atlas-today" data-left="${pct(today)}"></span>${t.start_date?`<span class="atlas-bar" data-left="${pct(s)}" data-width="${(pct(e)-pct(s)).toFixed(2)}"></span>`:''}<span class="atlas-dot" data-left="${pct(e)}"></span></div></li>`;}).join('')}</ol></section>`;
  }).join('');
}
function placeAtlas(){main.querySelectorAll('.atlas [data-left]').forEach(el=>{el.style.left=el.dataset.left+'%';if(el.dataset.width)el.style.width=Math.max(.8,+el.dataset.width)+'%';});}
const replayCard=`<a class="replay-card" href="/replay.html"><span class="replay-card-kicker">案例重播 · 新竹市真實裁罰案</span><strong>晚了 19 天，罰 6 萬元。</strong><span>如果那一家當時有用竹聘安，會在哪幾天收到提醒？ →</span></a>`;
function tasksPage() {
  let tasks=[...state.tasks].sort((a,b)=>a.status==='done'&&b.status!=='done'?1:b.status==='done'&&a.status!=='done'?-1:(a.due_date||'9999').localeCompare(b.due_date||'9999'));
  if(state.filter==='week')tasks=tasks.filter(t=>t.days_left!==null&&t.days_left>=0&&t.days_left<=7&&t.status!=='done');
  if(state.filter==='done')tasks=tasks.filter(t=>t.status==='done');
  const active=state.tasks.filter(t=>t.status!=='done');
  main.innerHTML=heading('辦理索引 / 01','今天，先辦這幾件。','每一項都留有來源、期限與辦理窗口。完成後，再由你親自確認。')+heroCard()+
    `<div class="summary-line"><span><strong>${active.length}</strong>項待辦</span><span><strong>${active.filter(t=>t.overdue).length}</strong>項已逾期</span><span><strong>${active.filter(t=>t.status==='needs_review').length}</strong>項需核對</span></div><div class="toolbar"><div class="filters" aria-label="待辦篩選">${[['all','全部'],['week','本週'],['done','已完成']].map(([id,label])=>`<button data-filter="${id}" aria-pressed="${state.filter===id}">${label}</button>`).join('')}</div><button id="new-document">＋ 讀取合成公文</button></div><div class="list-note"><span>依期限排序</span><span>事項 ／ 日期 ／ 辦理狀態</span></div><div class="task-list">${tasks.length?tasks.map(t=>`<article class="task-row row-${urgency(t)}"><div class="task-date">${t.due_date?h(t.due_date.slice(5).replace('-','/')):'待核對'}<span>${h(t.due_date?.slice(0,4)||'無確認日期')}</span></div><div><button class="task-title" data-task="${h(t.id)}">${h(t.title)}</button><div class="task-meta"><span>${h(t.display_code)}</span><span class="status ${t.overdue?'overdue':''}">${h(labels[t.status])}${t.overdue?' · 已逾期':''}</span>${t.status!=='done'&&t.days_left!==null?`<span class="countdown">${h(countdown(t))}</span>`:''}</div></div><button class="quiet row-arrow" data-task="${h(t.id)}" aria-label="查看${h(t.title)}">↗</button></article>`).join(''):'<div class="empty"><h2>這一頁，暫時沒有事項。</h2><p>可以切換篩選，或選一份合成公文開始。</p></div>'}</div><div class="note">「已委任」仍需取得證明；「準時」是判讀結果，按下「我已辦好，確認完成」才會完成待辦。</div>`+timelines()+replayCard;placeAtlas();
  $('#new-document').onclick=()=>go('documents');
  main.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{state.filter=b.dataset.filter;tasksPage();});
  main.querySelectorAll('[data-task]').forEach(b=>b.onclick=()=>detailPage(b.dataset.task));
}
const WORKER_TOPICS=/^(health_|recheck_report|dorm_change|renewal_window|permit_expiry)/;
function workerNotice(t){
  if(!t.due_date||t.status==='needs_review'||!WORKER_TOPICS.test(t.rule_key))return;
  const s=document.createElement('section');s.className='section worker-notice';
  s.innerHTML=`<div class="eyebrow">給看護的母語提醒</div><h2>用看護看得懂的語言，提醒什麼時候要去辦</h2><p class="muted">內容只有事項跟日期，不會放姓名、證號或地址。</p><div class="wn-controls"><div><label for="wn-lang">語言</label><select id="wn-lang"><option value="id">印尼語</option><option value="vi">越南語</option><option value="en">英語（菲律賓）</option></select></div><div><label for="wn-mode">產生方式</label><select id="wn-mode"><option value="stored">預存句型</option><option value="live">即時 AI 翻譯</option></select></div><button id="wn-make" class="secondary">產生提醒</button></div><div id="wn-result" aria-live="polite"></div>`;
  main.append(s);
  $('#wn-make').onclick=async()=>{const b=$('#wn-make');b.disabled=true;const out=$('#wn-result');out.innerHTML='<p class="muted">產生中，AI 翻譯可能要等一下…</p>';
    try{const r=await api('/api/tasks/'+encodeURIComponent(t.id)+'/worker-notice',{method:'POST',body:{lang:$('#wn-lang').value,mode:$('#wn-mode').value}});
      out.innerHTML=`<div class="wn-pair"><div><div class="wn-label">${h(r.lang_name)}</div><pre class="message-preview">${h(r.text)}</pre></div><div><div class="wn-label">中文對照</div><pre class="message-preview">${h(r.zh)}</pre></div></div><p class="muted">${h(r.mode)}。${h(r.notice)}</p><button class="quiet" id="wn-copy">複製${h(r.lang_name)}內容</button>`;
      $('#wn-copy').onclick=async()=>{try{await navigator.clipboard.writeText(r.text);notice('已複製，可以貼到 LINE 傳給看護');}catch{notice('沒辦法自動複製，請手動選取文字');}};}
    catch(e){out.innerHTML='';error(e.message,out);}finally{b.disabled=false;}};
}
async function detailPage(id) {
  try {
    const r=await api('/api/tasks/'+encodeURIComponent(id));state.selected=r;state.proof=r.proofs[0]||null;
    const t=r.task,tr=t.calc_trace;
    main.innerHTML=`<button class="quiet back" id="back">← 回到待辦</button>`+heading(t.display_code,t.title,'先看清楚何時前、去哪裡辦；辦理後再回來核對證明。')+
      `<div class="two-column"><section><div class="eyebrow">何時前</div><p class="detail-deadline">${h(t.due_date||'需人工確認')}</p><p><span class="status ${t.overdue?'overdue':''}">${h(labels[t.status])}${t.overdue?' · 原期限已逾':''}</span></p><dl class="details-grid"><dt>可以開始辦理</dt><dd>${h(t.start_date||'依期限前辦理')}</dd><dt>去哪裡辦</dt><dd>${h(t.office)}</dd><dt>文件來源</dt><dd>${h(r.document.kind)} · 合成示範</dd></dl><div class="actions"><a class="button" href="${h(t.official_url)}" target="_blank" rel="noopener">前往官方辦理入口 ↗</a>${t.status==='todo'?'<button class="secondary" id="delegate">委任代辦</button>':''}</div><details><summary>查看來源、法條與每一步計算</summary><dl class="details-grid">${[['事件',tr.event],['事件日',tr.event_date],['起算日',tr.start_date],['計算規則',tr.rule],['原到期日',tr.original_due_date],['假日順延',tr.holiday_adjustment],['最後期限',tr.final_due_date],['依據條文',t.law_ref],['條文版本',Object.values(tr.law_versions).map(v=>v.revision).join('；')],['日曆涵蓋',tr.calendar_years.join('、')],['日曆版本',tr.calendar_version],['規則版本',tr.rules_version]].map(([k,v])=>`<dt>${h(k)}</dt><dd>${h(v||'需人工確認')}</dd>`).join('')}</dl><h3>原文邊註</h3>${Object.entries(tr.source_excerpts||{}).map(([k,v])=>`<p class="source">${h(fieldLabels[k]||k)}：${h(v)}</p>`).join('')||'<p>尚無可核對的原文片段，請人工核對。</p>'}</details></section><section class="section"><h2>辦好了，留下一份證明。</h2><div id="proof-area"></div></section></div><details><summary>誰確認了這項待辦</summary><ul class="timeline">${r.audit_events.map(a=>`<li>${h(a.created_at.slice(0,16).replace('T',' '))}<br>${h(a.actor_id)} · ${h({confirm_fields:'確認文件日期',delegate:'委任代辦',submit_proof:'上傳證明，待雇主確認',confirm_done:'雇主確認完成',delete_proof:'刪除證明判讀'}[a.action]||a.action)}</li>`).join('')}</ul></details><details><summary>刪除此合成文件及相關待辦</summary><p>會移除此文件產生的全部待辦、證明判讀與通知紀錄。原件未保存。</p><button class="danger" id="delete-document">刪除此合成文件</button></details>`;
    $('#back').onclick=()=>go('tasks');
    if($('#delegate'))$('#delegate').onclick=async()=>{try{await api('/api/tasks/'+id,{method:'PATCH',body:{status:'delegated'}});notice('已委任；仍需證明與雇主確認。');await detailPage(id);}catch(e){error(e.message);}};
    $('#delete-document').onclick=async()=>{try{await api('/api/documents/'+r.document.id,{method:'DELETE'});notice('合成文件與相關資料已刪除');await go('tasks');}catch(e){error(e.message);}};
    workerNotice(t);renderProof();focusPage();
  } catch(e){error(e.message);}
}
function renderProof() {
  const {task:t}=state.selected,p=state.proof,area=$('#proof-area');
  if(t.status==='needs_review'){area.innerHTML='<p>期限尚未確認，請先向辦理窗口核對，再使用其他合成範例展示辦理流程。</p>';return;}
  if(t.status==='done') {area.innerHTML=`<div class="note"><h3>雇主已確認完成</h3><p>${h(p?.read_mode)}</p><p>辦理日期：${h(p?.observed_date)}<br>${p?.verdict==='late'?'已辦理，保留逾期事實。':'證明已核對。'}</p></div>`;return;}
  area.innerHTML=`<p>上傳後只暫時讀取日期，原始檔不保存。</p><div class="actions"><button class="secondary" id="sample-proof">使用固定合成證明</button></div><form id="proof-form"><label for="proof-file">上傳合成辦理證明</label><input id="proof-file" type="file" accept=".txt,.pdf" required><button type="submit" class="secondary">讀取證明日期</button></form>${p?`<div class="note"><p>${h(p.read_mode)}</p><strong>${h({on_time:'判讀為準時，等待你確認',late:'判讀為逾期，等待你確認',early:'早於辦理期間，請核對',unknown:'日期尚未讀取，請人工填寫',mismatch:'可能不是此待辦的證明'}[p.verdict]||'需核對證明')}</strong><p class="source">${h(p.excerpt)}</p></div><form id="complete-form"><label for="observed-date">核對後的實際辦理日期</label><input id="observed-date" type="date" required value="${h(p.observed_date||'')}"><label class="check"><input type="checkbox" id="proof-matches" required>我已核對此證明的案件、事項與辦理日期，確認已辦好。</label><label class="check"><input type="checkbox" id="outside-window">若早於辦理期間，我已另向窗口核對例外。</label><button type="submit">我已辦好，確認完成</button><button type="button" class="quiet" id="remove-proof">刪除這份判讀</button></form>`:''}`;
  $('#sample-proof').onclick=async()=>{
    try{const sample=await api('/api/tasks/'+t.id+'/proof-sample');const fd=new FormData();fd.append('file',new Blob([sample.text],{type:'text/plain'}),'合成證明.txt');fd.append('mode','stored');await submitProof(fd);}catch(e){error(e.message,area);}
  };
  $('#proof-form').onsubmit=async e=>{e.preventDefault();const file=$('#proof-file').files[0];if(!file)return;const fd=new FormData();fd.append('file',file);fd.append('mode','live');await submitProof(fd);};
  if(p){$('#complete-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/tasks/'+t.id+'/confirm',{method:'POST',body:{proof_id:p.id,confirmed:true,observed_date:$('#observed-date').value,matches_task:$('#proof-matches').checked,outside_window_acknowledged:$('#outside-window').checked}});notice('你已確認完成，辦理紀錄已保留。');await detailPage(t.id);}catch(err){error(err.message,area);}};
    $('#remove-proof').onclick=async()=>{try{await api('/api/tasks/'+t.id+'/proof/'+p.id,{method:'DELETE'});await detailPage(t.id);}catch(err){error(err.message,area);}};}
}
async function submitProof(fd){const area=$('#proof-area');try{area.setAttribute('aria-busy','true');const r=await api('/api/tasks/'+state.selected.task.id+'/proof',{method:'POST',body:fd});notice(r.mode+'；仍待你確認');await detailPage(state.selected.task.id);}catch(e){error(e.message,area);}finally{area.removeAttribute('aria-busy');}}

async function documentsPage(){
  const r=await api('/api/demo/samples');
  main.innerHTML=heading('文件邊註 / 02','先讀日期，再由你確認。','文件欄位在你確認前，不會寫入案件，也不會產生待辦。')+
    `<div class="step"><span class="active">01 選擇文件</span><span>→</span><span>02 核對日期</span><span>→</span><span>03 新增待辦</span></div>${caseSelect()}<div class="two-column"><section class="section"><h2>選一份合成公文</h2><p class="muted">下列範例使用固定內容，可在模型故障時切換預存結果。</p><div class="sample-list">${r.items.map(s=>`<button data-sample="${h(s.id)}">${h(s.label)}<span>↗</span></button>`).join('')}<button id="scan-sample">住宿變更 · 合成掃描範例<span>↗</span></button></div><label for="extract-mode">讀取方式</label><select id="extract-mode"><option value="live">即時模型擷取</option><option value="stored">預存示範結果（固定範例）</option></select></section><section class="section"><h2>或選取合成檔案</h2><form id="extract-form"><div class="upload"><label for="document-file">合成公文檔案</label><input id="document-file" type="file" accept=".txt,.pdf,.png,.jpg,.jpeg" required><p class="hint">JPG、PNG、PDF、TXT；上限15 MB，PDF最多10頁。圖片只接受系統提供的合成範例。</p></div><label class="check"><input id="synthetic-confirm" type="checkbox" required>我確認這是合成測試資料。</label><button type="submit">讀取文件欄位 →</button></form><div class="note">真實圖片／含圖 PDF 會停止處理。這個決賽版本不供正式收件。</div></section></div><div id="extract-status" role="status"></div>`;
  wireCase();
  main.querySelectorAll('[data-sample]').forEach(b=>b.onclick=async()=>{const s=r.items.find(s=>s.id===b.dataset.sample);await extractDocument(new File([s.text],s.id+'.txt',{type:'text/plain'}),$('#extract-mode').value);});
  $('#scan-sample').onclick=async()=>{try{const response=await fetch('/samples/'+encodeURIComponent('住宿地點變更_掃描.png'),{cache:'no-store'});await extractDocument(new File([await response.blob()],'住宿地點變更_掃描.png',{type:'image/png'}),$('#extract-mode').value);}catch(e){error(e.message);}};
  $('#extract-form').onsubmit=async e=>{e.preventDefault();if($('#synthetic-confirm').checked)await extractDocument($('#document-file').files[0],$('#extract-mode').value);};
}
async function extractDocument(file,mode){
  if(busy)return;busy=true;const status=$('#extract-status');status.innerHTML='<div class="note">正在讀取欄位；模型可能需要約90秒。原始檔不保存。你仍需核對日期。</div>';
  const fd=new FormData();fd.append('file',file);fd.append('mode',mode);
  try{const draft=await api('/api/documents/extract',{method:'POST',body:fd});if(state.page!=='documents')return;state.draft=draft;confirmationPage();}
  catch(e){error(e.message);status.innerHTML='<p>可在「讀取方式」切換為「預存示範結果」，再選擇合成範例。</p>';}
  finally{busy=false;}
}
function confirmationBody(previewOnly = false) {
  const fields = state.draft.workers.map((worker, index) => {
    const item = {...worker};
    for (const field of Object.keys(fieldLabels)) {
      const input = $(`#field-${index}-${field}`);
      if (input) item[field] = input.value || null;
    }
    return item;
  });
  const checked = [...main.querySelectorAll('[data-check-key]:checked')].map(input => input.dataset.checkKey);
  return {
    case_id: state.caseId, draft_id: state.draft.draft_id,
    document_kind: $('#document-kind').value, fields, checked,
    confirmed: previewOnly ? false : $('#confirm-fields').checked, preview_only: previewOnly,
  };
}

function dateField(worker, index, field, label) {
  const source = state.draft.fields.find(item => item.worker_index === index && item.field === field);
  const warning = source?.warning;
  return `<div class="field-block" id="date-block-${index}-${field}">
    <label for="field-${index}-${field}">${h(label)}</label>
    <input id="field-${index}-${field}" type="date" value="${h(worker[field] || '')}" data-original="${h(worker[field] || '')}" aria-describedby="source-${index}-${field}">
    <p class="source" id="source-${index}-${field}">來源：${h(worker.evidence?.[field] || '未讀到；請對照合成原件補充確認')}<span class="edited" hidden> · 已由你修改，將按新日期計算</span></p>
    ${warning ? `<p class="review-note">需核對：${h(warning)}</p><label class="check"><input type="checkbox" id="checked-${index}-${field}" data-check-key="${index}:${field}">已核對原件（${h(label)}，移工${index + 1}）</label>` : ''}
  </div>`;
}

function clearDateError(input) {
  const block = input.closest('.field-block');
  if (!block) return;
  block.classList.remove('field-error');
  block.querySelectorAll('[aria-invalid]').forEach(el => el.removeAttribute('aria-invalid'));
}

function markUnchecked(keys) {
  for (const key of keys) {
    const [index, field] = key.split(':');
    if (!/^\d+$/.test(index) || !Object.hasOwn(fieldLabels, field)) continue;
    const block = $(`#date-block-${index}-${field}`);
    if (!block) continue;
    block.classList.add('field-error');
    block.querySelectorAll('input').forEach(input => input.setAttribute('aria-invalid', 'true'));
  }
}

function confirmationPage() {
  const draft = state.draft;
  main.innerHTML = heading('文件邊註 / 02', '請把日期，逐一核對。', '原文留在邊註，日期可以修改。有提示的日期請逐欄勾選，或改成你已確認的日期。') +
    `<div class="step"><span>01 已選文件</span><span>→</span><span class="active">02 核對日期</span><span>→</span><span>03 新增待辦</span></div>
    <div class="note"><strong>${h(draft.mode)}</strong><br>${h(draft.warning)}；10分鐘後確認頁失效。</div>
    <form id="confirmation-form">${caseSelect()}
      <label for="document-kind">這是什麼文件</label><select id="document-kind">${['入國通報受理證明書','聘僱許可函','期滿續聘許可函','再檢查診斷證明書','住宿地點變更','家事移工預定入國','聘僱關係終止'].map(kind => `<option ${draft.document_kind === kind ? 'selected' : ''}>${h(kind)}</option>`).join('')}</select>
      <div class="two-column"><section><h2 class="section">逐欄確認</h2>${draft.workers.map((worker, index) => `<fieldset class="section"><legend>移工代號 ${String(index + 1).padStart(2, '0')} · 合成</legend>${Object.entries(fieldLabels).filter(([field]) => worker[field] || ['entry_date','event_date','permit_end'].includes(field)).map(([field, label]) => dateField(worker, index, field, label)).join('')}</fieldset>`).join('')}</section>
      <section class="section"><details open><summary>送出模型前的文字遮蔽預覽</summary><pre>${h(draft.masked_preview || '合成掃描範例，無可本機遮蔽的文字；僅此固定範例可處理。')}</pre></details>
        <div class="note" id="task-count" role="status">請核對文件日期後預覽待辦數量。</div>
        <label class="check"><input id="confirm-fields" type="checkbox" required>我已逐欄核對文件種類與日期，同意以這些日期產生待辦。</label>
        <div class="actions"><button type="submit" id="confirm-button">確認日期，新增待辦 →</button><button type="button" class="secondary" id="cancel-document">取消讀取</button></div>
      </section></div>
    </form>`;
  wireCase();
  $('#case-select').onchange = () => { state.caseId = $('#case-select').value; previewCount(); };
  let timer;
  main.querySelectorAll('input[type=date],#document-kind').forEach(input => input.oninput = () => {
    if (input.type === 'date') {
      const changed = input.value !== input.dataset.original;
      $(`#source-${input.id.slice(6)} .edited`).hidden = !changed;
      const check = input.closest('.field-block').querySelector('[data-check-key]');
      if (check) { check.checked = false; check.disabled = changed; }
      clearDateError(input);
    }
    $('#confirm-fields').checked = false;
    clearTimeout(timer);
    timer = setTimeout(previewCount, 250);
  });
  main.querySelectorAll('[data-check-key]').forEach(input => input.onchange = () => clearDateError(input));
  $('#cancel-document').onclick = async () => {
    await api('/api/documents/drafts/' + draft.draft_id, {method:'DELETE'});
    state.draft = null;
    await go('documents');
  };
  $('#confirmation-form').onsubmit = async event => {
    event.preventDefault();
    const button = $('#confirm-button');
    button.disabled = true;
    try {
      const result = await api('/api/documents/confirm', {method:'POST', body:confirmationBody()});
      state.draft = null;
      notice(result.duplicate ? '這份文件已確認，沒有重複新增。' : `已新增 ${result.task_ids.length} 項待辦；需核對的日期另有標示。`);
      await go('tasks');
    } catch (err) {
      error(err.message);
      markUnchecked(err.unchecked || []);
    } finally {
      button.disabled = false;
    }
  };
  previewCount();
  focusPage();
}

async function previewCount(){if(!state.draft||!$('#task-count'))return;try{const r=await api('/api/documents/confirm',{method:'POST',body:confirmationBody(true)});if($('#task-count'))$('#task-count').textContent=r.duplicate?'這份文件已在此案件中，將不重複新增。':`確認後將新增 ${r.task_count} 項待辦。僅需查辦公日曆且檢查日期超出2026／2027時，顯示「需人工確認」。`;}catch(e){if($('#task-count'))$('#task-count').textContent=e.message;}}

async function linePage(){
  const r=await api('/api/line/preview',{method:'POST'});
  main.innerHTML=heading('提醒索引 / 04','提醒，寄到你的 LINE。','每個 LINE 帳號只綁定一位雇主；訊息只含事項、日期與案件代號。')+
    `<div class="two-column"><section class="section"><h2>01 先配對帳號</h2><p>綁定狀態：<strong>${r.bound?'已綁定此雇主帳號':'尚未綁定'}</strong></p><button id="pair-code">取得六位配對碼</button><div id="pair-result" aria-live="polite"></div><p class="hint">在指定的 LINE 官方帳號對話輸入配對碼，10分鐘內有效且僅能用一次。</p><div class="actions"><button id="refresh-line" class="secondary">已在 LINE 輸入，重新查詢</button>${r.bound?'<button class="danger" id="unbind">解除綁定</button>':''}</div><p class="hint">解除後不再發送提醒。在 LINE 也可輸入「取消綁定」。</p></section><section class="section"><h2>02 看看會收到什麼</h2><div class="message-preview">${h(r.text)}</div><div class="actions"><button id="send-demo" ${r.bound&&r.configured?'':'disabled'}>發送此帳號測試訊息</button></div><p class="hint">只發給本帳號綁定的收件人。相同待辦的當日測試只發一次。</p>${!r.configured?'<div class="note">LINE 服務尚未設定。此處為訊息預覽，尚未寄送；展示者可用預存展示頁說明。</div>':''}<div id="send-result" role="status"></div></section></div>`;
  $('#pair-code').onclick=async()=>{try{const r=await api('/api/line/pair-code',{method:'POST'});$('#pair-result').innerHTML=`<div class="code">${h(r.code)}</div><p>有效至 ${h(new Date(r.expires_at).toLocaleTimeString('zh-TW'))}</p>`;}catch(e){error(e.message);}};
  $('#refresh-line').onclick=()=>go('line');
  if($('#unbind'))$('#unbind').onclick=async()=>{try{await api('/api/line/binding',{method:'DELETE'});notice('已解除綁定');await go('line');}catch(e){error(e.message);}};
  $('#send-demo').onclick=async()=>{const b=$('#send-demo');b.disabled=true;try{const r=await api('/api/line/send-demo',{method:'POST'});$('#send-result').textContent=`實際收件人數：${r.recipients}。${r.status==='sent'?'LINE 已接受發送，請在手機確認。':r.status==='duplicate'?'今天已發送，不重複寄送。':'尚未確認發送成功，請檢查連線後重試。'}`;}catch(e){error(e.message);}finally{b.disabled=false;}};
}
function qaPage(){
  main.innerHTML=heading('法源索引 / 05','帶著已確認的日期問。','個案內容只取自你已確認的文件和待辦；沒有的日期會保留「尚未確認」。')+
    `<form id="qa-form">${state.account.role==='employer'?caseSelect():''}<label for="question">想確認什麼</label><textarea id="question" required maxlength="2000" placeholder="例如：這個案件的住宿變更最晚何時通知？"></textarea><label for="qa-mode">回答方式</label><select id="qa-mode"><option value="text">條文文字模式（不需模型）</option><option value="live">即時模型協助白話說明</option></select><div class="actions"><button type="submit">查已確認資料與相關規定 →</button></div></form><div id="qa-result" aria-live="polite"></div>`;
  wireCase();$('#qa-form').onsubmit=async e=>{e.preventDefault();const b=$('button[type=submit]',e.target);b.disabled=true;const output=$('#qa-result');output.innerHTML='<p class="loading">正在查詢已確認資料與條文…</p>';try{const r=await api('/api/qa',{method:'POST',body:{case_id:state.account.role==='employer'?state.caseId:null,question:$('#question').value,mode:$('#qa-mode').value}});output.innerHTML=`<div class="note">${h(r.mode)} · 合成示範 · 回答時間 ${h(r.answered_at)}</div>`+Object.entries(r.sections).map(([k,v])=>`<section class="qa-section"><h2>${h(k)}</h2><pre>${h(v)}</pre></section>`).join('')+`<details><summary>查到的條文與資料版本</summary>${r.citations.map(c=>`<p>${h(c.law+c.no)}</p>`).join('')}<pre>${h(JSON.stringify(r.data_version,null,2))}</pre></details>`;}catch(err){output.replaceChildren();error(err.message,output);}finally{b.disabled=false;}};
}
function missingPage(){
  main.innerHTML=heading('聯絡確認 / 03','聯絡不上，先把事實理清。','請用實際應工作日及聯繫紀錄核對。這個流程不會自動宣告移工行蹤不明。')+
    `<form id="missing-form"><div class="two-column"><section><label for="guide-today">今天的日期</label><input id="guide-today" type="date" required value="2026-11-15"><label class="check"><input id="today-scheduled" type="checkbox">今天原本應工作</label><label for="last-attendance">最後實際出勤日</label><input id="last-attendance" type="date" required value="2026-11-12"><button type="button" class="secondary" id="make-days">列出之後各日，逐日確認</button><div id="work-days"></div></section><section><label class="check"><input type="checkbox" id="contact-attempted" required>已嘗試聯絡本人或受委任機構，並保留紀錄</label><label for="contact-result">聯繫結果</label><select id="contact-result"><option value="unreachable">仍無法聯繫</option><option value="uncertain">有回覆，但本人或資訊尚未核實</option><option value="recovered">已確認本人，聯絡恢復</option></select><fieldset class="section"><legend>是否掌握可核實的資訊</legend><label class="check"><input type="checkbox" id="location-verified">住宿地點已查認屬實</label><label class="check"><input type="checkbox" id="period-verified">住宿期間已查認屬實</label><label class="check"><input type="checkbox" id="method-verified">聯絡方式已查認屬實</label><label class="check"><input type="checkbox" id="sought-1955">已向1955求助</label><label class="check"><input type="checkbox" id="relationship-active" checked>聘僱關係尚未終止</label><label class="check"><input type="checkbox" id="special-period">處於入國未滿三日、許可餘期不足三日、轉換、限期出國或合意暫停勞務等特殊期間</label></fieldset><div class="note">曾向1955求助仍須核實住宿與聯絡事實，不能自動排除失去聯繫。不得扣留護照或居留證。</div><button type="submit">依已確認事實，查看下一步 →</button></section></div></form><div id="guide-result" aria-live="polite"></div>`;
  let days=[];
  $('#make-days').onclick=()=>{
    const start=$('#last-attendance').value,end=$('#guide-today').value;if(!start||!end)return;
    const first=new Date(start+'T00:00:00Z'),last=new Date(end+'T00:00:00Z');
    if(last<first||(last-first)/86400000>90){error('請選擇今天之前90日內的最後出勤日');return;}
    days=[];for(let d=new Date(first.getTime()+86400000);d<=last;d=new Date(d.getTime()+86400000))days.push(d.toISOString().slice(0,10));
    $('#work-days').innerHTML=days.map((day,i)=>`<fieldset class="section"><legend>${h(day)} · ${h(['日','一','二','三','四','五','六'][new Date(day).getUTCDay()])}</legend><label for="scheduled-${i}">當天是否應工作</label><select id="scheduled-${i}" required><option value="">請確認實際班表</option><option value="yes">應工作</option><option value="no">休息日</option></select><label for="absent-${i}">出勤狀況</label><select id="absent-${i}"><option value="unknown">尚未確認／不適用</option><option value="yes">沒有到工</option><option value="no">有到工</option></select><label for="justified-${i}">是否有正當理由</label><select id="justified-${i}"><option value="unknown">尚未確認／不適用</option><option value="yes">有，請保留紀錄供核對</option><option value="no">目前未查得正當理由</option></select></fieldset>`).join('');
  };
  $('#missing-form').onsubmit=async e=>{e.preventDefault();if(!days.length){error('請先列出之後各日並確認班表');return;}const nullable=v=>v==='unknown'?null:v==='yes';const body={today:$('#guide-today').value,today_scheduled:$('#today-scheduled').checked,last_attendance:$('#last-attendance').value,work_days:days.map((day,i)=>({day,scheduled:$('#scheduled-'+i).value==='yes',absent:nullable($('#absent-'+i).value),justified:nullable($('#justified-'+i).value)})),contact_attempted:$('#contact-attempted').checked,contact_result:$('#contact-result').value,location_verified:$('#location-verified').checked,accommodation_period_verified:$('#period-verified').checked,contact_method_verified:$('#method-verified').checked,sought_1955:$('#sought-1955').checked,relationship_active:$('#relationship-active').checked,special_period:$('#special-period').checked};
    try{const r=await api('/api/missing/guide',{method:'POST',body});const result=$('#guide-result');result.innerHTML=`<div class="note"><h2>${h(r.status)}</h2><p>${h(r.explanation)}</p><p>已填紀錄中的連續應工作日不到工：${r.consecutive_work_days}日</p></div><h3>尚需核對</h3><ul>${r.missing_facts.length?r.missing_facts.map(f=>`<li>${h(f)}</li>`).join(''):'<li>請主管機關依卷證核對完整要件</li>'}</ul><p>${h(r.next_step)}</p><p>${h(r.law_ref)}</p><div class="actions"><a class="button secondary" href="${h(r.official_url)}" target="_blank" rel="noopener">閱讀官方認定基準 ↗</a><a class="button" href="${h(r.report_url)}" target="_blank" rel="noopener">官方申辦與通報資訊 ↗</a></div>`;result.scrollIntoView({block:'start'});}catch(err){error(err.message);}};
}
function penaltyPage(){
  main.innerHTML=heading('承辦人工作桌 / 01','把缺漏指出來，讓判斷更周全。','七項要件逐一核對。是否處分、如何裁量與送出，仍由承辦人決定。')+
    `<div class="note"><strong>僅輔助檢核 · 合成示範</strong><br>本版本不供市府實際辦案，草稿處理後不保存原文。</div><div class="two-column"><section><button class="secondary" id="load-penalty">載入合成裁處書草稿</button><form id="penalty-form"><label for="penalty-text">合成裁處書草稿</label><textarea id="penalty-text" rows="19" required minlength="30" maxlength="50000"></textarea><label for="penalty-mode">檢核方式</label><select id="penalty-mode"><option value="live">即時模型檢核</option><option value="stored">預存示範結果（固定草稿）</option></select><div class="actions"><button type="submit">開始七項輔助檢核 →</button></div></form></section><section><div id="penalty-result" aria-live="polite"><div class="empty"><h2>逐條核對，留下補查方向。</h2><p>相對人、事實、違反條文、處罰條文、金額、陳述意見、救濟教示。</p></div></div></section></div>${state.account.is_admin?'<section class="reset-panel"><h2>合成展示資料重置</h2><p>清除案件、文件、證明判讀、LINE綁定、通知紀錄及暫存，重建固定合成案件。所有登入碼將重新啟用，Session失效。</p><label class="check"><input type="checkbox" id="reset-check">我確認要重置此展示機的合成資料。</label><button class="danger" id="reset-demo" disabled>清空並重建合成資料</button></section>':''}`;
  $('#load-penalty').onclick=async()=>{try{const r=await api('/api/penalty/sample');$('#penalty-text').value=r.text;notice('合成草稿已載入');}catch(e){error(e.message);}};
  $('#penalty-form').onsubmit=async e=>{e.preventDefault();const b=$('button[type=submit]',e.target);b.disabled=true;const output=$('#penalty-result');output.innerHTML='<div class="loading" role="status">七項檢核進行中…若模型失效可改選預存示範結果。</div>';try{const r=await api('/api/penalty/check',{method:'POST',body:{text:$('#penalty-text').value,mode:$('#penalty-mode').value}});$('#penalty-text').value='';output.innerHTML=`<div class="note">${h(r.mode)} · 耗時 ${r.elapsed_ms} ms<br>${h(r.notice)}</div><ol class="checklist">${r.items.map(i=>`<li><h3>${h(i.name)}<span class="status">${h(i.status)}</span></h3><p class="source">草稿：${h(i.source_excerpt)}</p><p>${h(i.reason)}</p><p class="muted">${h(i.law_ref)}</p><p>${h(i.next_step)}</p></li>`).join('')}</ol>`;}catch(err){output.replaceChildren();error(err.message,output);}finally{b.disabled=false;}};
  if($('#reset-demo')){$('#reset-check').onchange=()=>$('#reset-demo').disabled=!$('#reset-check').checked;$('#reset-demo').onclick=async()=>{try{await api('/api/demo/reset',{method:'POST',body:{rebuild:true}});clearState();loginPage();notice('已清除並重建合成資料，請重新登入。');}catch(e){error(e.message);}};}
}
window.addEventListener('offline',()=>{state.draft=null;state.tasks=[];state.selected=null;state.proof=null;main.innerHTML=heading('目前離線','目前無法讀取個案資料。','請恢復網路後重新讀取。公開資訊與固定預存範例仍可開啟。')+'<div class="actions"><a class="button" href="/offline.html">公開離線說明</a><a class="button secondary" href="/local-demo.html">預存展示頁</a></div>';});
window.addEventListener('online',()=>{if(state.account)go(state.page);else loginPage();});
window.addEventListener('pagehide',()=>{state.tasks=[];state.selected=null;state.proof=null;state.draft=null;main.replaceChildren();});
window.addEventListener('pageshow',e=>{if(e.persisted)boot();});
async function boot(){clearState();try{const r=await api('/api/session');state.account=r.account;await enter();}catch{loginPage();}}
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
boot();
