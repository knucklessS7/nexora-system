(() => {
  'use strict';
  if (window.__streamTV) return;
  window.__streamTV = true;
  const cfg = globalThis.STREAM_TV_PROFILE;
  if (!cfg) return;
  const root = document.documentElement;
  root.dataset.streamTv = cfg.id;
  const ALL = 'a[href],button,input:not([type="hidden"]),select,textarea,[role="button"],[role="link"],[role="tab"],[role="menuitem"],[role="option"],[tabindex],.title-card,.slider-item .ptrack-content';
  const query = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  let current = null, enabled = true, tv = true, pad = true, diagnostic = false, keyboardAt = -1000;
  let editing = null, route = location.pathname, busy = false, epoch = 0, pending = null, busyScope = null;
  let lastPad = '', nextRepeat = 0, column = null, observedScope = null, scopeCheck = 0;
  const events = [];
  const stateKey = `stream-tv-${cfg.id}`;
  try { const state = JSON.parse(localStorage.getItem(stateKey) || '{}'); tv = state.tv !== false; pad = state.pad !== false; } catch (_) {}
  const save = () => { try { localStorage.setItem(stateKey, JSON.stringify({tv, pad})); } catch (_) {} };
  const rendered = el => {
    if (!el?.isConnected || el.closest('[hidden],[inert],[aria-hidden="true"]') || el.matches(':disabled,[aria-disabled="true"]')) return false;
    for (let n = el; n; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.display === 'none' || s.visibility !== 'visible' || +s.opacity < .08) return false;
    }
    const r = el.getBoundingClientRect();
    return r.width >= 6 && r.height >= 6;
  };
  function visibleBox(el, allowVertical = false) {
    if (!rendered(el)) return null;
    const r = el.getBoundingClientRect();
    let left = Math.max(0, r.left), right = Math.min(innerWidth, r.right);
    let top = allowVertical ? r.top : Math.max(0, r.top), bottom = allowVertical ? r.bottom : Math.min(innerHeight, r.bottom);
    for (let n = el.parentElement; n && n !== document.body && n !== root; n = n.parentElement) {
      const s = getComputedStyle(n), b = n.getBoundingClientRect();
      if (/(hidden|clip|auto|scroll)/.test(s.overflowX)) { left = Math.max(left, b.left); right = Math.min(right, b.right); }
      // Off-screen children of a vertical scroller can be brought into view.
      if (/(hidden|clip)/.test(s.overflowY) || (!allowVertical && /(auto|scroll)/.test(s.overflowY))) { top = Math.max(top, b.top); bottom = Math.min(bottom, b.bottom); }
    }
    if (right - left < Math.min(24, r.width * .5) || bottom - top < Math.min(16, r.height * .5)) return null;
    if (top >= 0 && bottom <= innerHeight) {
      const hit = document.elementFromPoint((left + right) / 2, (top + bottom) / 2);
      if (hit && hit !== el && !el.contains(hit) && !hit.contains(el)) return null;
    }
    return {x:(left + right)/2, y:(top + bottom)/2, left, right, top, bottom};
  }
  function scope() {
    return query('[role="dialog"],[aria-modal="true"],dialog[open]'+(cfg.modal?','+cfg.modal:'')).filter(rendered).at(-1)
      || document.fullscreenElement
      || (cfg.player && query(cfg.player).find(e=>rendered(e) && e.querySelector('video')))
      || document;
  }
  const nativeTV = () => cfg.id === 'youtube' && location.pathname.startsWith('/tv') && !!document.querySelector('ytlr-app,ytlr-guide,ytlr-browse');
  function candidates(vertical = false) {
    const s = scope();
    const list = query(ALL, s).filter(e => !e.closest('[data-stv-ui]') && !e.matches(cfg.exclude || ':not(*)') && visibleBox(e, vertical));
    const leaf = list.filter(e => !list.some(other => other !== e && e.contains(other)));
    // Prefer a single cover/title link per card; retain separate player and menu controls.
    const seen = new Set();
    return leaf.filter(e => {
      const card = cfg.cards && e.closest(cfg.cards);
      if (!card) return true;
      const primary = leaf.find(n=>card.contains(n) && n.matches('a[href]')) || leaf.find(n=>card.contains(n));
      if(e !== primary || seen.has(card))return false;
      seen.add(card);return true;
    });
  }
  const row = el => el?.closest(cfg.rows || '[role="list"]') || el?.closest('nav,header,ul,ol,[role="list"]');
  function log(action, extra = {}) {
    if (!diagnostic) return;
    const r = current?.getBoundingClientRect();
    events.push({time:Date.now(), action, tag:current?.tagName || null, role:current?.getAttribute('role') || null,
      box:r ? [r.x,r.y,r.width,r.height].map(Math.round) : null, visible:!!visibleBox(current), ...extra});
    if (events.length > 400) events.shift();
  }
  function notice(message) {
    let e = document.getElementById('stv-notice');
    if (!e) { e = document.createElement('div'); e.id = 'stv-notice'; e.dataset.stvUi = '1'; e.setAttribute('role','status'); document.body.append(e); }
    e.textContent = message; clearTimeout(notice.timer); notice.timer = setTimeout(() => e.remove(), 4200);
  }
  function mark(el, horizontal = false) {
    if (!el || !rendered(el)) return;
    query('[data-stv-focus]').forEach(n => n.removeAttribute('data-stv-focus'));
    current = el; el.dataset.stvFocus = '1';
    if(cfg.id==='netflix') { el.dispatchEvent(new MouseEvent('mouseover',{bubbles:true})); el.dispatchEvent(new MouseEvent('mouseenter',{bubbles:false})); }
    if (!el.matches(ALL)) el.tabIndex = -1;
    el.focus({preventScroll:true});
    el.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});
    if (horizontal || column === null) column = el.getBoundingClientRect().x + el.getBoundingClientRect().width / 2;
    log('focus');
  }
  function cancel() { epoch++; busy = false; pending = null; }
  async function advance(direction) {
    const group = row(current);
    if (!group) return false;
    const selector = direction === 'ArrowRight' ? cfg.next : cfg.previous;
    const arrow = selector && query(selector,group).find(e=>visibleBox(e));
    let scroller = current.parentElement;
    while (scroller && scroller !== group.parentElement && !(scroller.scrollWidth > scroller.clientWidth + 20 && /(auto|scroll)/.test(getComputedStyle(scroller).overflowX))) scroller = scroller.parentElement;
    if (scroller === group.parentElement) scroller = null;
    if (!arrow && !scroller) return false;
    const before = new Set(candidates().filter(e=>row(e)===group)), old = current, token = ++epoch;
    busy = true; busyScope = scope();
    if (arrow) arrow.click(); else scroller.scrollBy({left:(direction === 'ArrowRight' ? 1 : -1)*scroller.clientWidth*.8,behavior:'smooth'});
    let stable = 0, signature = '', moved = false;
    const start = performance.now();
    while (performance.now()-start < 2600 && token===epoch) {
      await new Promise(r=>setTimeout(r,70));
      const now = query(ALL,group).slice(0,100).map(e=>Math.round(e.getBoundingClientRect().x)).join(',');
      if (now !== signature) { if (signature) moved=true; signature=now; stable=performance.now(); }
      if (performance.now()-stable>210 && performance.now()-start>(moved ? 250 : 900)) break;
    }
    if (token!==epoch) return true;
    if (scope()!==busyScope || !old.isConnected) {cancel();return true;}
    busy = false;
    const items=candidates().filter(e=>row(e)===group && e!==old && !e.matches([cfg.next,cfg.previous].filter(Boolean).join(',') || ':not(*)'));
    const fresh=items.filter(e=>!before.has(e));
    const pool=fresh.length?fresh:items;
    pool.sort((a,b)=>a.getBoundingClientRect().left-b.getBoundingClientRect().left);
    if (pool.length) mark(direction==='ArrowRight'?pool[0]:pool.at(-1),true);
    const next=pending; pending=null;if(next) move(next);
    return true;
  }
  function move(direction) {
    if (busy) { if (scope()===busyScope) {pending=direction; return;} cancel(); }
    const vertical = /Up|Down/.test(direction), positive = /Right|Down/.test(direction);
    const list = candidates(vertical);
    if (!list.length) return;
    if (!current?.isConnected || !list.includes(current)) { mark(list.find(e=>visibleBox(e)) || list[0],true); return; }
    const box = visibleBox(current,true), ownRow = row(current);
    if (!box) { mark(list[0],true); return; }
    const choices = list.filter(e=>e!==current).map(e=>({e,b:visibleBox(e,true)})).filter(({b})=>positive ? (vertical ? b.y>box.y+12 : b.x>box.x+12) : (vertical ? b.y<box.y-12 : b.x<box.x-12));
    const same = choices.filter(({e,b})=>!vertical && row(e)===ownRow && Math.abs(b.y-box.y)<Math.max(45,(box.bottom-box.top)*.65));
    let pool = !vertical ? same : choices;
    pool = pool.filter(({b})=>vertical || Math.abs(b.y-box.y)<Math.max(65,(box.bottom-box.top)*.7));
    pool.sort((a,b)=>{
      const score = o => vertical ? Math.abs(o.b.y-box.y)*2.5 + Math.abs(o.b.x-(column ?? box.x)) : Math.abs(o.b.x-box.x)+Math.abs(o.b.y-box.y)*4;
      return score(a)-score(b);
    });
    if (pool.length) mark(pool[0].e,!vertical); else if (!vertical) void advance(direction);
    log(direction,{count:list.length});
  }
  function back() {
    cancel();
    if (editing || document.activeElement?.matches('input,textarea,select,[contenteditable="true"]')) { editing=null;document.activeElement?.blur();notice('Navegação por controle');return; }
    if (document.fullscreenElement) { document.exitFullscreen().catch(()=>{}); return; }
    const dialog=scope();
    if (dialog!==document) {
      const close=query('button[aria-label="Close"],button[aria-label="Fechar"],[data-testid="close-button"],button.close',dialog).find(e=>visibleBox(e));
      if(close)close.click();else notice('Selecione o botão de fechar da janela');
    } else if (document.fullscreenElement) document.exitFullscreen().catch(()=>{});
    else history.back();
  }
  function activate() {
    if (!current || !visibleBox(current)) move('ArrowDown');
    if (!current || !visibleBox(current)) return;
    if (current.matches('input,textarea,select,[contenteditable="true"]')) {editing=current;current.focus();notice('Digite com o teclado. Esc/B volta à navegação.');return;}
    current.click();log('activate');
  }
  const typing = () => (!!editing && editing===document.activeElement) || (document.activeElement !== current && document.activeElement?.matches('input,textarea,select,[contenteditable="true"],[role="slider"]'));
  function exportDiagnostic() {
    const data={version:'0.1.0',app:cfg.id,events,viewport:[innerWidth,innerHeight],pad:!![...(navigator.getGamepads?.()||[])].find(p=>p?.mapping==='standard')};
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download=`stream-tv-${cfg.id}-${Date.now()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function nativeKey(key) {
    const codes={ArrowUp:38,ArrowDown:40,ArrowLeft:37,ArrowRight:39,Enter:13,Escape:27};
    const target=document.activeElement||document.body;
    for(const type of ['keydown','keyup'])target.dispatchEvent(new KeyboardEvent(type,{key,code:key,keyCode:codes[key],which:codes[key],bubbles:true,cancelable:true}));
  }
  function action(key, source) {
    if (!enabled) return;
    if (nativeTV()) { if(source==='pad')nativeKey(key); return; }
    if (key==='Escape')back();
    else if (typing()) return;
    else if (key==='Enter')activate();
    else move(key);
  }
  window.addEventListener('keydown',e=>{
    if (!e.isTrusted) return;
    if (e.key==='F6') {e.preventDefault();if(e.shiftKey)exportDiagnostic();else{diagnostic=!diagnostic;notice(`Diagnóstico ${diagnostic?'ligado':'desligado'} • Shift+F6 salva`);}return;}
    if (e.key==='F7') {e.preventDefault();tv=!tv;root.dataset.stvVisual=tv?'1':'0';save();return;}
    if (e.key==='F8') {e.preventDefault();enabled=!enabled;cancel();query('[data-stv-focus]').forEach(n=>n.removeAttribute('data-stv-focus'));notice(`Adaptação ${enabled?'ligada':'desligada'}`);return;}
    if (e.key==='F9') {e.preventDefault();pad=!pad;save();notice(`Controle direto ${pad?'ligado':'desligado'}`);return;}
    if (!enabled || nativeTV() || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key==='Tab') {current=null;editing=null;cancel();return;}
    if (typing() && e.key!=='Escape') return;
    if (e.key!=='Escape' && cfg.id==='netflix' && location.pathname.startsWith('/watch/') && [...document.querySelectorAll('video')].some(v=>v.readyState>=2 && !v.error)) return;
    if (!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Escape'].includes(e.key)) return;
    if (e.key!=='Escape' && !candidates(true).length) return;
    e.preventDefault();e.stopImmediatePropagation();keyboardAt=performance.now();
    if (e.repeat && ['Enter','Escape'].includes(e.key)) return;
    action(e.key,'keyboard');
  },true);
  document.addEventListener('pointerdown',()=>{cancel();current=null;column=null;query('[data-stv-focus]').forEach(n=>n.removeAttribute('data-stv-focus'));},true);
  function poll(now) {
    if(location.pathname!==route){route=location.pathname;cancel();current=null;column=null;editing=null;}
    if(now>scopeCheck){
      scopeCheck=now+250;const nextScope=scope();
      if(enabled && current && nextScope!==observedScope && nextScope!==document){cancel();mark(candidates().find(e=>visibleBox(e)),true);}
      observedScope=nextScope;
    }
    if(!globalThis.AURA_NATIVE_CONTROLLER && pad && enabled && document.hasFocus() && !document.hidden && now-keyboardAt>150){
      const g=[...(navigator.getGamepads?.()||[])].find(p=>p?.connected && p.mapping==='standard');
      let key='';
      if(g){const b=i=>g.buttons[i]?.pressed;key=b(1)?'Escape':b(0)?'Enter':b(12)||g.axes[1]<-.65?'ArrowUp':b(13)||g.axes[1]>.65?'ArrowDown':b(14)||g.axes[0]<-.65?'ArrowLeft':b(15)||g.axes[0]>.65?'ArrowRight':'';}
      if(key && (key!==lastPad || (key.startsWith('Arrow') && now>=nextRepeat))){action(key,'pad');nextRepeat=now+(key===lastPad?170:380);}
      lastPad=key;
    } else lastPad='';
    requestAnimationFrame(poll);
  }
  root.dataset.stvVisual=tv?'1':'0';requestAnimationFrame(poll);
})();
