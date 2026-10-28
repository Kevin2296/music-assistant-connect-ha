'use strict';
const PROVIDERS = [
  {id:'ytmusic',name:'YouTube Music',type:'Tijdelijke browser · Premium',logo:'▶',color:'#d32d38',cookie:true,help:'Vereist YouTube Music Premium én de YT Music PO Token Generator in Home Assistant.',docs:'https://www.music-assistant.io/music-providers/youtube-music/'},
  {id:'soundcloud',name:'SoundCloud',type:'Tijdelijke browser · Ook gratis',logo:'☁',color:'#fc6e24',cookie:true,help:'Client ID en OAuth-token kunnen na inloggen via een tijdelijke browsersessie worden verzameld.',docs:'https://www.music-assistant.io/music-providers/soundcloud/'},
  {id:'deezer',name:'Deezer',type:'Tijdelijke browser · Premium',logo:'▥',color:'#8d52cd',cookie:true,help:'We kunnen de ARL-cookie uit een tijdelijke browsersessie overnemen.',docs:'https://www.music-assistant.io/music-providers/deezer/'},
  {id:'spotify',name:'Spotify',type:'Officiële aanmeldflow · Premium',logo:'◉',color:'#179e53',cookie:false,help:'Volg de door Music Assistant geleide officiële inlog- en afspeelgoedkeuringsflow.',docs:'https://www.music-assistant.io/music-providers/spotify/'},
  {id:'tidal',name:'Tidal',type:'Officiële codekoppeling',logo:'◆',color:'#393b43',cookie:false,help:'Tidal vraagt een korte code via link.tidal.com.',docs:'https://www.music-assistant.io/music-providers/tidal/'},
  {id:'qobuz',name:'Qobuz',type:'Inloggen via Music Assistant',logo:'Q',color:'#285fbb',cookie:false,help:'We gebruiken de actuele setup-stappen die Music Assistant zelf levert.',docs:'https://www.music-assistant.io/music-providers/qobuz/'},
  {id:'apple_music',name:'Apple Music',type:'Inloggen via Music Assistant',logo:'♫',color:'#ee6770',cookie:false,help:'De beschikbare methode hangt van je Music Assistant-versie af.',docs:'https://www.music-assistant.io/music-providers/apple-music/'},
  {id:'bandcamp',name:'Bandcamp',type:'Inloggen via Music Assistant',logo:'b',color:'#38869a',cookie:false,help:'We gebruiken de setup-stappen vanuit Music Assistant.',docs:'https://www.music-assistant.io/music-providers/bandcamp/'}
];
const $=s=>document.querySelector(s);
const state={configured:false,connected:false,provider:null,flow:null,captured:{},activeBrowser:false,waiting:false,browserViewport:{width:980,height:720},maIngress:'',userName:'',poToken:null,blockNotice:''};
const escapeHTML = t => String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function message(el,text,variant=''){el.hidden=!text;el.textContent=text||'';el.className='message '+variant}
function errorMessage(e){return typeof e==='string'?e:(e?.message||'Er is iets fout gegaan.');}
function details(){if(state.configured)return {};const url=$('#ma-url').value.trim().replace(/\/$/,'');const token=$('#ma-token').value.trim();if(!url||!token)throw Error('Vul eerst de server-URL en het toegangstoken in.');return {url,token};}
async function post(path,body={}){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});let data;try{data=await r.json()}catch{throw Error('Onverwachte reactie van de lokale server.')}if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:data.error||`Fout ${r.status}`);return data}
async function ma(command,args={}){const out=await post('api/ma',{...details(),command,args});return out.data}
function renderCards(){const grid=$('#provider-grid');grid.innerHTML='';for(const p of PROVIDERS){const button=document.createElement('button');button.type='button';button.className='provider-card'+(state.provider?.id===p.id?' selected':'');button.innerHTML=`<div class="provider-logo" style="background:${p.color}">${escapeHTML(p.logo)}</div><div class="provider-meta"><strong>${escapeHTML(p.name)}</strong><span>${escapeHTML(p.type)}</span></div><span class="provider-arrow">↗</span>`;button.addEventListener('click',()=>selectProvider(p));grid.append(button)}}
async function connect(){const btn=$('#connect-btn'), box=$('#connection-message');btn.disabled=true;message(box,'Verbinding testen…');try{const result=await ma('config/providers');state.connected=true;$('#server-badge').classList.add('connected');$('#server-badge span').textContent='Verbonden';message(box,'Verbinding geslaagd. Je kunt nu een muziekdienst kiezen.','success');renderSources(result)}catch(e){state.connected=false;$('#server-badge').classList.remove('connected');$('#server-badge span').textContent='Niet verbonden';message(box,errorMessage(e),'error')}finally{btn.disabled=false}}
function renderSources(value){const list=$('#existing-list');const sources=Array.isArray(value)?value:Array.isArray(value?.providers)?value.providers:[];const filtered=sources.filter(s=>s.type==='music'||(!s.type&&s.domain));$('#existing-section').hidden=filtered.length===0;list.innerHTML='';for(const s of filtered){const name=String(s.name||s.default_name||s.domain||'Bron');const row=document.createElement('div');row.className='existing-item';const n=document.createElement('span');n.textContent=name;const status=document.createElement('small');status.textContent=s.status?.status||s.status||s.last_error?.message||'Aanwezig';const btn=document.createElement('button');btn.className='btn ghost compact';btn.textContent='Opnieuw koppelen';btn.onclick=()=>reconfigure(s);row.append(n,status,btn);list.append(row)}}
async function selectProvider(p){stopPolling();state.provider=p;state.flow=null;state.captured={};state.waiting=false;await endBrowser();renderCards();$('#wizard-section').hidden=false;$('#wizard-title').textContent=p.name+' koppelen';$('#wizard-section').scrollIntoView({behavior:'smooth',block:'start'});message($('#wizard-status'),p.help);const cont=$('#flow-content');cont.innerHTML=`<p class="flow-description">${escapeHTML(p.help)} <a href="${p.docs}" target="_blank" rel="noreferrer noopener">Handleiding</a></p>`;$('#flow-controls').innerHTML='';state.blockNotice='';renderProviderCheck();if(p.id==='ytmusic')checkPoToken();if(!state.connected){message($('#wizard-status'),'Verbind eerst met Music Assistant via stap 1.','error');return}try{state.flow=await ma('config/providers/setup',{provider_domain:p.id});renderFlow()}catch(e){message($('#wizard-status'),errorMessage(e),'error')}}
async function reconfigure(source){stopPolling();const p=PROVIDERS.find(x=>x.id===source.domain)||{id:source.domain,name:source.name||source.domain,cookie:false,help:'Bestaande bron opnieuw koppelen.',docs:'https://www.music-assistant.io/'};state.provider=p;state.captured={};await endBrowser();renderCards();$('#wizard-section').hidden=false;$('#wizard-title').textContent=p.name+' opnieuw koppelen';$('#wizard-section').scrollIntoView({behavior:'smooth',block:'start'});try{state.flow=await ma('config/providers/reconfigure',{instance_id:source.instance_id});renderFlow()}catch(e){message($('#wizard-status'),errorMessage(e),'error')}}
function getInputType(entry){const key=(entry.key||'').toLowerCase();if(entry.type!=='secure_string'&&/(url|uri)$/.test(key))return 'url';if(entry.type==='secure_string'||/(cookie|token|authorization|password|secret|arl)/.test(key))return 'password';if(entry.type==='integer'||entry.type==='float')return 'number';return 'text'}
function renderFlow(){const step=state.flow;const cont=$('#flow-content'),ctrl=$('#flow-controls');ctrl.innerHTML='';$('#browser-area').hidden=!state.activeBrowser;
if(!step){cont.innerHTML='<p>Music Assistant gaf geen koppelstap terug. Controleer de MA-versie en open de providerinstellingen via de snelkoppeling bij stap 1.</p>';return}const type=(step.type||'').toLowerCase();const desc=step.description?`<p class="flow-description">${escapeHTML(step.description)}</p>`:'';
if(type==='form'){stopPolling();const entries=step.entries||[];const pre=CredentialHelpers.prefill(state.provider?.id,entries,{userName:state.userName,poTokenUrl:state.poToken?.server_url});const html=entries.map(entry=>{const key=entry.key||'';const label=entry.label||key;const eType=entry.type||'string';if(entry.hidden)return '';if(eType==='divider')return '<div class="field full"><hr style="border:0;border-top:1px solid var(--border)"></div>';
if(['label','alert'].includes(eType))return `<p class="flow-description field full">${escapeHTML(entry.description||label)}</p>`;
if(eType==='url'){const url=entry.value||entry.default_value||'';return `<div class="field full"><a href="${escapeHTML(isSafeUrl(url)?url:'#')}" target="_blank" rel="noreferrer noopener">${escapeHTML(label)}</a></div>`}
if(eType==='image'){const src=entry.value||entry.default_value||'';return String(src).startsWith('data:image/')?`<div class="field full"><img src="${escapeHTML(src)}" alt="${escapeHTML(label)}" style="max-width:220px"></div>`:''}
if(eType==='action'){return `<div class="field"><button class="btn muted action-entry" data-key="${escapeHTML(key)}">${escapeHTML(label)}</button></div>`}
let current=Object.hasOwn(state.captured,key)?state.captured[key]:(entry.value??entry.default_value??'');if(current===''&&Object.hasOwn(pre,key))current=pre[key];const opts=Array.isArray(entry.options)?entry.options:[];let input;if(eType==='boolean'){input=`<input type="checkbox" data-key="${escapeHTML(key)}" ${current?'checked':''} style="width:auto;min-width:20px">`;}else if(opts.length){input=`<select data-key="${escapeHTML(key)}" ${entry.multi_value?'multiple':''}>${opts.map(o=>`<option value="${escapeHTML(o.value)}" ${String(current)===String(o.value)?'selected':''} ${o.disabled?'disabled':''}>${escapeHTML(o.title??o.value)}</option>`).join('')}</select>`;}else{input=`<input data-key="${escapeHTML(key)}" type="${getInputType(entry)}" value="${escapeHTML(current)}" ${entry.read_only?'readonly':''} ${entry.required?'required':''} ${eType==='float'?'step="any"':''} ${eType==='integer'?'step="1"':''} autocomplete="off" spellcheck="false">`}
return `<label class="field ${eType==='secure_string'?'full':''}" ${entry.depends_on?`data-depends="${escapeHTML(entry.depends_on)}" data-dep-value="${escapeHTML(JSON.stringify(entry.depends_on_value??null))}" data-dep-not="${escapeHTML(JSON.stringify(entry.depends_on_value_not??null))}"`:``}>${escapeHTML(label)} ${input}${entry.description?`<span class="field-description">${escapeHTML(entry.description)}</span>`:''}${step.errors?.[key]?`<span class="field-description" style="color:#ffada8">${escapeHTML(step.errors[key])}</span>`:''}</label>`}).join('');cont.innerHTML=`<h3 class="flow-title">${escapeHTML(step.title||'Gegevens invullen')}</h3>${desc}${step.errors?.base?`<div class="message error">${escapeHTML(step.errors.base)}</div>`:''}<div class="flow-fields">${html}</div>`;
for(const action of cont.querySelectorAll('.action-entry'))action.addEventListener('click',()=>submitFlow(action.dataset.key));
cont.onchange=updateConditionalFields;updateConditionalFields();addPasteButtons(cont);
const submit=document.createElement('button');submit.id='flow-submit';submit.className='btn primary';submit.textContent=step.last_step?'Opslaan en koppelen ↗':'Verder ↗';submit.addEventListener('click',()=>submitFlow());ctrl.append(submit);
if(state.provider?.cookie){const extraction=document.createElement('button');extraction.className='btn muted';extraction.textContent=state.captured&&Object.keys(state.captured).length?'Gegevens opnieuw ophalen':'Inloggen bij '+state.provider.name;extraction.onclick=()=>startBrowser();ctrl.append(extraction)}
}else if(type==='external'){cont.innerHTML=`<h3 class="flow-title">${escapeHTML(step.title||'Bevestig je aanmelding')}</h3>${desc}<p class="hint">Nadat je de koppeling in het nieuwe tabblad bevestigt, gaat dit scherm automatisch verder.</p>`;if(isSafeUrl(step.url)){const go=document.createElement('button');go.className='btn primary';go.textContent='Open aanmelding ↗';go.onclick=()=>window.open(step.url,'_blank','noopener,noreferrer');ctrl.append(go)}startPolling();
}else if(type==='progress'){cont.innerHTML=`<div class="flow-progress"><span class="spinner"></span><span>${escapeHTML(step.progress_text||step.title||'Even wachten op Music Assistant…')}</span></div>${desc}`;startPolling();
}else if(type==='finish'){stopPolling();cont.innerHTML='<div class="finished">✓ Koppeling afgerond volgens Music Assistant. Je muziekbibliotheek wordt mogelijk nog gesynchroniseerd.</div>';message($('#wizard-status'),'Music Assistant heeft de koppeling bevestigd.','success');state.captured={};endBrowser();ma('config/providers').then(renderSources).catch(()=>{});
}else if(type==='abort'){cont.innerHTML=`<div class="message error">${escapeHTML(step.reason||'Music Assistant heeft de koppeling afgebroken.')}</div>`;
}else{cont.innerHTML=`<p class="flow-description">Onbekend setup-type: ${escapeHTML(type)}. Gebruik de Music Assistant-interface voor deze stap.</p>`}
if(state.provider?.docs){const help=document.createElement('p');help.className='hint';const link=document.createElement('a');link.href=state.provider.docs;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Providerhandleiding en handmatig koppelen ↗';help.append(link);cont.append(help)}
}
function updateConditionalFields(){const panel=$('#flow-content');for(const field of panel.querySelectorAll('[data-depends]')){const other=[...panel.querySelectorAll('[data-key]')].find(x=>x.dataset.key===field.dataset.depends);const actual=other?(other.type==='checkbox'?other.checked:other.value):null;const need=JSON.parse(field.dataset.depValue||'null');const not=JSON.parse(field.dataset.depNot||'null');const yes=need!==null?String(actual)===String(need):!!actual;field.hidden=!yes||(not!==null&&String(actual)===String(not));for(const el of field.querySelectorAll('input,select,button'))el.disabled=field.hidden;}}
function readFields(){const values={};for(const entry of state.flow.entries||[]){if(entry.hidden||['divider','label','alert','image','url','action','icon'].includes(entry.type))continue;const input=[...document.querySelectorAll('#flow-content [data-key]')].find(el=>el.dataset.key===entry.key);if(!input||input.disabled)continue;let v=input.type==='checkbox'?input.checked:input.value;if(entry.type==='integer'&&v!=='')v=Number.parseInt(v,10);if(entry.type==='float'&&v!=='')v=Number.parseFloat(v);if(input.multiple)v=[...input.selectedOptions].map(x=>x.value);values[entry.key]=CredentialHelpers.normalize(state.provider?.id,entry.key,v)}return values}
async function submitFlow(actionKey){const btns=[...$('#flow-controls').querySelectorAll('button')];btns.forEach(x=>x.disabled=true);try{const values=readFields();if(actionKey)values[actionKey]=true;state.flow=await ma('config/flows/submit',{flow_id:state.flow.flow_id,values});state.captured={};renderFlow()}catch(e){message($('#wizard-status'),errorMessage(e),'error')}finally{btns.forEach(x=>x.disabled=false)}}
async function poll(){if(!state.flow||!['external','progress'].includes(state.flow.type))return;try{const next=await ma('config/flows/get',{flow_id:state.flow.flow_id});if(next.step_id!==state.flow.step_id||next.type!==state.flow.type||next.progress_text!==state.flow.progress_text){state.flow=next;renderFlow()}}catch(e){message($('#wizard-status'),'Opvragen van de volgende stap mislukt: '+errorMessage(e),'error')}}
let pollTimer=null;function startPolling(){if(pollTimer)clearInterval(pollTimer);pollTimer=setInterval(()=>{if(!document.hidden)poll()},3000)}function stopPolling(){if(pollTimer)clearInterval(pollTimer);pollTimer=null}
let screenshotURL='',shotBusy=false,browserGeneration=0;
async function shot(){
  if(!state.activeBrowser||shotBusy)return;
  shotBusy=true;const generation=browserGeneration;
  try{
    const r=await fetch('api/browser/screenshot',{cache:'no-store'});
    if(!r.ok)throw Error('Browser niet actief of sessie verlopen. Sluit de browser en begin opnieuw.');
    const blob=await r.blob();
    if(!state.activeBrowser||generation!==browserGeneration)return;
    const address=r.headers.get('X-Browser-URL');if(address){$('#browser-url').textContent=address;showBlockNotice(decodeURIComponent(address))}
    const obj=URL.createObjectURL(blob);$('#browser-image').src=obj;
    if(screenshotURL)URL.revokeObjectURL(screenshotURL);screenshotURL=obj;$('#browser-overlay').hidden=true;
  }catch(e){if(state.activeBrowser&&generation===browserGeneration){$('#browser-overlay').hidden=false;$('#browser-overlay').textContent=errorMessage(e)}}
  finally{shotBusy=false}
}
setInterval(()=>{if(state.activeBrowser&&!document.hidden)shot()},2000);
async function startBrowser(){if(!state.provider?.cookie)return;$('#browser-area').hidden=false;$('#browser-overlay').hidden=false;$('#browser-overlay').textContent='Browser starten…';try{const result=await post('api/browser/start',{provider:state.provider.id});state.activeBrowser=true;state.browserViewport=result.viewport||{width:980,height:720};$('#browser-image').style.aspectRatio=`${state.browserViewport.width}/${state.browserViewport.height}`;$('#browser-url').textContent=result.page;await shot();$('#browser-area').scrollIntoView({behavior:'smooth',block:'start'})}catch(e){message($('#wizard-status'),errorMessage(e),'error');$('#browser-area').hidden=true}}
async function browserAction(path,body={}){try{const r=await post('api/browser/'+path,body);if(r.url)$('#browser-url').textContent=r.url;if(state.lastControlError){message($('#wizard-status'),'');state.lastControlError=false}await shot();return r}catch(e){state.lastControlError=true;message($('#wizard-status'),errorMessage(e),'error');return null}}
async function endBrowser(){browserGeneration++;state.activeBrowser=false;$('#browser-area').hidden=true;$('#browser-overlay').hidden=false;if(screenshotURL)URL.revokeObjectURL(screenshotURL);screenshotURL='';try{await post('api/browser/close')}catch{}}
function patchExtracted(values){Object.assign(state.captured,readFields());const all=state.flow?.entries||[];let count=0;for(const [field,value]of Object.entries(values)){const entry=CredentialHelpers.match(all,field);if(entry){state.captured[entry.key]=value;count++}}renderFlow();return count}
async function extractBrowser(){try{const r=await post('api/browser/extract');if(r.found){await endBrowser();const count=patchExtracted(r.values);message($('#wizard-status'),count?`Gegevens lokaal opgehaald en ingevuld (${count} veld(en)). Controleer de overige velden en kies 'Opslaan en koppelen'.`:'Gegevens gevonden, maar niet automatisch herkend als Music Assistant-velden. Controleer de instellingen van de provider.',count?'success':'error');if(count)highlightSubmit()}else{if(Object.keys(r.values||{}).length)patchExtracted(r.values);message($('#wizard-status'),r.message,'error')}}catch(e){message($('#wizard-status'),errorMessage(e),'error')}}
function isSafeUrl(url){try{return ['https:','http:'].includes(new URL(url).protocol)}catch{return false}}
$('#connect-btn').addEventListener('click',connect);$('#link-btn').addEventListener('click',linkWithMA);$('#toggle-token').addEventListener('click',()=>{const t=$('#ma-token');t.type=t.type==='password'?'text':'password';$('#toggle-token').textContent=t.type==='password'?'Toon token':'Verberg token'});
$('#close-wizard').addEventListener('click',async()=>{stopPolling();await endBrowser();state.flow=null;state.provider=null;state.captured={};$('#wizard-section').hidden=true;renderCards()});$('#refresh-sources').addEventListener('click',async()=>{try{renderSources(await ma('config/providers'))}catch(e){message($('#connection-message'),errorMessage(e),'error')}});
let pointerStart=null;
const browserImage=$('#browser-image');browserImage.draggable=false;browserImage.style.touchAction='none';
function browserPoint(event){const box=browserImage.getBoundingClientRect();return {x:Math.max(0,Math.min(state.browserViewport.width-1,(event.clientX-box.left)/box.width*state.browserViewport.width)),y:Math.max(0,Math.min(state.browserViewport.height-1,(event.clientY-box.top)/box.height*state.browserViewport.height))}}
browserImage.addEventListener('pointerdown',event=>{if(!state.activeBrowser||!event.isPrimary)return;event.preventDefault();pointerStart=browserPoint(event);browserImage.setPointerCapture(event.pointerId)});
browserImage.addEventListener('pointerup',async event=>{if(!pointerStart)return;const start=pointerStart;pointerStart=null;const end=browserPoint(event);if(Math.hypot(end.x-start.x,end.y-start.y)>6)await browserAction('drag',{...start,end_x:end.x,end_y:end.y});else await browserAction('click',start)});
browserImage.addEventListener('pointercancel',()=>{pointerStart=null});
$('#browser-reload').addEventListener('click',()=>browserAction('reload'));$('#browser-end').addEventListener('click',endBrowser);
$('#browser-scroll-up').addEventListener('click',()=>browserAction('scroll',{delta_y:-550,x:state.browserViewport.width/2,y:state.browserViewport.height/2}));
$('#browser-scroll-down').addEventListener('click',()=>browserAction('scroll',{delta_y:550,x:state.browserViewport.width/2,y:state.browserViewport.height/2}));
$('#browser-refresh-image').addEventListener('click',shot);
$('#browser-home').addEventListener('click',()=>browserAction('home'));
let wheelPending=null,wheelBusy=false;
$('#browser-image').addEventListener('wheel',e=>{
  if(!state.activeBrowser)return;e.preventDefault();
  const box=e.currentTarget.getBoundingClientRect();
  const delta=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?state.browserViewport.height:1);
  wheelPending={delta_y:Math.max(-1500,Math.min(1500,(wheelPending?.delta_y||0)+delta)),x:(e.clientX-box.left)/box.width*state.browserViewport.width,y:(e.clientY-box.top)/box.height*state.browserViewport.height};
  if(!wheelBusy)flushWheel();
},{passive:false});
async function flushWheel(){wheelBusy=true;const generation=browserGeneration;try{while(wheelPending&&state.activeBrowser&&generation===browserGeneration){const body=wheelPending;wheelPending=null;await browserAction('scroll',body)}}finally{wheelPending=null;wheelBusy=false}}
$('#browser-reveal').addEventListener('click',()=>{const input=$('#browser-input');input.type=input.type==='password'?'text':'password'});$('#browser-type').addEventListener('click',async()=>{const field=$('#browser-input');const value=field.value;field.value='';await browserAction('type',{value})});$('#browser-input').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();$('#browser-type').click()}});$('#browser-enter').addEventListener('click',()=>browserAction('key',{value:'Enter'}));$('#browser-tab').addEventListener('click',()=>browserAction('key',{value:'Tab'}));$('#browser-extract').addEventListener('click',extractBrowser);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll()});
try{sessionStorage.removeItem('ma-token');sessionStorage.removeItem('ma-url')}catch{}
loadSettings();
renderCards();

