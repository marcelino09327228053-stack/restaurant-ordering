/* Keep Design Your Page, Menu, and Tables & QR as isolated workspaces. */
(function(){
  if (window.__mbStudioNavigationFix) return;
  window.__mbStudioNavigationFix = true;

  function install(){
    const room = document.getElementById('designRoom');
    if (!room || typeof window.showDesignPage !== 'function' || typeof window.toggleStudioPanel !== 'function') {
      setTimeout(install, 250);
      return;
    }

    if (!document.getElementById('mbStudioIsolationStyle')) {
      const style = document.createElement('style');
      style.id = 'mbStudioIsolationStyle';
      style.textContent = `
        #designRoom.mb-studio-section-open > .design-work,
        #designRoom.mb-studio-section-open #mbCapcutToolbar,
        #designRoom.mb-studio-section-open .design-slideshow,
        #designRoom.mb-studio-section-open #editorToolPanel,
        #designRoom.mb-studio-section-open #mbCapcutInspector,
        #designRoom.mb-studio-section-open #mbCapcutTimeline {
          display:none !important;
        }
        #designRoom.mb-studio-section-open .studio-panel[hidden] { display:none !important; }
        #designRoom.mb-studio-section-open .studio-panel:not([hidden]) { display:flex !important; }
        #designRoom #tablesPanel {
          left:50% !important;
          right:auto !important;
          transform:translateX(-50%) !important;
          width:min(760px, calc(100% - 32px)) !important;
          max-width:760px !important;
          top:calc(var(--studio-header-height, 68px) + 20px) !important;
          bottom:auto !important;
          max-height:calc(100% - var(--studio-header-height, 68px) - 40px) !important;
        }
        #designRoom #tablesPanel .studio-panel-body { width:100%; overflow:auto; }
        #tablePaymentSection {
          margin-top:18px !important;
          padding-top:14px !important;
          border-top:1px solid #ffffff24 !important;
        }
        #tablePaymentSection > summary {
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:10px;
          cursor:pointer;
          padding:10px 12px !important;
          border:1px solid #ffffff20;
          border-radius:10px;
          background:#ffffff08;
        }
        #tablePaymentSection > summary::after { content:'▾'; opacity:.7; }
        #tablePaymentSection[open] > summary::after { content:'▴'; }
        #paymentsPanel { display:none !important; }
      `;
      document.head.appendChild(style);
    }

    const originalShowDesignPage = window.showDesignPage;
    const originalToggleStudioPanel = window.toggleStudioPanel;

    function hideEditorOnly(){
      room.classList.add('mb-studio-section-open');
      room.classList.remove('canvas-tools-visible');
      const designButton = document.getElementById('designPageButton');
      if (designButton) designButton.setAttribute('aria-pressed','false');
      const toolPanel = document.getElementById('editorToolPanel');
      if (toolPanel) toolPanel.hidden = true;
      const slide = document.getElementById('slideshowPanel');
      if (slide) slide.hidden = true;
      room.querySelector('.design-work')?.classList.remove('tool-panel-open');
      room.querySelectorAll('.tool-section').forEach(x => x.hidden = true);
      room.querySelectorAll('.tool-rail [aria-expanded]').forEach(x => x.setAttribute('aria-expanded','false'));
    }

    function syncButtons(activeId){
      room.querySelectorAll('.design-top [data-studio-panel]').forEach(button => {
        button.setAttribute('aria-expanded', String(button.dataset.studioPanel === activeId));
      });
    }

    window.showDesignPage = function(){
      room.classList.remove('mb-studio-section-open');
      room.querySelectorAll('.studio-panel').forEach(panel => panel.hidden = true);
      const paymentPanel = document.getElementById('paymentsPanel');
      if (paymentPanel) paymentPanel.hidden = true;
      originalShowDesignPage();
      room.classList.add('canvas-tools-visible');
      syncButtons(null);
    };

    window.toggleStudioPanel = function(id, force){
      if (id === 'paymentsPanel') {
        id = 'tablesPanel';
        force = true;
        setTimeout(() => {
          const payment = document.getElementById('tablePaymentSection');
          if (payment) payment.open = true;
        }, 0);
      }

      const target = document.getElementById(id);
      if (!target) return originalToggleStudioPanel(id, force);
      const isOpen = !target.hidden;
      const shouldOpen = typeof force === 'boolean' ? force : !isOpen;

      room.querySelectorAll('.studio-panel').forEach(panel => panel.hidden = true);
      if (!shouldOpen) {
        window.showDesignPage();
        return;
      }

      hideEditorOnly();
      target.hidden = false;
      syncButtons(id);

      if (id === 'menuPanel') {
        try {
          const customerPreview = document.getElementById('menuCustomerPreview');
          if (customerPreview) customerPreview.style.width = '100%';
          const phone = document.getElementById('menuPhonePreview');
          if (phone) phone.setAttribute('aria-pressed','false');
          if (typeof window.refreshMenuCustomerPage === 'function') window.refreshMenuCustomerPage();
        } catch (_) {}
      }
      if (id === 'previewPanel' && typeof window.renderPreview === 'function') window.renderPreview();
    };

    // Re-apply isolation after injected CapCut modules finish mounting.
    const observer = new MutationObserver(() => {
      const active = [...room.querySelectorAll('.studio-panel')].find(panel => !panel.hidden);
      if (active) hideEditorOnly();
    });
    observer.observe(room, {childList:true, subtree:true});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})();
