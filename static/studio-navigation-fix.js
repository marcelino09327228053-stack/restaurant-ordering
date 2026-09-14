/* Keep Design Your Page, Menu, and Tables & QR as isolated workspaces. */
(function(){
  if (window.__mbStudioNavigationFixV2) return;
  window.__mbStudioNavigationFixV2 = true;

  function room(){ return document.getElementById('designRoom'); }

  function injectStyles(){
    if (document.getElementById('mbStudioIsolationStyleV2')) return;
    const style = document.createElement('style');
    style.id = 'mbStudioIsolationStyleV2';
    style.textContent = `
      #designRoom.mb-studio-section-open > .design-work,
      #designRoom.mb-studio-section-open #mbCapcutToolbar,
      #designRoom.mb-studio-section-open .design-slideshow,
      #designRoom.mb-studio-section-open #editorToolPanel,
      #designRoom.mb-studio-section-open #mbCapcutInspector,
      #designRoom.mb-studio-section-open #mbCapcutTimeline {display:none!important;}
      #designRoom.mb-studio-section-open .studio-panel[hidden] {display:none!important;}
      #designRoom.mb-studio-section-open .studio-panel:not([hidden]) {display:flex!important;}
      #designRoom #tablesPanel {
        left:50%!important;right:auto!important;transform:translateX(-50%)!important;
        width:min(760px,calc(100% - 32px))!important;max-width:760px!important;
        top:calc(var(--studio-header-height,68px) + 20px)!important;bottom:auto!important;
        max-height:calc(100% - var(--studio-header-height,68px) - 40px)!important;
      }
      #designRoom #tablesPanel .studio-panel-body {width:100%;overflow:auto;}
      #paymentsPanel {display:none!important;}
      .mb-table-tabs {display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:4px;margin:0 0 16px;border:1px solid #ffffff1f;border-radius:12px;background:#0d1015;position:sticky;top:0;z-index:5;}
      .mb-table-tab {min-height:42px;border:1px solid transparent;border-radius:9px;background:transparent;color:#aeb4bd;font:700 12px Arial,sans-serif;cursor:pointer;}
      .mb-table-tab:hover {color:#fff;background:#ffffff08;}
      .mb-table-tab.active {color:#fff;background:#f97316;border-color:#fb923c;box-shadow:0 6px 20px #f9731626;}
      .mb-table-pane[hidden] {display:none!important;}
      .mb-table-pane {width:100%;}
      #mbPaymentPane .block {border:0;box-shadow:none;padding:0;margin:0;}
    `;
    document.head.appendChild(style);
  }

  function activateTablesTab(name){
    const host = room();
    const tablePane = document.getElementById('mbTableOrdersPane');
    const paymentPane = document.getElementById('mbPaymentPane');
    if (!host || !tablePane || !paymentPane) return;
    const payment = name === 'payment';
    tablePane.hidden = payment;
    paymentPane.hidden = !payment;
    host.querySelectorAll('.mb-table-tab').forEach(button => {
      const active = button.dataset.tab === (payment ? 'payment' : 'tables');
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
    });
  }

  function installTableTabs(){
    injectStyles();
    const body = document.getElementById('tablesPanelBody');
    if (!body) return false;
    if (document.getElementById('mbTableTabs')) return true;

    const paymentSection = document.getElementById('tablePaymentSection');
    const paymentBody = document.getElementById('paymentsPanelBody');
    if (!paymentBody) return false;

    const tabs = document.createElement('div');
    tabs.id = 'mbTableTabs';
    tabs.className = 'mb-table-tabs';
    tabs.setAttribute('role','tablist');
    tabs.setAttribute('aria-label','Table orders and payment');
    tabs.innerHTML = '<button type="button" class="mb-table-tab active" data-tab="tables" role="tab" aria-selected="true">Table Orders & QR</button><button type="button" class="mb-table-tab" data-tab="payment" role="tab" aria-selected="false">Payment</button>';

    const tablePane = document.createElement('section');
    tablePane.id = 'mbTableOrdersPane';
    tablePane.className = 'mb-table-pane';
    tablePane.setAttribute('role','tabpanel');

    const paymentPane = document.createElement('section');
    paymentPane.id = 'mbPaymentPane';
    paymentPane.className = 'mb-table-pane';
    paymentPane.setAttribute('role','tabpanel');
    paymentPane.hidden = true;

    [...body.children].forEach(child => {
      if (child !== paymentSection && child !== tabs) tablePane.appendChild(child);
    });
    paymentPane.appendChild(paymentBody);
    if (paymentSection) paymentSection.remove();
    body.append(tabs, tablePane, paymentPane);

    tabs.querySelector('[data-tab="tables"]').onclick = () => activateTablesTab('tables');
    tabs.querySelector('[data-tab="payment"]').onclick = () => activateTablesTab('payment');
    activateTablesTab('tables');
    return true;
  }

  function ensureTabs(){
    if (!installTableTabs()) setTimeout(ensureTabs, 200);
  }

  function installNavigation(){
    const host = room();
    if (!host) { setTimeout(installNavigation,250); return; }

    const originalShow = typeof window.showDesignPage === 'function' ? window.showDesignPage : null;
    const originalToggle = typeof window.toggleStudioPanel === 'function' ? window.toggleStudioPanel : null;
    if (!originalShow || !originalToggle) { setTimeout(installNavigation,250); return; }
    if (window.__mbStudioNavigationWrappedV2) return;
    window.__mbStudioNavigationWrappedV2 = true;

    function hideEditorOnly(){
      host.classList.add('mb-studio-section-open');
      host.classList.remove('canvas-tools-visible');
      document.getElementById('designPageButton')?.setAttribute('aria-pressed','false');
      const toolPanel=document.getElementById('editorToolPanel'); if(toolPanel) toolPanel.hidden=true;
      const slide=document.getElementById('slideshowPanel'); if(slide) slide.hidden=true;
      host.querySelector('.design-work')?.classList.remove('tool-panel-open');
      host.querySelectorAll('.tool-section').forEach(x=>x.hidden=true);
      host.querySelectorAll('.tool-rail [aria-expanded]').forEach(x=>x.setAttribute('aria-expanded','false'));
    }

    function syncButtons(activeId){
      host.querySelectorAll('.design-top [data-studio-panel]').forEach(button=>button.setAttribute('aria-expanded',String(button.dataset.studioPanel===activeId)));
    }

    window.showDesignPage=function(){
      host.classList.remove('mb-studio-section-open');
      host.querySelectorAll('.studio-panel').forEach(panel=>panel.hidden=true);
      originalShow();
      host.classList.add('canvas-tools-visible');
      syncButtons(null);
    };

    window.toggleStudioPanel=function(id,force){
      let requestedPayment=false;
      if(id==='paymentsPanel'){id='tablesPanel';force=true;requestedPayment=true;}
      const target=document.getElementById(id);
      if(!target) return originalToggle(id,force);
      const shouldOpen=typeof force==='boolean'?force:target.hidden;
      host.querySelectorAll('.studio-panel').forEach(panel=>panel.hidden=true);
      if(!shouldOpen){window.showDesignPage();return;}
      hideEditorOnly();
      target.hidden=false;
      syncButtons(id);
      if(id==='tablesPanel'){
        installTableTabs();
        activateTablesTab(requestedPayment?'payment':'tables');
      }
      if(id==='menuPanel'){
        try{
          const customerPreview=document.getElementById('menuCustomerPreview'); if(customerPreview) customerPreview.style.width='100%';
          const phone=document.getElementById('menuPhonePreview'); if(phone) phone.setAttribute('aria-pressed','false');
          if(typeof window.refreshMenuCustomerPage==='function') window.refreshMenuCustomerPage();
        }catch(_){}
      }
      if(id==='previewPanel'&&typeof window.renderPreview==='function') window.renderPreview();
    };

    const observer=new MutationObserver(()=>{
      installTableTabs();
      const active=[...host.querySelectorAll('.studio-panel')].find(panel=>!panel.hidden);
      if(active) hideEditorOnly();
    });
    observer.observe(host,{childList:true,subtree:true});
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',()=>{ensureTabs();installNavigation();},{once:true});
  } else {
    ensureTabs();
    installNavigation();
  }
})();
