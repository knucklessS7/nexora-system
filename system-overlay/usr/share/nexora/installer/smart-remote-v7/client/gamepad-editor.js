'use strict';
/*
 * Editor local de layout para o Gamepad da V8.5.
 * Permite alternar entre edição em conjunto e separada para d-pad e A/B/X/Y.
 */
(() => {
  const card = document.querySelector('#panel-gamepad .gamepad-card');
  if (!card) return;
  const panel = document.getElementById('gamepadEditor');
  const toggle = document.getElementById('customizeGamepadBtn');
  const modeToggle = document.getElementById('gamepadEditModeToggle');
  const sizeInput = document.getElementById('gamepadSize');
  const sizeOutput = document.getElementById('gamepadSizeValue');
  const spacingInput = document.getElementById('gamepadSpacing');
  const spacingOutput = document.getElementById('gamepadSpacingValue');
  const saveButton = document.getElementById('gamepadSaveLayout');
  const cancelButton = document.getElementById('gamepadCancelLayout');
  const resetButton = document.getElementById('gamepadResetLayout');
  const info = document.getElementById('gamepadEditInfo');
  const collapseButton = document.getElementById('gamepadCollapseEditor');
  const STORAGE_KEY = 'batocera-smart-remote-gamepad-v3';
  const MIN_SCALE = 0.60, MAX_SCALE = 1.85, MIN_GAP = 0.70, MAX_GAP = 1.55;
  const clamp = (n, low, high) => Math.max(low, Math.min(high, n));
  const controlSpecs = [
    ['L1','L1','[data-command="L1"]'], ['L2','L2','[data-command="L2"]'], ['R2','R2','[data-command="R2"]'], ['R1','R1','[data-command="R1"]'],
    ['DPAD_GROUP','Direcional','.dpad.small','group'], ['FACE_GROUP','A / B / X / Y','.face-buttons','group'],
    ['GP_UP','Seta cima','[data-command="GP_UP"]'], ['GP_LEFT','Seta esquerda','[data-command="GP_LEFT"]'], ['GP_RIGHT','Seta direita','[data-command="GP_RIGHT"]'], ['GP_DOWN','Seta baixo','[data-command="GP_DOWN"]'],
    ['Y','Y','[data-command="Y"]'], ['X','X','[data-command="X"]'], ['B','B','[data-command="B"]'], ['A','A','[data-command="A"]'],
    ['SELECT_GAME','Select','[data-command="SELECT_GAME"]'], ['START','Start','[data-command="START"]'],
    ['STICK_LEFT','L3','[data-stick="LEFT"]'], ['STICK_RIGHT','R3','[data-stick="RIGHT"]']
  ];
  const controls = new Map();
  for (const [id, name, selector, type='single'] of controlSpecs) {
    let element = card.querySelector(selector);
    if ((id === 'STICK_LEFT' || id === 'STICK_RIGHT') && element) element = element.closest('.analog-group');
    if (!element) throw new Error(`Controle ausente no editor: ${id}`);
    controls.set(id, { element, name, type, grouped: type==='group' });
  }
  for (const [id, item] of controls) {
    item.element.classList.add('gp-layout-item');
    item.element.dataset.layoutId = id;
    item.element.dataset.layoutName = item.name;
    item.element.dataset.customScale = '1';
    item.element.style.setProperty('--gp-x', '0px');
    item.element.style.setProperty('--gp-y', '0px');
    item.element.style.setProperty('--gp-scale', '1');
    if (item.grouped) item.element.style.setProperty('--gp-gap-scale', '1');
  }

  function readStored() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (parsed?.version === 3 && parsed.layouts && typeof parsed.layouts === 'object') return parsed.layouts;
    } catch (_) {}
    return {};
  }
  const layouts = readStored();
  const orientation = () => matchMedia('(orientation: landscape)').matches ? 'landscape' : 'portrait';
  let activeOrientation = orientation();
  let editing = false, selected = null, gesture = null, resizeFrame = 0;
  let editMode = 'group';
  let draft = {};

  const initial = id => controls.get(id)?.grouped ? { x:0, y:0, s:1, g:1 } : { x:0, y:0, s:1 };
  function sanitized(input) {
    const result = {};
    if (!input || typeof input !== 'object') return result;
    for (const id of controls.keys()) {
      const o = input[id];
      if (!o || typeof o !== 'object') continue;
      const x=Number(o.x), y=Number(o.y), s=Number(o.s);
      if (![x,y,s].every(Number.isFinite)) continue;
      const clean = { x:clamp(x,-2,2), y:clamp(y,-2,2), s:clamp(s,MIN_SCALE,MAX_SCALE) };
      if (controls.get(id)?.grouped) {
        const g = Number(o.g);
        clean.g = Number.isFinite(g) ? clamp(g,MIN_GAP,MAX_GAP) : 1;
      }
      result[id] = clean;
    }
    return result;
  }
  const copied = v => JSON.parse(JSON.stringify(v));
  const getValue = id => draft[id] || initial(id);
  const canUseSpacing = id => !!id && !!controls.get(id)?.grouped;

  function persistLayouts() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({version:3, layouts})); return true; }
    catch (_) { return false; }
  }

  function render() {
    const width=Math.max(1, card.clientWidth), height=Math.max(1, card.clientHeight);
    for (const [id, item] of controls) {
      const v = getValue(id);
      item.element.style.setProperty('--gp-x', `${Math.round(width*v.x*10)/10}px`);
      item.element.style.setProperty('--gp-y', `${Math.round(height*v.y*10)/10}px`);
      item.element.style.setProperty('--gp-scale', String(v.s));
      if (item.grouped) item.element.style.setProperty('--gp-gap-scale', String(v.g ?? 1));
      item.element.dataset.customScale = String(v.s);
      item.element.classList.toggle('gp-selected', editing && id === selected);
    }
    card.classList.toggle('gp-has-custom-layout', Object.keys(draft).length > 0);
    card.dataset.editMode = editMode;
    card.classList.toggle('gp-edit-group', editMode === 'group');
    card.classList.toggle('gp-edit-separate', editMode === 'separate');
  }

  function refreshInputs() {
    sizeInput.disabled = !selected;
    spacingInput.disabled = !canUseSpacing(selected);
    if (!selected) {
      sizeInput.value='100'; sizeOutput.value='100%'; spacingInput.value='100'; spacingOutput.value='100%';
      return;
    }
    const v=getValue(selected);
    sizeInput.value = Math.round(v.s*100); sizeOutput.value = `${sizeInput.value}%`;
    const gapPercent = Math.round((v.g ?? 1) * 100);
    spacingInput.value = gapPercent; spacingOutput.value = `${gapPercent}%`;
  }

  function updateModeLabel() {
    modeToggle.textContent = editMode === 'group' ? 'Modo: Conjunto' : 'Modo: Separado';
    modeToggle.setAttribute('aria-pressed', String(editMode === 'group'));
  }

  function select(id) {
    selected = id;
    refreshInputs();
    if (!id) {
      info.textContent = editMode === 'group'
        ? 'Toque em um conjunto, analógico, gatilho, Select ou Start.'
        : 'Toque em um botão individual, analógico, gatilho, Select ou Start.';
      render();
      return;
    }
    const meta = controls.get(id);
    info.textContent = meta.grouped
      ? `${meta.name} selecionado. Arraste para mover e ajuste tamanho e espaço entre os botões.`
      : `${meta.name} selecionado. Arraste para mover ou altere o tamanho.`;
    render();
  }

  function showEditor(active) {
    editing = active;
    card.classList.toggle('gp-editing', active);
    panel.hidden = !active;
    panel.classList.remove('is-collapsed');
    collapseButton.textContent='Recolher';
    collapseButton.setAttribute('aria-expanded','true');
    toggle.setAttribute('aria-pressed', String(active));
    toggle.classList.toggle('is-editing', active);
    toggle.querySelector('span').textContent = active ? 'Editando' : 'Personalizar';
    if (!active) select(null);
    updateModeLabel();
    render();
  }
  function begin() {
    if (editing) return;
    window.dispatchEvent(new CustomEvent('gamepad-editor-start'));
    activeOrientation = orientation();
    draft = sanitized(layouts[activeOrientation]);
    showEditor(true);
    select(null);
    render();
  }
  function cancel() {
    if (!editing) return;
    gesture = null;
    showEditor(false);
    draft = sanitized(layouts[activeOrientation]);
    render();
  }
  function save() {
    if (!editing) return;
    gesture = null;
    const clean = sanitized(draft);
    if (Object.keys(clean).length) layouts[activeOrientation] = copied(clean); else delete layouts[activeOrientation];
    const persisted = persistLayouts();
    showEditor(false);
    render();
    document.getElementById('eventStatus').textContent = persisted ? 'Layout salvo neste celular.' : 'Layout aplicado, mas o navegador não permitiu armazená-lo.';
  }
  function reset() {
    if (!editing) return;
    gesture = null;
    delete layouts[activeOrientation];
    persistLayouts();
    draft = {};
    showEditor(false);
    render();
    document.getElementById('eventStatus').textContent = 'Disposição original restaurada neste aparelho.';
  }

  function resolveEditableTarget(target) {
    if (!(target instanceof Element)) return null;
    if (target.closest('#gamepadEditor')) return null;
    const dpadButton = target.closest('.dpad.small [data-command^="GP_"]');
    const faceButton = target.closest('.face-buttons [data-command]');
    if (editMode === 'group') {
      if (dpadButton) return controls.get('DPAD_GROUP')?.element;
      if (faceButton) return controls.get('FACE_GROUP')?.element;
    } else {
      if (dpadButton) return dpadButton;
      if (faceButton) return faceButton;
    }
    const byLayout = target.closest('[data-layout-id]');
    return byLayout && card.contains(byLayout) ? byLayout : null;
  }

  collapseButton.addEventListener('click',()=>{
    const collapsed=panel.classList.toggle('is-collapsed');
    collapseButton.textContent=collapsed?'Expandir':'Recolher';
    collapseButton.setAttribute('aria-expanded', String(!collapsed));
  });
  toggle.addEventListener('click',()=>editing?cancel():begin());
  modeToggle.addEventListener('click',()=>{
    editMode = editMode === 'group' ? 'separate' : 'group';
    updateModeLabel();
    select(null);
    render();
  });
  saveButton.addEventListener('click',save);
  cancelButton.addEventListener('click',cancel);
  resetButton.addEventListener('click',reset);
  sizeInput.addEventListener('input',()=>{
    if (!editing || !selected) return;
    const v={...getValue(selected), s:clamp(Number(sizeInput.value)/100, MIN_SCALE, MAX_SCALE)};
    draft[selected]=v; sizeOutput.value=`${Math.round(v.s*100)}%`; render();
  });
  spacingInput.addEventListener('input',()=>{
    if (!editing || !canUseSpacing(selected)) return;
    const v={...getValue(selected), g:clamp(Number(spacingInput.value)/100, MIN_GAP, MAX_GAP)};
    draft[selected]=v; spacingOutput.value=`${Math.round(v.g*100)}%`; render();
  });

  card.addEventListener('pointerdown', e => {
    if (!editing) return;
    const node = resolveEditableTarget(e.target);
    if (!node || !card.contains(node)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (gesture) return;
    const id = node.dataset.layoutId;
    select(id);
    const itemRect=node.getBoundingClientRect(), bounds=card.getBoundingClientRect();
    gesture={pointerId:e.pointerId,node,id,x:e.clientX,y:e.clientY,itemRect,bounds,base:{...getValue(id)}};
    try { node.setPointerCapture(e.pointerId); } catch (_) {}
  }, true);
  card.addEventListener('pointermove', e => {
    if (!editing || !gesture || gesture.pointerId !== e.pointerId) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const {bounds,itemRect,base,id}=gesture;
    const limit=(v,lo,hi)=>lo>hi?0:clamp(v,lo,hi);
    const dx=limit(e.clientX-gesture.x,bounds.left+5-itemRect.left,bounds.right-5-itemRect.right);
    const dy=limit(e.clientY-gesture.y,bounds.top+5-itemRect.top,bounds.bottom-5-itemRect.bottom);
    draft[id]={...base, x:clamp(base.x+dx/Math.max(1,bounds.width),-2,2), y:clamp(base.y+dy/Math.max(1,bounds.height),-2,2)};
    render();
  }, true);
  function endPointer(e){
    if (!editing || !gesture || gesture.pointerId !== e.pointerId) return;
    e.preventDefault(); e.stopImmediatePropagation();
    try { gesture.node.releasePointerCapture(e.pointerId); } catch (_) {}
    gesture = null;
  }
  card.addEventListener('pointerup', endPointer, true);
  card.addEventListener('pointercancel', endPointer, true);
  card.addEventListener('lostpointercapture', e=>{ if (gesture?.pointerId === e.pointerId) gesture = null; }, true);
  card.addEventListener('click', e=>{ if (editing && resolveEditableTarget(e.target)) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);
  card.addEventListener('contextmenu', e=>{ if (editing && resolveEditableTarget(e.target)) e.preventDefault(); });
  window.addEventListener('keydown',e=>{ if(editing && ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Escape',' '].includes(e.key)) e.stopImmediatePropagation(); }, true);
  window.addEventListener('keyup',e=>{ if(editing && ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Escape',' '].includes(e.key)) e.stopImmediatePropagation(); }, true);
  window.addEventListener('blur',()=>{ if(gesture) gesture=null; });
  function applyOrientation(){
    const next = orientation();
    if (next !== activeOrientation) { if (editing) cancel(); activeOrientation=next; draft=sanitized(layouts[activeOrientation]); }
    render();
  }
  window.addEventListener('gamepad-layout-visible',()=>requestAnimationFrame(render));
  window.addEventListener('resize',()=>{ cancelAnimationFrame(resizeFrame); resizeFrame=requestAnimationFrame(applyOrientation); });

  draft = sanitized(layouts[activeOrientation]);
  updateModeLabel();
  render();
  window.GamepadLayoutEditor = { cancel, isEditing:()=>editing };
})();
