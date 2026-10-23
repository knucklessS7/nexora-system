(function init() {
  if (document.readyState==='loading') { document.addEventListener('DOMContentLoaded',init,{once:true}); return; }
  if (window.__auraChromeNav) { window.__auraChromeNavRefresh?.(); return; }
  const hosts=['primevideo.com','netflix.com','disneyplus.com','globo.com','spotify.com','apple.com','deezer.com','youtube.com'];
  if(!hosts.some(h=>location.hostname===h||location.hostname.endsWith('.'+h)))return;
  window.__auraChromeNav=true;
  // Aura 7.1.2: recover focus and highlight after player/catalog transitions.
  let pointerMode=false;
  let current=null, enabled=true, lastRoute=location.pathname+location.search;
  const remembered=new Map();
  const netflixHost=location.hostname==='netflix.com'||location.hostname.endsWith('.netflix.com');
  const netflixPlayer=()=>netflixHost&&/^\/watch(?:\/|$)/.test(location.pathname);
  const selector='a[href],button,input:not([type="hidden"]),textarea,select,[role="button"],[role="link"],[role="tab"],[tabindex],.title-card';
  const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>8&&r.height>8&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth&&s.display!=='none'&&s.visibility==='visible'&&!e.closest('[hidden],[inert],[aria-hidden="true"]')&&!e.matches(':disabled');};
  const scope=()=>[...document.querySelectorAll('[role="dialog"],[aria-modal="true"],dialog[open]')].filter(visible).at(-1)||document;
  // Include offscreen rows, but exclude hidden and horizontally clipped cards.
  const available=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>8&&r.height>8&&r.right>0&&r.left<innerWidth&&s.display!=='none'&&s.visibility==='visible'&&!e.closest('[hidden],[inert],[aria-hidden="true"]')&&!e.matches(':disabled');};
  const rowSelector='.carousel-row,.lolomoRow';
  const cardSelector='a[data-uia$="-card"],a:has(.tracked-card),.title-card a[href]';
  const cardRow=e=>e?.closest(rowSelector);
  function rowCards(row){return [...row.querySelectorAll(cardSelector)].filter(available);}
  let carouselPending=false;
  function moveRow(key){
    if(!netflixHost||scope()!==document)return false;
    const row=cardRow(current);if(!row)return false;
    const cards=rowCards(row);if(!cards.includes(current))return false;
    const sign=/Right|Down/.test(key)?1:-1;
    if(/Left|Right/.test(key)){
      const index=cards.indexOf(current),next=cards[index+sign];
      if(next){mark(next);return true;}
      if(carouselPending)return true;
      const pattern=sign>0?/mais t[ií]tulos|next|pr[oó]xim/i:/anteriores|previous/i;
      const arrow=[...row.querySelectorAll('button,[role="button"]')].find(e=>visible(e)&&!e.disabled&&pattern.test(e.getAttribute('aria-label')||''));
      if(arrow){
        const old=current;carouselPending=true;arrow.click();
        setTimeout(()=>{carouselPending=false;if(!row.isConnected||cardRow(current)!==row)return;
          const updated=rowCards(row),i=updated.indexOf(old);
          const target=i>=0?updated[i+sign]:sign>0?updated[0]:updated.at(-1);
          if(target)mark(target);
        },450);
      }
      return true;
    }
    const rows=[...document.querySelectorAll(rowSelector)],i=rows.indexOf(row);
    const rect=current.getBoundingClientRect(),x=rect.left+rect.width/2;
    for(let j=i+sign;j>=0&&j<rows.length;j+=sign){
      const targets=rowCards(rows[j]);
      if(targets.length){targets.sort((a,b)=>{const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();return Math.abs(ra.left+ra.width/2-x)-Math.abs(rb.left+rb.width/2-x);});mark(targets[0]);return true;}
    }
    // At the bottom keep the selected card; Up from the first row may reach the hero.
    return sign>0;
  }
  function items(){
    const found=[...scope().querySelectorAll(selector)].filter(e=>available(e)&&!e.closest('#aura-help,#aura-control-bar'));
    if(netflixHost&&scope()===document){return found.filter(e=>!cardRow(e)||e.matches(cardSelector));}
    const cards=new Set();
    return found.filter(e=>{
      const card=e.closest('.title-card');
      if(!card)return true;
      if(cards.has(card))return false;
      const target=[...card.querySelectorAll('a[href],button,[role="button"]')].find(available)||card;
      if(e!==target)return false;
      cards.add(card);return true;
    });
  }
  function mark(e){
    if(!e)return;
    document.querySelectorAll('[data-aura-focus]').forEach(n=>n.removeAttribute('data-aura-focus'));
    current=e;e.setAttribute('data-aura-focus','');e.focus({preventScroll:true});
    const r=e.getBoundingClientRect();
    if(r.top<90||r.bottom>innerHeight-85)e.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});
    // Synthetic hover expands Netflix cards and changes the navigation geometry.
  }
  function move(key){
    if(moveRow(key))return true;
    const list=items();if(!list.length)return false;
    if(!list.includes(current)){mark(list.find(visible)||list[0]);return true;}
    const r=current.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
    const horizontal=/Left|Right/.test(key),sign=/Right|Down/.test(key)?1:-1;
    const ranked=list.filter(e=>e!==current&&!e.contains(current)&&!current.contains(e)).map(e=>{
      const b=e.getBoundingClientRect(),dx=b.x+b.width/2-x,dy=b.y+b.height/2-y;
      const overlap=Math.min(r.bottom,b.bottom)-Math.max(r.top,b.top);
      return {e,main:(horizontal?dx:dy)*sign,cross:Math.abs(horizontal?dy:dx),sameRow:overlap>Math.min(r.height,b.height)*.4};
    }).filter(p=>p.main>8&&(horizontal?p.sameRow:!p.sameRow))
      .sort((a,b)=>(a.main+a.cross*(horizontal?3:.15))-(b.main+b.cross*(horizontal?3:.15)));
    if(ranked.length)mark(ranked[0].e);
    else if(!horizontal)window.scrollBy({top:sign*innerHeight*.55,left:0,behavior:'instant'});
    return true;
  }
  function back(){const active=document.activeElement;if(active?.matches('input,textarea,[contenteditable="true"]')){active.blur();return;}
    if(document.fullscreenElement){document.exitFullscreen().catch(()=>{});return;}
    const close=[...scope().querySelectorAll('button,[role="button"]')].find(e=>visible(e)&&/^(close|fechar|voltar|back|sair)(\b|$)/i.test(e.getAttribute('aria-label')||e.title||e.textContent.trim()));
    if(close)close.click();else if(history.length>1)history.back();}
  function help(){let h=document.getElementById('aura-help');if(h){h.remove();return;}h=document.createElement('div');h.id='aura-help';h.textContent='AURA  |  CONTROLES\n\nNAVEGAR\nSetas / direcional: navegar   •   Enter / A: confirmar\nEsc / B: voltar   •   Tab: próximo\n\nREPRODUÇÃO E PONTEIRO\nY: alternar ponteiro   •   A: clicar   •   X: pausar\n\nATALHOS\nF8: ligar/desligar navegação AURA\nSelect + Start / Alt + F4: sair do streaming\nF1 / Esc: fechar esta ajuda';h.style.cssText='position:fixed;inset:20px 5% auto;z-index:2147483647;background:#101b30;color:white;padding:24px;border:3px solid #53dcff;font:22px sans-serif';document.documentElement.append(h);}
  function refresh() {
    const route=location.pathname+location.search;
    if(route!==lastRoute || (current&&!current.isConnected)) {
      if(current)remembered.set(lastRoute,{node:current,href:current.getAttribute('href')});
      current?.removeAttribute('data-aura-focus'); current=null; lastRoute=route;
      document.querySelectorAll('[data-aura-focus]').forEach(e=>e.removeAttribute('data-aura-focus'));
      const saved=remembered.get(route);
      if(saved){const list=items();const restored=list.includes(saved.node)?saved.node:list.find(e=>saved.href&&e.getAttribute('href')===saved.href);if(restored)mark(restored);}
    }
    document.getElementById('aura-control-bar')?.remove();
    if(!document.getElementById('aura-navigation-style')) {
      const style=document.createElement('style');style.id='aura-navigation-style';
      style.textContent=`
        /* AURA TV layout v1: hide scrollbars, never disable scrolling. */
        html,body,*{scrollbar-width:none!important}
        *::-webkit-scrollbar{display:none!important;width:0!important;height:0!important}
        [data-aura-focus]{outline:3px solid #53dcff!important;outline-offset:3px!important;box-shadow:0 0 0 6px #071725!important}
        :fullscreen [data-aura-focus]{outline:none!important;box-shadow:none!important}
        #aura-help{box-sizing:border-box!important;inset:5vh 5vw auto!important;max-height:85vh;overflow:auto;
          padding:clamp(18px,3vw,36px)!important;border:1px solid #53dcff!important;border-radius:16px;
          background:#081525!important;color:#eef8ff!important;box-shadow:0 8px 32px #000a;
          font:clamp(16px,2.2vw,24px)/1.6 sans-serif!important;white-space:pre-line}
      `;
      (document.head||document.documentElement).append(style);
    }
  }
  let lastCalibration='';
  window.__auraCalibrationStatus=message=>{
    if(message===lastCalibration)return;lastCalibration=message;
    document.getElementById('aura-calibration')?.remove();
    if(!message)return;
    const panel=document.createElement('div');panel.id='aura-calibration';panel.textContent=message;
    panel.style.cssText='position:fixed;inset:25% 10% auto;z-index:2147483647;background:#102237;color:white;border:4px solid #53dcff;padding:40px;font:30px sans-serif;pointer-events:none';
    document.documentElement.append(panel);
    if(message.startsWith('Controle salvo.'))setTimeout(()=>panel.remove(),5000);
  };
  window.__auraChromeNavRefresh=refresh;
  window.addEventListener('popstate',refresh);
  window.addEventListener('pageshow',refresh);
  refresh();
  window.addEventListener('keydown',e=>{
    if(!e.isTrusted||e.ctrlKey||e.altKey||e.metaKey)return;
    refresh();
    if(e.key==='F2'){e.preventDefault();if(!e.repeat){pointerMode=!pointerMode;refresh();}return;}
    if(e.key==='F1'){e.preventDefault();if(!e.repeat)help();return;}
    if(e.key==='F8'){e.preventDefault();if(!e.repeat)enabled=!enabled;return;}
    if(!enabled)return;
    if(e.key==='Tab'){current=null;return;}
    // The TV app has its own focus engine. Pass arrows, Enter, Escape and pause through.
    if((location.hostname==='www.youtube.com'||location.hostname==='youtube.com')&&/^\/tv(?:\/|$)/.test(location.pathname))return;
    const editing=document.activeElement?.matches('input,textarea,select,[contenteditable="true"]')&&visible(document.activeElement);
    if(editing&&e.key!=='Escape')return;
    // Leave player keys native even while its video is loading or removed.
    if(netflixPlayer()&&e.key!=='Escape')return;
    // Aura 7.1.1: Netflix catalog previews must not disable navigation.
    const playing=[...document.querySelectorAll('video')].some(v=>visible(v)&&v.readyState>=2&&!v.error);
    const netflixCatalog=netflixHost&&!/^\/watch(?:\/|$)/.test(location.pathname);
    // The real Netflix player and other services keep their native video keys.
    if(playing&&!netflixCatalog&&e.key!=='Escape')return;
    if(e.key===' '){e.preventDefault();e.stopImmediatePropagation();return;}
    let handled=false;
    if(e.key.startsWith('Arrow'))handled=move(e.key);
    else if(e.key==='Enter'){const list=items();const el=list.includes(current)?current:list[0];if(el){handled=true;if(!e.repeat){mark(el);el.click();}}}
    else if(e.key==='Escape'){handled=true;if(!e.repeat){if(document.getElementById('aura-help'))help();else back();}}
    if(handled){e.preventDefault();e.stopImmediatePropagation();}
  },true);
  document.addEventListener('pointerdown',()=>{current?.removeAttribute('data-aura-focus');current=null;},true);
  document.addEventListener('focusin',e=>{if(e.target.matches?.(selector)&&visible(e.target))current=e.target;},true);
})();
