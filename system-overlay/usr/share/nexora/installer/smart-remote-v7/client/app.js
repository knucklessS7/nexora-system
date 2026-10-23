'use strict';
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const status = $('#eventStatus');
const titles = {remote:'Controle principal',gamepad:'Gamepad virtual',mouse:'Mouse e teclado',apps:'Aplicativos'};
let currentMode = 'remote';
let socket = null, reconnectTimer = null;
let connected = false, stopped = false, csrf = '';
const pendingPings = new Map();
let inputSeq = 0;
function feedback(s){ status.textContent = s; }
function transport(message){
  if(!connected || socket?.readyState!==WebSocket.OPEN)return;
  if(socket.bufferedAmount>16384){socket.close();return;}
  socket.send(JSON.stringify({...message,v:1,seq:++inputSeq}));
}
function connection(label){$('#connLabel').textContent=label;$('.status').textContent=label;$('.gamepad-player').textContent=connected?'CONECTADO':'DESCONECTADO';}
async function api(path,body){
  const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:body?JSON.stringify(body):undefined});
  if(r.status===401){window.location.replace('/pair');throw new Error('401: Sessão expirada');}
  if(!r.ok)throw new Error((await r.text()).slice(0,180));return r.json();
}
async function connect(){
  if(stopped)return;
  try{
    const state=await api('/api/state');csrf=state.csrf;
    $$('[data-app]').forEach(b=>{b.disabled=!state.apps.includes(b.dataset.app);b.title=b.disabled?'Não instalado ou não configurado':'';});
    socket=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws`);inputSeq=0;
    socket.onopen=()=>socket.send(JSON.stringify({type:'hello',v:1,csrf}));
    socket.onmessage=e=>{
      const m=JSON.parse(e.data);
      if(m.type==='ready'){connected=true;connection(state.fake?'TESTE SIMULADO':'Conectado');transport({type:'mode',mode:currentMode});feedback('Controle autorizado pela TV.');}
      if(m.type==='error'||m.type==='app_result')feedback(m.message);
      if(m.type==='pong'&&pendingPings.has(m.seq)){connection(`Conectado · ${Math.round(performance.now()-pendingPings.get(m.seq))} ms`);pendingPings.delete(m.seq);}
    };
    socket.onclose=()=>{connected=false;releaseInput();pendingPings.clear();connection('Desconectado');if(!stopped)reconnectTimer=setTimeout(connect,2000);};
  }catch(e){
    if(String(e.message).includes('401') || String(e.message).includes('Sessão inválida')){stopped=true;window.location.replace('/pair');return;}
    connection('Sem conexão');if(!stopped)reconnectTimer=setTimeout(connect,2500);
  }
}
setInterval(()=>{if(connected){pendingPings.clear();pendingPings.set(inputSeq+1,performance.now());transport({type:'ping'});}},750);
// V8.4: proteção contra seleção, arrasto nativo e menu de toque prolongado
// do iOS Safari. Só atua em superfícies interativas, não em campos de texto.
const NO_CALLOUT = '#panel-gamepad .gamepad-card, #panel-remote button[data-command], #panel-mouse .touchpad, #panel-mouse .mouse-actions button, #panel-apps .app-tile';
const BLOCK_GESTURE = '#panel-gamepad .shoulders button, #panel-gamepad .dpad.small button, #panel-gamepad .face-buttons button, #panel-gamepad .midbuttons button, #panel-gamepad .joystick';
function isNoCalloutTarget(event) {
  return event.target instanceof Element && !!event.target.closest(NO_CALLOUT) &&
    !event.target.closest('input, textarea, select, [contenteditable="true"]');
}
['contextmenu', 'selectstart', 'dragstart'].forEach(type => {
  document.addEventListener(type, event => {
    if (!isNoCalloutTarget(event)) return;
    event.preventDefault();
  }, { capture: true });
});
// Em iOS Safari, impedir o comportamento padrão em touchstart também
// evita a seleção pelo toque longo. Os comandos usam Pointer Events;
// tocar no editor e nos sliders não passa por esta proteção.
document.addEventListener('touchstart', event => {
  if (!(event.target instanceof Element) || !event.target.closest(BLOCK_GESTURE)) return;
  if (event.cancelable) event.preventDefault();
}, { capture: true, passive: false });
// Limpa qualquer seleção anterior ao iniciar o toque no controle.
// Não interfere com o toque prolongado usado para MOVER botões em Personalizar.
document.addEventListener('pointerdown', event => {
  if (!isNoCalloutTarget(event)) return;
  const selection = window.getSelection?.();
  if (selection && selection.rangeCount) selection.removeAllRanges();
}, { capture: true });

const buttonPointers=new Map();
const pointerOwners=new Map();
function press(btn,phase){const control=btn.dataset.command;if(!control)return;if(control==='HOME'){if(phase==='down'){changeTab('remote');transport({type:'home'});feedback('Voltando ao início…');}return;}btn.classList.toggle('pressed',phase==='down');transport({type:'button',control,phase});}
$$('[data-command]').forEach(btn=>{
  btn.addEventListener('pointerdown',e=>{
    if(e.button!==0||btn.disabled||btn.closest('#panel-gamepad .dpad.small'))return;
    e.preventDefault();
    if(buttonPointers.has(btn) || pointerOwners.has(e.pointerId))return;
    buttonPointers.set(btn,e.pointerId);
    pointerOwners.set(e.pointerId,btn);
    btn.setPointerCapture(e.pointerId);
    press(btn,'down');
  });
  function end(e){
    if(buttonPointers.get(btn)!==e.pointerId)return;
    buttonPointers.delete(btn);
    if(pointerOwners.get(e.pointerId)===btn)pointerOwners.delete(e.pointerId);
    press(btn,'up');
  }
  btn.addEventListener('pointerup',end);btn.addEventListener('pointercancel',end);btn.addEventListener('lostpointercapture',end);
  btn.addEventListener('keydown',e=>{if([' ','Enter'].includes(e.key)&&!e.repeat){e.stopPropagation();e.preventDefault();press(btn,'down');}});
  btn.addEventListener('keyup',e=>{if([' ','Enter'].includes(e.key)){e.stopPropagation();e.preventDefault();press(btn,'up');}});
});
async function tryLandscape(){
  if(!document.body.classList.contains('gamepad-active'))return;
  let fullscreenOk=false, locked=false;
  try{if(!document.fullscreenElement && document.documentElement.requestFullscreen){await document.documentElement.requestFullscreen({navigationUI:'hide'});fullscreenOk=true;}else fullscreenOk=!!document.fullscreenElement;}catch(e){/* Browser may deny full-screen; layout still adapts */}
  try{if(screen.orientation && typeof screen.orientation.lock==='function'){await screen.orientation.lock('landscape');locked=true;}}catch(e){/* Many browsers including iOS Safari disallow orientation lock */}
  feedback(locked?'orientação horizontal solicitada.':fullscreenOk?'tela cheia ativada; gire o aparelho se necessário.':'gire o celular manualmente; o navegador não autorizou rotação/tela cheia.');
}
const resetters=[];
// One pointer owns the D-pad gesture; hit-testing follows its current position.
const gameDpad=$('#panel-gamepad .dpad.small');
let dpadPointer=null, dpadDirection=null;
function handoffDpad(next){
  if(next===dpadDirection)return;
  if(dpadDirection)press(dpadDirection,'up');
  dpadDirection=next;
  if(next)press(next,'down');
}
function directionAt(x,y){
  const hit=document.elementFromPoint(x,y)?.closest('[data-command^="GP_"]');
  return hit && gameDpad.contains(hit) && !hit.disabled ? hit : null;
}
function endDpad(){
  const pointer=dpadPointer;dpadPointer=null;
  handoffDpad(null);
  if(pointer!==null){
    pointerOwners.delete(pointer);
    if(gameDpad.hasPointerCapture(pointer))gameDpad.releasePointerCapture(pointer);
  }
}
resetters.push(endDpad);
gameDpad.addEventListener('pointerdown',e=>{
  if(e.button!==0||dpadPointer!==null||pointerOwners.has(e.pointerId)||window.GamepadLayoutEditor?.isEditing())return;
  e.preventDefault();dpadPointer=e.pointerId;pointerOwners.set(e.pointerId,gameDpad);
  gameDpad.setPointerCapture(e.pointerId);handoffDpad(directionAt(e.clientX,e.clientY));
});
gameDpad.addEventListener('pointermove',e=>{
  if(e.pointerId!==dpadPointer)return;
  e.preventDefault();handoffDpad(directionAt(e.clientX,e.clientY));
});
for(const type of ['pointerup','pointercancel','lostpointercapture']){
  gameDpad.addEventListener(type,e=>{if(e.pointerId===dpadPointer)endDpad();});
}

window.addEventListener('gamepad-editor-start',()=>releaseInput());
function releaseInput(){
  transport({type:'release_all'});buttonPointers.clear();pointerOwners.clear();resetters.forEach(f=>f());
  for(const c of keysDown)transport({type:'button',control:c,phase:'up'});keysDown.clear();
  $$('[data-command].pressed').forEach(b=>press(b,'up'));
  $$('[data-stick]').forEach(el=>{el.querySelector('.knob').style.transform='translate(-50%,-50%)';if(currentMode==='gamepad')transport({type:'axis',stick:el.dataset.stick,x:0,y:0});});
}
async function exitLandscape(){
  try{screen.orientation?.unlock?.()}catch(e){}
  try{if(document.fullscreenElement && document.exitFullscreen)await document.exitFullscreen()}catch(e){}
}
function changeTab(mode){
  if(mode!=='gamepad')window.GamepadLayoutEditor?.cancel();
  releaseInput();currentMode=mode;transport({type:'mode',mode});
  if(mode!=='gamepad')exitLandscape();
  document.body.classList.toggle('gamepad-active',mode==='gamepad');
  document.documentElement.classList.toggle('gamepad-active',mode==='gamepad');
  $$('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===mode));
  $$('.panel').forEach(p=>p.classList.toggle('visible',p.id===`panel-${mode}`));
  $('#modeTitle').textContent=titles[mode];
  if(mode==='gamepad'){window.dispatchEvent(new Event('gamepad-layout-visible'));feedback('Gamepad aberto. Toque em Horizontal para tentar tela cheia e rotação.');}
}
$('#rotateBtn').addEventListener('click',tryLandscape);
$('#retryRotateBtn').addEventListener('click',tryLandscape);
$('#exitGamepadBtn').addEventListener('click',()=>changeTab('remote'));
$$('.tab').forEach(btn=>btn.addEventListener('click',()=>{ 
  changeTab(btn.dataset.tab);
  if(btn.dataset.tab==='gamepad' && matchMedia('(pointer:coarse) and (max-width: 1000px)').matches)void tryLandscape();
}));
$('#logoutBtn').addEventListener('click',async()=>{
  if(stopped)return;
  stopped=true;clearTimeout(reconnectTimer);releaseInput();
  try{await api('/api/logout',{});}catch(e){}
  socket?.close();connected=false;
  window.location.replace('/pair');
});
$$('[data-app]').forEach(btn=>btn.addEventListener('click',()=>transport({type:'launch_app',app:btn.dataset.app})));
$('#textForm').addEventListener('submit',e=>{e.preventDefault();const value=$('#typeInput').value;if(!value)return;transport({type:'type_text',text:value});$('#typeInput').value='';});
const pad=$('#touchpad'); let last=null, padPointer=null;
resetters.push(()=>{last=null;padPointer=null;});
pad.addEventListener('pointerdown',e=>{if(padPointer!==null)return;padPointer=e.pointerId;last={x:e.clientX,y:e.clientY};pad.setPointerCapture(e.pointerId);});
pad.addEventListener('pointermove',e=>{if(!last||padPointer!==e.pointerId)return;const dx=Math.round(e.clientX-last.x),dy=Math.round(e.clientY-last.y);if(dx||dy)transport({type:'mouse_move',dx,dy});last={x:e.clientX,y:e.clientY};});
function endPad(e){if(e.pointerId===padPointer){last=null;padPointer=null;}}
pad.addEventListener('pointerup',endPad);pad.addEventListener('pointercancel',endPad);pad.addEventListener('lostpointercapture',endPad);
$$('[data-stick]').forEach(el=>{
  let active=null;const knob=$('.knob',el);
  function update(e){
    const r=el.getBoundingClientRect(), k=knob.getBoundingClientRect();
    const radiusX=Math.max(1,(r.width-k.width)/2),radiusY=Math.max(1,(r.height-k.height)/2);
    let x=(e.clientX-r.left-r.width/2)/radiusX,y=(e.clientY-r.top-r.height/2)/radiusY;
    const length=Math.hypot(x,y);if(length>1){x/=length;y/=length;}
    const scaleX=r.width/el.offsetWidth,scaleY=r.height/el.offsetHeight;
    knob.style.transform=`translate(calc(-50% + ${x*radiusX/scaleX}px),calc(-50% + ${y*radiusY/scaleY}px))`;
    transport({type:'axis',stick:el.dataset.stick,x,y});
  }
  el.addEventListener('pointerdown',e=>{
    if(e.button!==0||e.target.closest('[data-command]')||active!==null||pointerOwners.has(e.pointerId)||window.GamepadLayoutEditor?.isEditing())return;
    e.preventDefault();active=e.pointerId;pointerOwners.set(active,el);el.setPointerCapture(active);update(e);
  });
  el.addEventListener('pointermove',e=>{if(active===e.pointerId){e.preventDefault();update(e);}});
  function end(e){
    if(active===null||(e&&e.pointerId!==active))return;
    const pointer=active;active=null;pointerOwners.delete(pointer);
    knob.style.transform='translate(-50%,-50%)';
    if(currentMode==='gamepad')transport({type:'axis',stick:el.dataset.stick,x:0,y:0});
    if(el.hasPointerCapture(pointer))el.releasePointerCapture(pointer);
  }
  resetters.push(()=>end());
  for(const type of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(type,end);
});
const keyMap={ArrowUp:'UP',ArrowDown:'DOWN',ArrowLeft:'LEFT',ArrowRight:'RIGHT',Enter:'SELECT',Escape:'BACK'};
const keysDown=new Set();
window.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA'].includes(document.activeElement.tagName))return;const c=currentMode==='gamepad'?({ArrowUp:'GP_UP',ArrowDown:'GP_DOWN',ArrowLeft:'GP_LEFT',ArrowRight:'GP_RIGHT',Enter:'START',Escape:'SELECT_GAME'}[e.key]):keyMap[e.key];if(!c)return;e.preventDefault();if(keysDown.has(c))return;keysDown.add(c);transport({type:'button',control:c,phase:'down'});});
window.addEventListener('keyup',e=>{const c=currentMode==='gamepad'?({ArrowUp:'GP_UP',ArrowDown:'GP_DOWN',ArrowLeft:'GP_LEFT',ArrowRight:'GP_RIGHT',Enter:'START',Escape:'SELECT_GAME'}[e.key]):keyMap[e.key];if(!c||!keysDown.has(c))return;e.preventDefault();keysDown.delete(c);transport({type:'button',control:c,phase:'up'});});
window.addEventListener('blur',releaseInput);
document.addEventListener('visibilitychange',()=>{if(document.hidden)releaseInput();});
window.addEventListener('pagehide',releaseInput);
document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement && document.body.classList.contains('gamepad-active'))feedback('Tela cheia encerrada. O controle permanece disponível.');});

connect();
