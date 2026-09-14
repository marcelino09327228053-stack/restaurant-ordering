/* Keep Design Your Page, Menu, and Tables & QR as isolated workspaces. */
(function(){
  if (window.__mbStudioNavigationFixV3) return;
  window.__mbStudioNavigationFixV3 = true;

  function room(){ return document.getElementById('designRoom'); }

  function injectStyles(){
    if (document.getElementById('mbStudioIsolationStyleV3')) return;
    const style=document.createElement('style');
    style.id='mbStudioIsolationStyleV3';
    style.textContent=`
      #designRoom.mb-studio-section-open > .design-work,
      #designRoom.mb-studio-section-open #mbCapcutToolbar,
      #designRoom.mb-studio-section-open .design-slideshow,
      #designRoom.mb-studio-section-open #editorToolPanel,
      #designRoom.mb-studio-section-open #mbCapcutInspector,
      #designRoom.mb-studio-section-open #mbCapcutTimeline{display:none!important;}
      #designRoom.mb-studio-section-open .studio-panel[hidden]{display:none!important;}
      #designRoom.mb-studio-section-open .studio-panel:not([hidden]){display:flex!important;}
      #paymentsPanel{display:none!important;}

      #designRoom #tablesPanel{
        left:50%!important;right:auto!important;transform:translateX(-50%)!important;
        width:min(820px,calc(100% - 40px))!important;max-width:820px!important;
        top:calc(var(--studio-header-height,68px) + 18px)!important;bottom:auto!important;
        max-height:calc(100% - var(--studio-header-height,68px) - 36px)!important;
        border:1px solid #ffffff1d!important;border-radius:16px!important;
        background:#121418!important;box-shadow:0 22px 70px #0008!important;overflow:hidden!important;
      }
      #tablesPanel .studio-panel-head{
        display:flex!important;align-items:center!important;gap:12px!important;
        padding:16px 18px!important;border-bottom:1px solid #ffffff14!important;background:#15181d!important;
      }
      #tablesPanel .studio-panel-head h3{margin:0!important;font-size:18px!important;color:#ff9a4d!important;}
      #tablesPanel .studio-panel-head .grow{flex:1!important;}
      #tablesPanel .studio-panel-head .btn{min-height:36px!important;padding:7px 13px!important;}
      #tablesPanel .studio-panel-body{width:100%!important;overflow:auto!important;padding:16px 18px 18px!important;}

      #mbNativeTableTabs{margin:0 0 16px!important;position:static!important;border-radius:12px!important;background:#0c0f13!important;}
      #mbNativeTableTabs button{font-size:13px!important;letter-spacing:.01em!important;}

      #tablesBuilder.block,#mbNativePaymentPane .block{
        margin:0!important;border:1px solid #ffffff14!important;border-radius:14px!important;
        background:#0f1216!important;padding:16px!important;box-shadow:none!important;
      }
      #tablesBuilder h2,#mbNativePaymentPane h2{font-size:15px!important;margin:0 0 4px!important;}
      #tablesBuilder .hint,#mbNativePaymentPane .hint{margin-top:6px!important;color:#9da4ae!important;}
      #tablesBuilder>div[style*="display:flex"]{gap:10px!important;align-items:center!important;margin-top:14px!important;}
      #tablesBuilder input{min-height:42px!important;}
      #tablesBuilder .btn.solid{min-height:42px!important;padding:8px 16px!important;}
      #tableList{display:grid!important;gap:10px!important;margin-top:14px!important;}
      #tableList .table-qr-card{margin-top:0!important;border:1px solid #ffffff17!important;border-radius:12px!important;background:#0b0e12!important;padding:12px!important;}
      #tableList .table-qr-card img{width:104px!important;height:104px!important;border-radius:9px!important;}
      #tableList .table-qr-actions{gap:8px!important;}
      #tableList .table-qr-actions .btn{min-height:34px!important;}

      #mbDirectTableTabs,#mbTableTabs{display:none!important;}
    `;
    document.head.appendChild(style);
  }

  function removeLegacyTabs(){
    document.querySelectorAll('#mbDirectTableTabs,#mbTableTabs').forEach(node=>node.remove());
  }

  function installNavigation(){
    injectStyles();
    removeLegacyTabs();
    const host=room();
    if(!host){setTimeout(installNavigation,250);return;}
    const originalShow=typeof window.showDesignPage==='function'?window.showDesignPage:null;
    const originalToggle=typeof window.toggleStudioPanel==='function'?window.toggleStudioPanel:null;
    if(!originalShow||!originalToggle){setTimeout(installNavigation,250);return;}
    if(window.__mbStudioNavigationWrappedV3)return;
    window.__mbStudioNavigationWrappedV3=true;

    function hideEditorOnly(){
      host.classList.add('mb-studio-section-open');
      host.classList.remove('canvas-tools-visible');
      document.getElementById('designPageButton')?.setAttribute('aria-pressed','false');
      const toolPanel=document.getElementById('editorToolPanel');if(toolPanel)toolPanel.hidden=true;
      const slide=document.getElementById('slideshowPanel');if(slide)slide.hidden=true;
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
      if(!target)return originalToggle(id,force);
      const shouldOpen=typeof force==='boolean'?force:target.hidden;
      host.querySelectorAll('.studio-panel').forEach(panel=>panel.hidden=true);
      if(!shouldOpen){window.showDesignPage();return;}
      hideEditorOnly();
      target.hidden=false;
      syncButtons(id);
      removeLegacyTabs();
      if(id==='tablesPanel'&&typeof window.mbSelectTablesTab==='function')window.mbSelectTablesTab(requestedPayment?'payment':'tables');
      if(id==='menuPanel'){
        try{
          const customerPreview=document.getElementById('menuCustomerPreview');if(customerPreview)customerPreview.style.width='100%';
          const phone=document.getElementById('menuPhonePreview');if(phone)phone.setAttribute('aria-pressed','false');
          if(typeof window.refreshMenuCustomerPage==='function')window.refreshMenuCustomerPage();
        }catch(_){}
      }
      if(id==='previewPanel'&&typeof window.renderPreview==='function')window.renderPreview();
    };

    const observer=new MutationObserver(()=>{
      removeLegacyTabs();
      const active=[...host.querySelectorAll('.studio-panel')].find(panel=>!panel.hidden);
      if(active)hideEditorOnly();
    });
    observer.observe(host,{childList:true,subtree:true});
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',installNavigation,{once:true});
  else installNavigation();
})();