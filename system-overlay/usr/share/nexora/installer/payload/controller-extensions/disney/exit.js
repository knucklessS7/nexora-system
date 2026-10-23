(() => {
  // Standard Xbox: View + Menu closes this app's tab only.
  let held = false;
  function poll() {
    if (globalThis.AURA_NATIVE_CONTROLLER) { requestAnimationFrame(poll); return; }
    const gamepad = [...(navigator.getGamepads?.() || [])].find(p => p?.connected && p.mapping === 'standard');
    const combo = document.hasFocus() && gamepad?.buttons[8]?.pressed && gamepad?.buttons[9]?.pressed;
    if (combo && !held) chrome.runtime.sendMessage({action:'stream-tv-close'}).catch(()=>{});
    held = !!combo; requestAnimationFrame(poll);
  }
  requestAnimationFrame(poll);
})();
