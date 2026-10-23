"use strict";
const pinInput = document.querySelector('#pin');
const form = document.querySelector('#pairForm');
const submit = document.querySelector('#pairBtn');
const message = document.querySelector('#pairMessage');
const waiting = document.querySelector('#pairWait');
let activeRequest = false;
function showStatus(text, error=false) { message.textContent=text; message.classList.toggle('error',error); }
async function api(path,body) {
  const response=await fetch(path, { method:body?'POST':'GET', credentials:'same-origin',
    headers:body?{'Content-Type':'application/json'}:{},
    body:body?JSON.stringify(body):undefined,cache:'no-store' });
  if(!response.ok) throw new Error(response.status===429?'Muitas tentativas. Aguarde e tente novamente.':
    response.status===403?'Acesso negado. Confira a conexão de rede.':'Não foi possível validar. Confira o PIN na TV.');
  return response.json();
}
async function checkExisting() {
  try {
    const res=await fetch('/api/state',{cache:'no-store',credentials:'same-origin'});
    if(res.ok) window.location.replace('/control');
  } catch (_) { /* Sem serviço ativo: permitir exibir tela de acesso. */ }
}
form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(activeRequest)return;
  const pin=pinInput.value.replace(/\D/g,'');
  if(!/^\d{6}$/.test(pin)){showStatus('Digite os 6 números do PIN exibido na TV.',true);pinInput.focus();return;}
  activeRequest=true;submit.disabled=true;pinInput.disabled=true;
  try {
    const result=await api('/api/pair',{pin,name:navigator.userAgentData?.platform||navigator.platform||'Celular'});
    if(!result.approved)throw new Error('PIN não autorizado.');
    pinInput.value='';showStatus('Vinculado! Abrindo o controle…');window.location.replace('/control');
  } catch (e) {
    showStatus(e.message||'Não foi possível conectar.',true);waiting.hidden=true;
  } finally {activeRequest=false;submit.disabled=false;pinInput.disabled=false;}
});
pinInput.addEventListener('input',()=>{pinInput.value=pinInput.value.replace(/\D/g,'').slice(0,6);message.classList.remove('error');if(pinInput.value.length===6&&!activeRequest)form.requestSubmit();});
window.addEventListener('online',checkExisting);
window.addEventListener('pageshow',checkExisting);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkExisting();});
checkExisting();
