(() => {
  function activateStudio() {
    const legacyTop = document.querySelector('body > .top');
    const legacyShell = document.querySelector('body > .shell');
    if (legacyTop) legacyTop.style.display = 'none';
    if (legacyShell) legacyShell.style.display = 'none';

    document.title = 'Design Your Page';

    try {
      if (typeof window.setupStudioWorkspace === 'function' && !document.body.classList.contains('studio-only')) {
        window.setupStudioWorkspace();
      }
    } catch (error) {
      console.error('Studio workspace setup failed:', error);
    }

    try {
      const designRoom = document.getElementById('designRoom');
      if (designRoom) designRoom.hidden = false;
      if (typeof window.openDesignRoom === 'function') {
        window.openDesignRoom();
      }
    } catch (error) {
      console.error('Design room startup failed:', error);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', activateStudio, { once: true });
  } else {
    activateStudio();
  }
})();
