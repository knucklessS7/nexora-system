(() => {
  'use strict';
  if (window.__ptv104) return;
  window.__ptv104 = true;
  const ALL = 'a[href],button,input:not([type="hidden"]),textarea,select,[role="button"],[role="link"],[role="tab"],[role="menuitem"],[role="option"],[tabindex]';
  const ROW = '[data-testid="standard-carousel"],[data-testid="card-container-list"],[data-testid="station-carousel"],[aria-roledescription="carousel"],ul,ol,[role="list"]';
  const HERO = '[data-testid="top-hero-card"],[data-testid*="hero"],[class*="Hero"],[class*="hero"]';
  const NAV = 'header,nav,[role="navigation"]';
  const $ = (s, root = document) => [...root.querySelectorAll(s)];
  const rect = el => el.getBoundingClientRect();
  let current = null, saved = null, enabled = true, busy = false;
  let route = location.origin + location.pathname, epoch = 0, lastMove = 0;
  let keyboardAt = -1000, pointerUntil = 0, padEnabled = true;
  let padAction = '', repeatAt = 0, padSignature = '';
  let columnX = null;
  let pendingDirection = null, advanceId = 0;
  const memory = new Map();
  try { padEnabled = localStorage.getItem('ptv-pad') !== '0'; } catch (_) {}
  // Diagnostic module: observes navigation without correcting or moving focus.
  const diagnostics = (() => {
    const buffer = [], MAX = 640;
    const nodeIds = new WeakMap(); let nextNode = 0;
    function nodeId(el) { if (!el) return null; if (!nodeIds.has(el)) nodeIds.set(el,++nextNode); return nodeIds.get(el); }
    let enabled = false, panel = null, timer = null, lastState = '';
    let tv = true, showCss = true, sequence = 0;
    try { tv = localStorage.getItem('ptv-tv-style') !== '0'; } catch (_) {}
    const rounded = n => Math.round(n || 0);
    function describe(el) {
      if (!el || el === document.body || el === document.documentElement) return null;
      const r = el.getBoundingClientRect(), style = getComputedStyle(el);
      const region = el.closest(NAV) ? 'menu' : el.closest(HERO) ? 'destaque' : el.closest(ROW) ? 'fileira' : 'outro';
      return {
        node:nodeId(el), group:nodeId(source(el)), sourceTag:source(el)?.tagName?.toLowerCase(), sourceTestid:source(el)?.getAttribute?.('data-testid') || '',
        tag: el.tagName.toLowerCase(), testid: (el.getAttribute('data-testid') || '').slice(0,100),
        role: el.getAttribute('role') || '', region,
        box: [r.x,r.y,r.width,r.height].map(rounded),
        outline: style.outlineStyle + ' ' + style.outlineWidth,
        boxShadow: style.boxShadow, connected: el.isConnected,
        hidden: !!el.closest('[hidden],[aria-hidden="true"],[inert]'),
        // No link URLs, visible text, input values, profile names or authentication data.
        path: domPath(el)
      };
    }
    function domPath(el) {
      const parts = [];
      for (let p = el; p && p !== document.body && parts.length < 6; p = p.parentElement) {
        const siblings = p.parentElement ? [...p.parentElement.children].filter(e => e.tagName === p.tagName) : [];
        parts.unshift(p.tagName.toLowerCase() + ':nth-of-type(' + (siblings.indexOf(p)+1) + ')');
      }
      return parts.join('>');
    }
    function sample() {
      const marks = $('[data-ptv-focus="1"]');
      return {
        active: describe(document.activeElement), selected: describe(current),
        markers: marks.slice(0,8).map(describe), markerCount: marks.length,
        mismatch: !!current?.isConnected && current !== document.activeElement,
        scroll: [rounded(scrollX), rounded(scrollY)],
        viewport: [innerWidth,innerHeight], declaredVersion: document.documentElement.dataset.ptvVersion || '',
        tvStyle: tv, nativeMode: document.documentElement.dataset.ptvNative,
        player: player(), editing: editing(), busy, pendingDirection, columnX,
        pads: pads().map(p => ({index:p.index, mapping:p.mapping, buttons:p.buttons.length, axes:p.axes.length}))
      };
    }
    function record(type, detail = {}) {
      if (!enabled) return;
      try {
        const entry = {n:++sequence, ms:rounded(performance.now()), type, ...detail, state:sample()};
        buffer.push(entry); if (buffer.length > MAX) buffer.shift();
        render(entry.state);
      } catch (_) { /* Diagnostics must never stop navigation. */ }
    }
    function short(el) {
      return el ? `${el.region}: ${el.tag}${el.testid ? '['+el.testid+']' : ''} (${el.box.join(',')})` : 'nenhum';
    }
    function render(state) {
      if (!panel?.isConnected) return;
      const recent = buffer.filter(e => /key|gamepad|move|route/.test(e.type)).slice(-5).map(e =>
        '#' + e.n + ' ' + e.type + ' ' + (e.key || e.direction || e.action || '')).join('\n');
      panel.textContent = 'PRIME TV 10.4 · DIAGNÓSTICO\n' +
        'F6 fechar · Shift+F6 salvar · F7 visual · F4 Veja mais\n' +
        `Foco diferente: ${state.mismatch ? 'SIM' : 'não'} · marcadores: ${state.markerCount}\n` +
        'Selecionado: ' + short(state.selected) + '\n' +
        'Navegador: ' + short(state.active) + '\n' +
        `Rolagem: ${state.scroll[1]} · visual TV: ${tv ? 'ligado' : 'desligado'}\n` +
        `Controle: ${state.pads.length ? state.pads.map(p=>p.mapping||'sem padrão').join(', ') : 'não detectado'} · registros: ${buffer.length}\n` + recent;
    }
    function toggle() {
      enabled = !enabled;
      if (enabled) {
        panel = document.createElement('pre'); panel.id = 'ptv104-diagnostics';
        panel.dataset.ptvUi = '1'; panel.setAttribute('aria-hidden','true');
        document.documentElement.append(panel);
        record('diagnostic-enabled');
        timer = setInterval(() => {
          const s = sample(), signature = JSON.stringify(s);
          if (signature !== lastState) { lastState = signature; record('state-change'); }
        }, 180);
      } else { clearInterval(timer); timer = null; panel?.remove(); panel = null; }
      return enabled;
    }
    function download() {
      if (!buffer.length) { status('Ative F6, reproduza o problema e depois pressione Shift+F6.'); return; }
      record('export');
      const payload = {format:'prime-tv-focus-v1', version:'10.4', navigationBase:'10',
        notes:'No page text, typed values, URLs, account or login data collected. Focus mismatch does not by itself prove duplicate extensions.',
        events:buffer};
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
      const link = document.createElement('a'); link.href = url;
      link.download = 'prime-tv-diagnostico-' + Date.now() + '.json';
      link.dataset.ptvUi = '1'; link.hidden = true; document.body.append(link); link.click(); link.remove();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
      status('Relatório solicitado. Confira a pasta Downloads do Chromium.');
    }
    function applyStyle() {
      document.documentElement.dataset.ptvTv = tv && showCss && !player() ? '1' : '0';
    }
    function toggleStyle() {
      tv = !tv;
      try { localStorage.setItem('ptv-tv-style',tv?'1':'0'); } catch (_) {}
      applyStyle(); record('tv-style',{on:tv});
      status('Visual de TV: ' + (tv?'ligado':'desligado') + ' · navegação baseada na v10');
    }
    document.addEventListener('focusin', () => record('focusin'), true);
    // Log the release separately, without consuming it or changing v10 behavior.
    window.addEventListener('keyup', e => {
      if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Escape','Tab'].includes(e.key)) {
        record('keyup',{key:e.key}); setTimeout(()=>record('after-keyup',{key:e.key}),60);
      }
    },true);
    applyStyle();
    setInterval(applyStyle,500);
    return {record,toggle,download,toggleStyle,
      candidates(list){
        if (!enabled) return;
        const y = current?.isConnected ? current.getBoundingClientRect().top : 0;
        const nearby = [...list].sort((a,b)=>Math.abs(a.getBoundingClientRect().top-y)-Math.abs(b.getBoundingClientRect().top-y));
        record('candidates',{total:list.length,nearby:nearby.slice(0,18).map(describe)});
      },
      setNative(on){showCss=on;applyStyle();}
    };
  })();


  function rendered(el) {
    if (!el?.isConnected || el.disabled || el.closest('[hidden],[inert],[aria-hidden="true"],[aria-disabled="true"],[data-ptv-ui],#ptv104-status')) return false;
    const r = rect(el);
    if (r.width < 8 || r.height < 8) return false;
    for (let p = el; p; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.display === 'none' || s.visibility !== 'visible' || Number(s.opacity) < .02) return false;
    }
    return true;
  }
  function visible(el) {
    if (!rendered(el)) return false;
    const r = rect(el);
    let l = Math.max(0, r.left), right = Math.min(innerWidth, r.right), t = r.top, b = r.bottom;
    for (let p = el.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
      const s = getComputedStyle(p), a = rect(p);
      if (/hidden|clip|auto|scroll/.test(s.overflowX)) { l = Math.max(l, a.left); right = Math.min(right, a.right); }
      if (/hidden|clip|auto|scroll/.test(s.overflowY)) { t = Math.max(t, a.top); b = Math.min(b, a.bottom); }
    }
    if (right - l < Math.min(r.width * .65, innerWidth * .65) || b - t < Math.min(r.height * .55, 24)) return false;
    // Below/above the viewport is allowed: those rows can be reached by scrolling.
    if (t >= 0 && b <= innerHeight) {
      const hit = document.elementFromPoint((l + right) / 2, (t + b) / 2);
      if (hit && !el.contains(hit) && !hit.contains(el) && !(more(el) && hit.closest(NAV))) return false;
    }
    return true;
  }
  function scope() {
    return $('[role="dialog"],[aria-modal="true"],dialog[open],[role="menu"]')
      .filter(visible).at(-1) || document;
  }
  function editing() {
    return !!document.activeElement?.closest('input,textarea,select,[contenteditable]:not([contenteditable="false"])');
  }
  function player() {
    if (/\/(player|watch)(\/|$)/i.test(location.pathname)) return true;
    if (document.fullscreenElement?.querySelector('video') || document.fullscreenElement?.matches('video')) return true;
    // Banner trailers must not disable navigation. Recognize an actual player UI.
    return $('video').some(v => rendered(v) && !v.closest(HERO) &&
      v.closest('#dv-web-player,.webPlayerUIContainer,[data-testid="web-player"]'));
  }
  function label(el) {
    return [el.getAttribute('aria-label'), el.getAttribute('title'), el.getAttribute('data-testid'), el.textContent].filter(Boolean).join(' ').trim();
  }
  function arrow(el) {
    if (!el.matches('button,[role="button"]')) return '';
    const id = el.getAttribute('data-testid');
    if (id === 'right-arrow') return 'right';
    if (id === 'left-arrow') return 'left';
    const text = label(el);
    if (/next|pr[oó]xim|avan[çc]|direita/i.test(text)) return 'right';
    if (/previous|prev\b|anterior|esquerda/i.test(text)) return 'left';
    return '';
  }
  function heroRoot(el) {
    return el.closest('[data-testid="top-hero-card"]') || el.closest(HERO);
  }
  function more(el) { return el.matches('[data-testid="see-more"]'); }
  function listForMore(el) {
    for (let p=el.parentElement;p && p!==document.body && p.tagName!=='MAIN';p=p.parentElement) {
      const lists=$('ul,ol,[role="list"]',p).filter(l=>!l.closest(NAV)&&!heroRoot(l));
      if (lists.length===1) return lists[0];
      if (lists.length>1) return null;
    }
    return null;
  }
  function source(el) {
    return el.closest(NAV) || heroRoot(el) || (more(el) && listForMore(el)) || el.closest(ROW) || el.closest('section') || document.body;
  }
  function items() {
    const root = scope(), out = [], cards = new Set();
    for (const el of $(ALL, root)) {
      if (!visible(el)) continue;
      if (el.matches('[tabindex="-1"]') && !el.matches('a[href],button,input,textarea,select,[role]')) continue;
      const parent = el.parentElement?.closest('a[href],button,[role="button"],[role="link"]');
      if (parent && root.contains(parent)) continue;
      // These controls change carousel pages, not the selected title. They are
      // clicked by advance() at a horizontal edge, never vertical destinations.
      if (arrow(el)) continue;
      if (el.closest(NAV) && /logo|pv-nav-branding/i.test((el.getAttribute('data-testid') || '') + ' ' + el.className)) continue;
      const card = el.closest('[data-testid="card"],[data-testid="genre-card"],[data-testid="episode-list-item"],li');
      // A hero slide is also an LI. Treating it as a movie card was discarding
      // all its action buttons and retaining only its full-screen image link.
      if (card && !heroRoot(el) && !el.closest(NAV) && !el.closest('[role="menu"],[role="dialog"],[aria-modal="true"]')) {
        const primary = $('a[href]', card).find(visible) || $('button,[role="button"]', card).find(visible);
        if (primary && el !== primary) continue;
        if (cards.has(card)) continue;
        cards.add(card);
      }
      out.push(el);
    }
    return out.filter(el=>{
      if (!el.matches('[data-testid="image-link"]') || !heroRoot(el)) return true;
      const hero=heroRoot(el);
      // Keep the image as a fallback if the site supplies no visible action.
      return !out.some(other=>other!==el && heroRoot(other)===hero &&
        !other.matches('[data-testid="image-link"]') && !arrow(other));
    });
  }
  function groups(list) {
    const rows = [];
    for (const el of list.filter(e=>!more(e))) {
      const r = rect(el), src = source(el), y = r.top + scrollY, cy = y + r.height / 2;
      const nav = !!el.closest(NAV), hero = !!el.closest(HERO);
      let g = rows.find(g => g.src === src && (nav || hero || Math.abs(g.cy - cy) <= Math.min(g.height, r.height) * .5));
      if (!g) { g = { src, cy, top: y, height: r.height, nav, hero, items: [] }; rows.push(g); }
      g.items.push(el);
      g.top = Math.min(g.top, y);
    }
    rows.sort((a, b) => a.nav !== b.nav ? (a.nav ? -1 : 1) : a.top - b.top);
    for (const row of rows) row.items.sort((a, b) => rect(a).left - rect(b).left);
    for (const el of list.filter(more)) {
      const row=rows.find(g=>g.src===source(el));
      if (row) row.items.push(el); // Reach Veja mais via Right after the last visible card.
      else {
        const r=rect(el),src=source(el);
        rows.push({src,cy:r.top+scrollY+r.height/2,top:r.top+scrollY,height:r.height,nav:false,hero:false,items:[el]});
      }
    }
    rows.sort((a,b)=>a.nav!==b.nav?(a.nav?-1:1):a.top-b.top);
    return rows;
  }
  function clear() { $('[data-ptv-focus]').forEach(el => el.removeAttribute('data-ptv-focus')); }
  function snapshot(el) {
    const r = rect(el);
    return { href: el.getAttribute('href'), label: label(el), src: source(el), x: r.left + r.width / 2, y: r.top + scrollY + r.height / 2 };
  }
  function reveal(el) {
    if (el.closest(NAV)) return; // A fixed header must never scroll the document.
    const r = rect(el);
    const header = $(NAV).filter(rendered).map(rect).filter(r => r.top <= 5 && r.bottom < innerHeight / 3);
    const top = Math.max(24, ...header.map(r => r.bottom + 24)), bottom = innerHeight - 36;
    if (r.top < top || r.bottom > bottom) {
      // Exactly one synchronous scroll: no delayed recenter fighting the next key.
      const delta = r.height > bottom - top ? r.top - top : r.top < top ? r.top - top : r.bottom - bottom;
      window.scrollBy({ top: delta, behavior: 'instant' });
    }
  }
  function focus(el, scroll = true) {
    if (!el || !rendered(el)) return false;
    diagnostics.record('select-request',{target:el.tagName});
    current = el; saved = snapshot(el); memory.set(saved.src, saved);
    clear(); el.setAttribute('data-ptv-focus', '1');
    if (!el.matches('a[href],button,input,textarea,select,[tabindex]')) el.tabIndex = -1;
    el.focus({ preventScroll: true });
    if (scroll) reveal(el);
    diagnostics.record('selected');
    return true;
  }
  function recover(list) {
    if (current?.isConnected && list.includes(current)) return current;
    if (saved) {
      const same = list.filter(e => source(e) === saved.src);
      const exact = same.find(e => saved.href ? e.getAttribute('href') === saved.href : label(e) === saved.label);
      if (exact) return exact;
      const pool = same.length ? same : list.filter(e => !e.closest(NAV));
      return pool.sort((a, b) => {
        const distance = e => { const s = snapshot(e); return Math.abs(s.y - saved.y) * 4 + Math.abs(s.x - saved.x); };
        return distance(a) - distance(b);
      })[0] || list[0];
    }
    const active = document.activeElement;
    return list.includes(active) ? active : list.find(e => e.matches('[aria-current="page"],[aria-selected="true"]')) ||
      list.find(e => { const r = rect(e); return r.top >= 0 && r.bottom <= innerHeight; }) || list[0];
  }
  function choose(row, x) {
    const old = memory.get(row.src);
    const remembered = old && row.items.find(e => old.href ? e.getAttribute('href') === old.href : label(e) === old.label);
    if (row.nav) {
      const active=row.items.find(e=>e.matches('[aria-current="page"],[aria-selected="true"]'));
      if (active || remembered) return active || remembered;
    }
    const primary=row.items.filter(e=>!more(e));
    const options=primary.length?primary:row.items;
    return options.reduce((a,b)=>Math.abs(snapshot(a).x-x)<=Math.abs(snapshot(b).x-x)?a:b);
  }
  function cancelAdvance(reason) {
    advanceId++; pendingDirection=null; busy=false;
    diagnostics.record('carousel-cancelled',{reason});
  }
  function advance(row, dir) {
    let host = row.src.closest('[data-testid="standard-carousel"],[aria-roledescription="carousel"]') || row.src;
    // The captured Prime markup also has sibling arrows in ordinary SECTIONs.
    if (!host.querySelector('[data-testid="right-arrow"],[data-testid="left-arrow"]')) {
      for(let p=row.src.parentElement;p&&p!==document.body&&p.tagName!=='MAIN';p=p.parentElement){
        if ($('[data-testid="right-arrow"],[data-testid="left-arrow"]',p).length && $('ul,ol,[role="list"]',p).length===1){host=p;break;}
        if ($('ul,ol,[role="list"]',p).length>1)break;
      }
    }
    const button = $('button,[role="button"]', host).find(e => rendered(e) && arrow(e) === dir);
    const scroller = [row.src, ...$('*', host)].find(e => e.scrollWidth > e.clientWidth + 20 && /auto|scroll/.test(getComputedStyle(e).overflowX));
    if (!button && !scroller) return;
    const oldItems = new Map(row.items.map(e=>[e,e.getAttribute('href')]));
    const token = epoch, id=++advanceId, root=scope(), start=performance.now();
    const geometry=()=>$('a[href],button,[role="button"]',row.src).slice(0,100).map(e=>{
      const r=rect(e);return [e,Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)];
    });
    const equal=(a,b)=>a.length===b.length && a.every((r,i)=>r.every((v,j)=>v===b[i][j]));
    let lastGeometry=geometry(), stableSince=start, moved=false;
    busy = true; pendingDirection=null;
    diagnostics.record('carousel-start',{direction:dir});
    if (button) button.click();
    else scroller.scrollBy({ left: (dir === 'right' ? 1 : -1) * scroller.clientWidth * .8, behavior: 'instant' });
    // Native Prime carousels keep moving after the old fixed 280ms deadline.
    // Require measured geometry to settle before selecting a card or releasing input.
    function finish() {
      if (id!==advanceId) return;
      if (token!==epoch || !enabled || !row.src.isConnected || scope()!==root || player() || editing()) {
        cancelAdvance('context-changed');return;
      }
      const now=performance.now(), elapsed=now-start, currentGeometry=geometry();
      if (!equal(currentGeometry,lastGeometry)) { moved=true;stableSince=now;lastGeometry=currentGeometry; }
      const settled=now-stableSince>=200 && (moved || elapsed>=900);
      if (!settled && elapsed<2600) { setTimeout(finish,65);return; }
      const candidates = groups(items()).filter(g => g.src === row.src).flatMap(g => g.items).filter(e=>!more(e));
      const fresh = candidates.filter(e => !oldItems.has(e) || oldItems.get(e)!==e.getAttribute('href'));
      const target=fresh.length ? (dir==='right'?fresh[0]:fresh.at(-1)) :
        candidates.includes(current)?current:candidates.length?choose({src:row.src,items:candidates},saved?.x||0):null;
      if (target) {focus(target);columnX=snapshot(target).x;}
      busy=false;
      diagnostics.record(settled?'carousel-settled':'carousel-timeout',{direction:dir,elapsed:Math.round(elapsed)});
      const pending=pendingDirection;pendingDirection=null;
      if (pending) requestAnimationFrame(()=>{
        if(id===advanceId && token===epoch && enabled && !player() && !editing() && scope()===root)move(pending);
      });
    }
    setTimeout(finish, 65);
  }
  function move(dir) {
    diagnostics.record('move',{direction:dir});
    if (busy) {pendingDirection=dir;diagnostics.record('direction-queued',{direction:dir});return true;}
    const list = items();
    diagnostics.candidates(list);
    if (!list.length) return true;
    const from = recover(list);
    if (!current || !list.includes(current)) { focus(from); return true; }
    const rows = groups(list), index = rows.findIndex(g => g.items.includes(from));
    if (index < 0) return true;
    const row = rows[index], primary=row.items.filter(e=>!more(e));
    const horizontal=primary.length?primary:row.items, i=horizontal.indexOf(from);
    if (dir === 'left' || dir === 'right') {
      const target = i<0 ? (dir==='right'?horizontal[0]:horizontal.at(-1)) : horizontal[i + (dir === 'right' ? 1 : -1)];
      if (target) { focus(target); columnX = snapshot(target).x; }
      else if (!row.nav && !row.hero) advance(row, dir);
    } else {
      const next = rows[index + (dir === 'down' ? 1 : -1)];
      if (columnX===null) columnX=snapshot(from).x;
      if (next) focus(choose(next, columnX));
      // At the edge retain focus; never scroll with no known destination.
    }
    return true;
  }
  function activate() {
    if (busy) return;
    const el = recover(items());
    if (el && visible(el)) { focus(el, false); el.click(); }
  }
  function back() {
    cancelAdvance('back');
    if (editing()) { document.activeElement?.blur(); return; }
    if (document.fullscreenElement) { document.exitFullscreen().catch(()=>{}); return; }
    const dialog = scope();
    const container = dialog !== document ? dialog : (player() ? document : null);
    if (container) {
      const close = [...container.querySelectorAll('button,[role="button"],a[aria-label]')].find(el =>
        visible(el) && /^(close|fechar|voltar|back|sair|exit)(\b|$)/i.test(el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent.trim()));
      if (close) { close.click(); return; }
      if (dialog !== document) { status('Selecione o botão Fechar desta janela.'); return; }
    }
    if (history.length > 1) history.back();
    else status('Você está na tela inicial. Select + Start fecha o aplicativo.');
  }
  function openMore() {
    if (busy) return;
    const list=items(), from=recover(list);
    const row=groups(list).find(g=>g.items.includes(from));
    const link=row?.items.find(more);
    if (link) {focus(link,false);link.click();}
    else status('Esta fileira não tem o botão Veja mais.');
  }
  function status(text) {
    document.getElementById('ptv104-status')?.remove();
    const box = document.createElement('div');
    box.id = 'ptv104-status'; box.setAttribute('role', 'status'); box.textContent = text;
    document.documentElement.appendChild(box);
    setTimeout(() => box.remove(), 6500);
  }
  function pads() { try { return Array.from(navigator.getGamepads?.() || []).filter(Boolean); } catch (_) { return []; } }
  window.addEventListener('keydown', e => {
    if (!e.isTrusted) return;
    if (e.key === 'F6') {
      e.preventDefault(); e.stopImmediatePropagation();
      if (!e.repeat) { if (e.shiftKey) diagnostics.download(); else diagnostics.toggle(); }
      return;
    }
    if (e.key === 'F7') {
      e.preventDefault(); e.stopImmediatePropagation();
      if (!e.repeat) diagnostics.toggleStyle();
      return;
    }
    if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Escape','Tab'].includes(e.key)) {
      diagnostics.record('keydown',{key:e.key,repeat:e.repeat});
      setTimeout(()=>diagnostics.record('after-keydown',{key:e.key}),60);
    }
    if (e.key === 'F8') {
      enabled = !enabled; epoch++; cancelAdvance('mode-toggle'); diagnostics.setNative(enabled);
      document.documentElement.dataset.ptvNative = enabled ? '1' : '0';
      if (!enabled) clear();
      status('Prime TV 10.4: ' + (enabled ? 'ligado' : 'desligado')); e.preventDefault(); return;
    }
    if (e.key === 'F9') {
      padEnabled = !padEnabled;
      try { localStorage.setItem('ptv-pad', padEnabled ? '1' : '0'); } catch (_) {}
      status('Controle direto: ' + (padEnabled ? 'ligado' : 'desligado')); e.preventDefault(); return;
    }
    if (e.key === 'F10') {
      const p = pads();
      status('Prime TV 10.4 · ' + (p.length ? p.map(p => p.id + ' [' + (p.mapping || 'sem mapeamento padrão') + ']').join(' · ') : 'Nenhum controle exposto pelo Chromium. Pressione A no controle e tente novamente.'));
      e.preventDefault(); return;
    }
    if (enabled && e.key === 'Escape' && !e.altKey && !e.ctrlKey && !e.metaKey) {
      e.preventDefault(); e.stopImmediatePropagation();
      if (!e.repeat) back();
      return;
    }
    if (!enabled || player() || editing() || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key==='F4') {
      e.preventDefault();e.stopImmediatePropagation();
      if(!e.repeat)openMore();return;
    }
    if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)) {
      e.preventDefault(); e.stopImmediatePropagation(); keyboardAt = performance.now();
      if (e.repeat && keyboardAt - lastMove < 150) return;
      lastMove = keyboardAt; move(e.key.slice(5).toLowerCase());
    } else if (e.key === 'Enter') {
      e.preventDefault(); e.stopImmediatePropagation(); keyboardAt = performance.now();
      if (!e.repeat) activate();
    } else if (e.key === 'Tab') { cancelAdvance('tab');current = null; saved = null;columnX=null; clear(); }
  }, true);
  document.addEventListener('pointerdown', e => {
    if (!enabled) return;
    if (busy)cancelAdvance('pointer');
    pointerUntil = performance.now() + 500;
    columnX = null;
    const el = e.target.closest(ALL);
    if (el && visible(el)) focus(el, false);
  }, true);
  document.addEventListener('focusin', e => {
    if (!enabled || player() || editing()) return;
    // Automatic focus changes from the SPA do not reset the TV cursor to its header.
    if ((!current || performance.now() < pointerUntil) && e.target.matches?.(ALL) && visible(e.target)) {
      current = e.target; saved = snapshot(current); clear(); current.dataset.ptvFocus = '1';
    }
  }, true);
  function poll(now) {
    requestAnimationFrame(poll);
    if (globalThis.AURA_NATIVE_CONTROLLER || !enabled || !padEnabled || document.hidden || !document.hasFocus()) { padAction = ''; return; }
    const pad = pads().find(p => p.mapping === 'standard');
    if (!pad) { padAction = ''; return; }
    const signature = pad.index + ':' + pad.id;
    if (signature !== padSignature) { padSignature = signature; padAction = ''; }
    const b = i => pad.buttons[i]?.pressed, x = pad.axes[0] || 0, y = pad.axes[1] || 0;
    const action = b(12) ? 'up' : b(13) ? 'down' : b(14) ? 'left' : b(15) ? 'right' :
      Math.max(Math.abs(x),Math.abs(y)) > .65 ? (Math.abs(x) > Math.abs(y) ? (x < 0 ? 'left' : 'right') : (y < 0 ? 'up' : 'down')) :
      b(0) ? 'ok' : b(1) ? 'back' : b(2) ? 'more' : '';
    if (!action) { padAction = ''; return; }
    if ((player() || editing()) && action !== 'back') { padAction = ''; return; }
    const first = action !== padAction;
    if (first || now >= repeatAt) {
      padAction = action; repeatAt = now + (first ? 380 : 160);
      diagnostics.record('gamepad',{action});
      if (now - keyboardAt < 600) return;
      if (action === 'ok') { if (first) activate(); }
      else if (action==='more') {if(first)openMore();}
      else if (action === 'back') {
        if (first) back();
      } else move(action);
    }
  }
  setInterval(() => {
    const next = location.origin + location.pathname;
    if (next !== route) {
      diagnostics.record('route-change');
      route = next; epoch++;cancelAdvance('route'); current = null; saved = null; columnX=null; memory.clear(); clear();
      // No delayed autofocus: the next user input chooses a destination on the new page.
    }
  }, 200);
  document.documentElement.dataset.ptvNative = '1';
  document.documentElement.dataset.ptvVersion = '10.4';
  requestAnimationFrame(poll);
})();
