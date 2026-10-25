"""Phone-friendly human handoff dashboard. Does not depend on a JS framework."""

HTML = r'''<!doctype html>
<html lang="tg"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>PLAZA-I • Client Desk</title>
<style>
:root{color-scheme:dark;--bg:#0d1722;--surface:#172432;--panel:#1d3040;--line:#314657;--muted:#acc2d1;--accent:#67d4bc;--text:#f1f8ff;--danger:#ffa7a7}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--text)}
header{height:72px;display:flex;align-items:center;justify-content:space-between;padding:14px 22px;border-bottom:1px solid var(--line)}
h1{font-size:19px;margin:0;letter-spacing:.05em}small{color:var(--muted)}.pill{font-size:12px;border:1px solid var(--accent);color:var(--accent);border-radius:30px;padding:6px 10px}
main{display:grid;grid-template-columns:minmax(245px,350px) 1fr;height:calc(100dvh - 72px)}aside{overflow:auto;border-right:1px solid var(--line)}
.toolbar{padding:16px;border-bottom:1px solid var(--line)}.toolbar h2{margin:0 0 8px;font-size:15px}button{background:var(--accent);color:#09252a;font-weight:650;border:0;border-radius:12px;padding:11px 14px;cursor:pointer}button.ghost{background:var(--panel);color:var(--text);border:1px solid var(--line)}button.danger{color:var(--danger)}button:disabled{opacity:.45;cursor:not-allowed}
input,textarea{width:100%;padding:12px;background:#111f2a;border:1px solid #476070;border-radius:10px;color:var(--text);font:inherit}textarea{resize:vertical;min-height:66px}.help{font-size:12px;color:var(--muted);line-height:1.5}
.chat{width:100%;text-align:left;display:block;padding:16px;background:none;color:var(--text);border-bottom:1px solid #273a4a;border-radius:0;font-weight:normal}
.chat:hover,.chat.selected{background:var(--surface)}.chat strong{font-size:14px}.chat p{white-space:nowrap;text-overflow:ellipsis;overflow:hidden;margin:7px 0 0;color:var(--muted);font-size:13px}
.label{float:right;font-size:11px;color:var(--accent)}section{display:flex;flex-direction:column;min-height:0}.chatheader{padding:14px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}#chatid{font-weight:700}
#messages{overflow-y:auto;flex:1;padding:20px;display:flex;flex-direction:column;gap:11px}.bubble{padding:11px 14px;max-width:min(82%,590px);border-radius:15px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5;font-size:14px}
.bubble.user{align-self:flex-start;background:var(--surface)}.bubble.assistant{align-self:flex-end;background:#174638}.bubble.staff{align-self:flex-end;background:#28577a}.who{display:block;font-size:11px;opacity:.7;margin-bottom:4px}
.bottom{padding:14px 18px;border-top:1px solid var(--line);display:flex;gap:10px;align-items:stretch}.bottom textarea{flex:1}.empty{color:var(--muted);margin:auto;padding:24px;text-align:center}
#alert{color:var(--danger);font-size:13px;min-height:1.4em;padding-top:8px}.smallbtn{padding:9px 10px;font-size:12px}
@media(max-width:740px){header{height:60px;padding:12px}main{height:calc(100dvh - 60px);grid-template-columns:1fr}aside{max-height:32vh;border-right:none;border-bottom:1px solid var(--line)}section{min-height:0}.toolbar{padding:10px}#messages{padding:12px}.bottom{padding:10px}.bubble{max-width:91%}}

.knowledgePanel{position:fixed;inset:72px 0 0;background:var(--bg);z-index:10;overflow:auto;padding:20px}
.knowledgePanel[hidden]{display:none}.knowledgeWrap{max-width:980px;margin:0 auto}
.knowledgeForm{display:grid;gap:10px;margin:14px 0 20px}.knowledgeForm textarea{min-height:100px}
.knowledgeActions{display:flex;gap:8px;flex-wrap:wrap}
.knowledgeEntry{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:9px}
.knowledgeEntry strong{font-size:14px}.knowledgeEntry p{margin:6px 0;white-space:pre-wrap;overflow-wrap:anywhere}
.knowledgeEntry .sub{font-size:12px;color:var(--muted)}.knowledgeEntry button{margin-top:5px}
@media(max-width:740px){.knowledgePanel{inset:60px 0 0;padding:12px}}
</style></head><body>
<header><div><h1>PLAZA-I <span style="color:#67d4bc">/ CLIENT DESK</span></h1><small>Architecture & Design • Душанбе</small></div><div style="display:flex;gap:9px;align-items:center"><button class="ghost smallbtn" onclick="toggleKnowledge()" id="kbSwitch">Донишҳо</button><span class="pill" id="status">Санҷиш...</span></div></header>
<main><aside><div class="toolbar"><h2>Суҳбатҳо</h2><div class="help">Менеҷер метавонад ботро барои ҳар мизоҷ боздорад. Рамзи DEMO / БЕ AI маънои онро дорад, ки ҷавобҳо танҳо намунавӣ мебошанд.</div>
<div style="margin-top:12px;padding:10px;border:1px solid var(--line);border-radius:10px">
 <div style="display:flex;justify-content:space-between;align-items:center">
  <strong style="font-size:13px">Ҳисобгирии API (90 рӯз)</strong>
  <button class="ghost smallbtn" onclick="refreshUsage()">Навсозӣ</button>
 </div>
 <p class="help" id="apiUsageText">Маълумот бор мешавад...</p>
 <p class="help">Арзиши тахминӣ аст, на ҳисоби расмии OpenAI. Дар Render Free омор ҳангоми бозоғозӣ метавонад гум шавад.</p>
</div>
<div id="demo" style="display:none;margin-top:12px"><label class="help" for="testtext">Санҷиши бот (бе WhatsApp)</label><p class="help" id="apiPreviewInfo"></p><input id="testtext" placeholder="Ба ман дизайни хона лозим" style="margin-top:6px"><button style="width:100%;margin-top:8px" onclick="demo()">Санҷидани паём</button></div></div>
<div id="chatlist"></div></aside>
<section><div class="chatheader"><div><div id="chatid">Мизоҷро интихоб кунед</div><small id="modehelp">AI / менеҷер</small></div><div style="display:flex;gap:6px;align-items:center"><button class="ghost smallbtn" id="toggle" onclick="toggle()" disabled>Гузариш ба менеҷер</button><button class="ghost danger smallbtn" id="delete" onclick="erase()" disabled>Тоза</button></div></div>
<div id="messages"><div class="empty">Суҳбатро аз рӯйхат кушоед.</div></div>
<div class="bottom"><textarea id="reply" placeholder="Ҷавоби менеҷер..." aria-label="Ҷавоби менеҷер"></textarea><button id="send" onclick="send()" disabled>Ирсол</button></div>
<div id="alert" role="status" style="padding-left:15px"></div>
</section></main>
<div class="knowledgePanel" id="knowledgePanel" hidden>
 <div class="knowledgeWrap">
  <h2>Маркази донишҳои PLAZA-I</h2>
  <p class="help">Бот фақат донишҳои тасдиқшударо истифода мебарад. Ҷавобҳои менеҷер пешниҳод мешаванд; саволҳои мизоҷон худкор ҳамчун далели дуруст қабул намешаванд. Маълумоти шахсиро ба донишҳо илова накунед.</p>
  <div class="knowledgeForm">
   <label class="help" for="kbTopic">Мавзӯъ</label>
   <select id="kbTopic" style="width:100%;padding:12px;background:#111f2a;color:var(--text);border:1px solid #476070;border-radius:10px">
    <option value="architecture">Меъморӣ</option><option value="estimate">Смета</option>
    <option value="interior">Дизайн</option><option value="author_supervision">Назорати муаллифӣ</option>
    <option value="general">Дигар</option><option value="from_staff">Суҳбати менеҷер</option>
   </select>
   <label class="help" for="kbQuestion">Саволи умумӣ (бе маълумоти мизоҷ)</label>
   <textarea id="kbQuestion" maxlength="500" placeholder="Смета чӣ гуна таҳия мешавад?"></textarea>
   <label class="help" for="kbAnswer">Ҷавоби санҷидашуда</label>
   <textarea id="kbAnswer" maxlength="1500" placeholder="Ҷавоби умумӣ ва тасдиқшудаи ширкат"></textarea>
   <div class="knowledgeActions">
    <button id="kbSave" onclick="saveKnowledge()">Ба баррасӣ илова кардан</button>
    <button class="ghost" id="kbApprove" onclick="reviewKnowledge('approved')" style="display:none">Тасдиқ кардан</button>
    <button class="ghost danger" id="kbReject" onclick="reviewKnowledge('rejected')" style="display:none">Рад кардан</button>
    <button class="ghost" onclick="clearKnowledge()">Пок кардани форма</button>
   </div><div id="kbMessage" class="help" role="status"></div>
  </div>
  <div class="knowledgeActions" style="margin-bottom:14px">
  <button class="ghost smallbtn" onclick="exportKnowledge()">Нусхаи эҳтиётии донишҳо (JSON)</button>
  <label class="help" for="kbRestore" style="align-self:center">Барқарор кардан:</label>
  <input id="kbRestore" type="file" accept=".json,application/json" style="max-width:260px"/>
  <button class="ghost smallbtn" onclick="importKnowledge()">Ворид кардан барои баррасӣ</button>
 </div>
 <h3>Саволу ҷавобҳо барои баррасӣ ва тасдиқ</h3>
  <div id="knowledgeList"></div>
 </div>
</div>
<script>
let current='',mode='',demoMode=false,latestChat='',knowledgeEditing=0;
async function call(path, options={}){
  const response=await fetch(path,{credentials:'same-origin',...options});
  if(!response.ok)throw Error('Хатои сервер: '+response.status+' '+await response.text());
  return await response.json();
}
const POST={method:'POST',headers:{'Content-Type':'application/json','X-PLAZAI-Request':'dashboard'}};
function el(name,text,klass){const d=document.createElement(name);if(text!==undefined)d.textContent=text;if(klass)d.className=klass;return d;}
function error(e){
  const offline=(e instanceof TypeError && String(e).includes('fetch'));
  document.getElementById('alert').textContent=offline
    ?'Пайвасти браузер ба сервер қатъ шуд. Интернетро санҷед ва саҳифаро нав кунед.'
    :String(e);
}
async function refreshUsage(){
 try{
  const data=await call('/api/admin/usage?days=90');
  const t=data.totals;
  const breakdown=Object.entries(t.errors||{}).map(item=>item[0]+': '+item[1]).join('; ');
  let line='Ҷавобҳои API: '+t.successful+'; хатогиҳо: '+t.failed;
  line+='; хароҷоти тахминӣ (USD): '+Number(t.estimated_usd).toFixed(4);
  line+='; воридотӣ: '+t.input_tokens+' токен, ҷавобӣ: '+t.output_tokens+' токен.';
  if(breakdown)line+=' Сабаби хатогиҳо: '+breakdown;
  if(t.unpriced_successes)line+=' Дархостҳои бенарх: '+t.unpriced_successes;
  document.getElementById('apiUsageText').textContent=line;
 }catch(err){
  document.getElementById('apiUsageText').textContent='Омор дастнорас: '+String(err);
 }
}
async function refresh(){
 try{
  const result=await call('/api/admin/chats');demoMode=result.demo;
  document.getElementById('status').textContent=demoMode?(result.ai_preview?'AI / САНҶИШ':'DEMO / БЕ AI'):'LIVE / WHATSAPP';
  document.getElementById('demo').style.display=demoMode?'block':'none';
  document.getElementById('apiPreviewInfo').textContent=result.ai_preview
    ?'Ин санҷиш аз OpenAI API истифода мекунад. Ҳангоми хатоҳои 429 ҷавоби офлайн нишон дода мешавад; ин ҷавоби AI нест.'
    :'DEMO: танҳо ҷавобҳои намунавӣ, бе API ва бе WhatsApp.';
  const list=document.getElementById('chatlist');list.replaceChildren();
  result.items.forEach(c=>{
    const b=el('button',undefined,'chat'+(c.wa_id===current?' selected':''));
    b.append(el('strong',c.wa_id),el('span',c.mode==='human'?'МЕНЕҶЕР':'AI','label'),el('p',c.last_message));
    b.onclick=()=>{current=c.wa_id;latestChat='';load()};list.append(b);
  });
  if(current)await load();
 }catch(e){error(e)}
}
async function load(){
 try{
  const d=await call('/api/admin/chats/'+encodeURIComponent(current));mode=d.mode;
  document.getElementById('chatid').textContent=current;
  document.getElementById('modehelp').textContent=mode==='human'?'Менеҷер ҷавоб медиҳад':'AI ҷавоб медиҳад';
  document.getElementById('toggle').textContent=mode==='human'?'Фаъол кардани AI':'Ба менеҷер супоридан';
  document.getElementById('toggle').disabled=false;document.getElementById('delete').disabled=false;
  document.getElementById('send').disabled=mode!=='human';
  const msg=document.getElementById('messages');
  const marker=JSON.stringify(d.messages);
  if(marker===latestChat)return;
  latestChat=marker;msg.replaceChildren();
  d.messages.forEach(m=>{
    let p=el('div',undefined,'bubble '+m.role);
    p.append(el('span',m.role==='user'?'МИЗОҶ':(m.role==='staff'?'МЕНЕҶЕР':'PLAZA-I AI'),'who'),el('div',m.body));
    msg.append(p);
  });msg.scrollTop=msg.scrollHeight;
 }catch(e){error(e)}
}
async function toggle(){try{const next=mode==='human'?'ai':'human';await call('/api/admin/chats/'+current+'/mode',{...POST,body:JSON.stringify({mode:next})});await refresh()}catch(e){error(e)}}
async function send(){const box=document.getElementById('reply');const text=box.value.trim();if(!current||!text)return;
 try{await call('/api/admin/chats/'+current+'/reply',{...POST,body:JSON.stringify({text})});box.value='';await refresh()}catch(e){error(e)}}
async function demo(){const box=document.getElementById('testtext');const text=box.value.trim();if(!text)return;try{await call('/api/admin/demo',{...POST,body:JSON.stringify({text})});current='992900000001';box.value='';setTimeout(refresh,1100)}catch(e){error(e)}}
async function erase(){if(!current||!confirm('Тамоми паёмҳои ҳамин мизоҷ тоза шаванд?'))return;
 try{await call('/api/admin/chats/'+current,{method:'DELETE',headers:{'X-PLAZAI-Request':'dashboard'}});current='';latestChat='';document.getElementById('messages').replaceChildren();await refresh()}catch(e){error(e)}}


async function exportKnowledge(){
 try{
  const data=await call('/api/admin/knowledge/export');
  const file=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(file);const a=document.createElement('a');
  a.href=url;a.download='plaza-i-approved-knowledge.json';a.click();
  URL.revokeObjectURL(url);
  kbStatus('Нусхаи донишҳои тасдиқшуда омода шуд. Онро дар ҷои бехатар нигоҳ доред.');
 }catch(e){kbStatus(String(e))}
}
async function importKnowledge(){
 try{
  const file=document.getElementById('kbRestore').files[0];
  if(!file)throw Error('Аввал файли JSON-ро интихоб кунед.');
  if(file.size>1000000)throw Error('Файл аз ҳад калон аст.');
  const data=JSON.parse(await file.text());
  if(!Array.isArray(data.items)||data.format!=='plazai-approved-knowledge-v1')
    throw Error('Формати нусха нодуруст аст.');
  await call('/api/admin/knowledge/import',{...POST,body:JSON.stringify({items:data.items})});
  document.getElementById('kbRestore').value='';
  kbStatus('Донишҳо барои баррасӣ ворид шуданд; тасдиқ зарур аст.');
  await loadKnowledge();
 }catch(e){kbStatus(String(e))}
}
function kbStatus(msg){document.getElementById('kbMessage').textContent=msg}
function clearKnowledge(){
 knowledgeEditing=0;document.getElementById('kbQuestion').value='';
 document.getElementById('kbAnswer').value='';
 document.getElementById('kbTopic').value='general';
 document.getElementById('kbSave').style.display='';
 document.getElementById('kbApprove').style.display='none';
 document.getElementById('kbReject').style.display='none';
 kbStatus('');
}
async function toggleKnowledge(){
 const panel=document.getElementById('knowledgePanel');
 panel.hidden=!panel.hidden;
 document.getElementById('kbSwitch').textContent=panel.hidden?'Донишҳо':'Суҳбатҳо';
 if(!panel.hidden)await loadKnowledge();
}
async function loadKnowledge(){
 try{
  const data=await call('/api/admin/knowledge');
  const list=document.getElementById('knowledgeList');list.replaceChildren();
  if(!data.items.length){list.append(el('p','Донишҳо ҳанӯз ворид нашудаанд.','help'));return}
  data.items.forEach(entry=>{
   const card=el('div',undefined,'knowledgeEntry');
   card.append(el('strong',entry.question),el('p',entry.answer),
     el('div',entry.state+' • '+entry.topic+' • '+entry.origin,'sub'));
   const choose=el('button',entry.state==='pending'?'Баррасӣ':'Намоиш','ghost smallbtn');
   choose.onclick=()=>{
    knowledgeEditing=entry.id;
    document.getElementById('kbQuestion').value=entry.question;
    document.getElementById('kbAnswer').value=entry.answer;
    document.getElementById('kbTopic').value=['architecture','estimate','interior','author_supervision','general','from_staff'].includes(entry.topic)?entry.topic:'general';
    document.getElementById('kbSave').style.display='none';
    document.getElementById('kbApprove').style.display=entry.state==='approved'?'none':'';
    document.getElementById('kbReject').style.display=entry.state==='rejected'?'none':'';
    kbStatus('Савол ва ҷавобро ислоҳ карда, баъд тасдиқ намоед.');
    document.getElementById('kbQuestion').scrollIntoView({behavior:'smooth',block:'center'});
   };
   card.append(choose);list.append(card);
  });
 }catch(e){kbStatus(String(e))}
}
async function saveKnowledge(){
 try{
  const question=document.getElementById('kbQuestion').value.trim();
  const answer=document.getElementById('kbAnswer').value.trim();
  const topic=document.getElementById('kbTopic').value;
  await call('/api/admin/knowledge',{...POST,body:JSON.stringify({question,answer,topic})});
  clearKnowledge();kbStatus('Ба навбати баррасӣ илова шуд.');await loadKnowledge();
 }catch(e){kbStatus(String(e))}
}
async function reviewKnowledge(state){
 if(!knowledgeEditing)return;
 try{
  const question=document.getElementById('kbQuestion').value.trim();
  const answer=document.getElementById('kbAnswer').value.trim();
  await call('/api/admin/knowledge/'+knowledgeEditing+'/review',
   {...POST,body:JSON.stringify({state,question,answer})});
  clearKnowledge();kbStatus(state==='approved'?'Ба донишҳои бот дохил шуд.':'Рад карда шуд.');
  await loadKnowledge();
 }catch(e){kbStatus(String(e))}
}

refresh();refreshUsage();setInterval(refresh,4500);setInterval(refreshUsage,60000);
</script></body></html>'''