async function loadSettings(){
  try {
    const response=await fetch('api/settings',{cache:'no-store'});
    if(!response.ok){let failure={};try{failure=await response.json()}catch{}throw Error(typeof failure.detail==='string'?failure.detail:`Appconfiguratie kon niet worden geladen (HTTP ${response.status}). Werk de app bij en herstart; open daarna opnieuw via Home Assistant.`)}
    const settings=await response.json();state.configured=settings.configured;state.maIngress=settings.ma_ingress||'';state.userName=settings.user_name||'';
    $('#ma-url').value=settings.ma_url||'';
    $('#auto-link').hidden=state.configured||!state.maIngress;
    $('#manual-connection').open=!state.configured&&!state.maIngress;
    if(state.configured){
      $('#ma-url').disabled=true;$('#ma-token').disabled=true;$('#toggle-token').hidden=true;
      $('#ma-token').placeholder='Ingesteld in Home Assistant';
      message($('#connection-message'),'Verbindingsgegevens uit de appconfiguratie geladen.');
    }else if(state.maIngress){
      message($('#connection-message'),'Music Assistant gevonden op deze Home Assistant. Tik op Koppel met Music Assistant.');
    }else if(settings.ma_state&&settings.ma_state!=='started'){
      message($('#connection-message'),'Music Assistant is geïnstalleerd maar niet gestart. Start de app Music Assistant in Home Assistant en open deze pagina opnieuw.','error');
    }
    const links=CredentialHelpers.links(settings.ma_ui_url);
    const nav=$('#ma-navigation');nav.replaceChildren();
    for(const [key,label] of Object.entries({home:'Open Music Assistant',providers:'Muziekproviders',profile:'Profiel / API-token',api:'API-documentatie'})){
      if(!links[key])continue;
      const a=document.createElement('a');a.className='btn ghost compact';a.textContent=label+' ↗';a.href=links[key];a.target='_blank';a.rel='noopener noreferrer';nav.append(a);
    }
    if(!links.home)$('#navigation-hint').textContent='Stel ma_ui_url in bij de appconfiguratie voor directe snelkoppelingen. Gebruik voor toegang op afstand het HA Music Assistant-paneel of een bestaand HTTPS-adres.';
    if(state.configured)await connect();
  }catch(e){message($('#connection-message'),errorMessage(e),'error')}
}
async function linkWithMA(){
  const btn=$('#link-btn'),box=$('#connection-message');btn.disabled=true;message(box,'Koppelen met Music Assistant…');
  let token='';
  try{
    // Same-origin HA ingress request: MA recognises the signed-in HA user, exactly like its own panel.
    const r=await fetch(state.maIngress+'api',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({message_id:'connect-link',command:'auth/token/create',args:{name:'Music Assistant Connect'}})});
    if(r.status===503)throw Error('Open eerst eenmalig Music Assistant via de zijbalk en rond de eerste stappen af. Probeer het daarna opnieuw.');
    if(r.status===401||r.status===403)throw Error('Music Assistant geeft je account geen toestemming. Gebruik een Home Assistant-beheerder of verbind handmatig.');
    if(!r.ok)throw Error('Music Assistant reageerde niet zoals verwacht. Werk Music Assistant bij of verbind handmatig.');
    try{token=await r.json()}catch{token=''}
    if(typeof token!=='string'||token.length<8)throw Error('Music Assistant gaf geen toegangssleutel terug. Verbind handmatig.');
    const result=await post('api/link',{token});
    await loadSettings();
    message(box,result.saved?'Gekoppeld. De sleutel is veilig in de appconfiguratie bewaard.':'Gekoppeld voor nu. Opslaan in de appconfiguratie lukte niet; na een herstart is opnieuw koppelen nodig.',result.saved?'success':'error');
  }catch(e){message(box,errorMessage(e),'error');$('#manual-connection').open=true}
  finally{token='';btn.disabled=false}
}
function renderProviderCheck(){
  const box=$('#provider-check');box.replaceChildren();box.hidden=true;
  if(state.provider?.id!=='ytmusic'||!state.poToken)return;
  const s=state.poToken;box.hidden=false;
  const text=document.createElement('p');
  if(s.reachable){box.className='message success';text.textContent='✓ YT Music PO Token Generator draait. Music Assistant gebruikt hem automatisch.';box.append(text);return}
  box.className='message error';
  text.textContent=!s.known?'Kon niet controleren of de YT Music PO Token Generator draait. Controleer dat die app geïnstalleerd en gestart is.':s.installed?'De YT Music PO Token Generator is geïnstalleerd maar reageert niet. Open hem, tik op Starten en kom terug.':'YouTube Music heeft de app YT Music PO Token Generator nodig. Open hem, tik op Installeren en daarna op Starten. Kom dan terug naar dit scherm.';
  const a=document.createElement('a');a.className='btn ghost compact';a.href=s.app_path;a.target='_top';a.textContent='Open PO Token Generator ↗';
  const again=document.createElement('button');again.type='button';again.className='btn ghost compact';again.textContent='Opnieuw controleren';again.onclick=checkPoToken;
  const row=document.createElement('div');row.className='line-actions';row.append(a,again);box.append(text,row);
}
async function checkPoToken(){try{const r=await fetch('api/ytmusic/status',{cache:'no-store'});if(r.ok)state.poToken=await r.json()}catch{}renderProviderCheck()}
function showBlockNotice(address){const text=CredentialHelpers.blocked(state.provider?.id,address);if(text&&text!==state.blockNotice)message($('#wizard-status'),text,'error');state.blockNotice=text}
function highlightSubmit(){const submit=$('#flow-submit');if(!submit)return;submit.classList.add('attention');submit.scrollIntoView({behavior:'smooth',block:'center'});submit.focus({preventScroll:true})}
function addPasteButtons(container){
  for(const input of container.querySelectorAll('input[type="password"]')){
    if(input.readOnly)continue;
    const button=document.createElement('button');button.type='button';button.className='btn ghost compact';button.textContent='Plak uit klembord';
    button.onclick=async()=>{
      try{input.value=CredentialHelpers.normalize(state.provider?.id,input.dataset.key,await navigator.clipboard.readText());input.dispatchEvent(new Event('change',{bubbles:true}));}
      catch{input.focus();message($('#wizard-status'),'Klembord niet beschikbaar. Houd het invoerveld ingedrukt en kies Plakken.');}
    };
    input.after(button);
  }
}
