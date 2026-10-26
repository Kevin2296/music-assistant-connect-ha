'use strict';
let clientId='';
if(CONFIG.provider==='soundcloud')chrome.webRequest.onBeforeRequest.addListener(request=>{
  const value=new URL(request.url).searchParams.get('client_id');
  if(value&&/^[a-zA-Z0-9]{32}$/.test(value))clientId=value;
},{urls:['https://*.soundcloud.com/*']});
async function capture(){
  const urls={ytmusic:'https://music.youtube.com/',soundcloud:'https://soundcloud.com/',deezer:'https://www.deezer.com/'};
  const cookies=await chrome.cookies.getAll({url:urls[CONFIG.provider]});
  const values={};
  if(CONFIG.provider==='ytmusic')values.cookie=cookies.map(c=>`${c.name}=${c.value}`).join('; ');
  if(CONFIG.provider==='soundcloud'){
    const token=cookies.find(c=>c.name==='oauth_token')?.value;
    if(token)values.authorization='OAuth '+token.replace(/^OAuth /,'');
    if(clientId)values.client_id=clientId;
  }
  if(CONFIG.provider==='deezer'){
    const arl=cookies.find(c=>c.name.toLowerCase()==='arl')?.value;
    if(arl)values.arl=arl;
  }
  await fetch(CONFIG.bridge,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values})});
}
async function poll(){
  try{
    const response=await fetch(CONFIG.bridge,{cache:'no-store'});
    if(response.ok){
      const command=await response.json();
      if(command.navigate){const [active]=await chrome.tabs.query({active:true,lastFocusedWindow:true});if(active?.id)await chrome.tabs.update(active.id,{url:command.navigate});}
      if(command.capture)await capture();
      const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true});
      if(tab?.url)await fetch(CONFIG.bridge,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'status',url:tab.url})});
    }
  }
  catch{}finally{setTimeout(poll,1000)}
}
poll();
