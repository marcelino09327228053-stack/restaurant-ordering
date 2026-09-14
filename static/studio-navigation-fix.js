/* Keep the original Design Your Page and Menu behavior. Only add Tables & QR routing/polish. */
(function(){
  if (window.__mbStudioTablesOnlyFix) return;
  window.__mbStudioTablesOnlyFix = true;

  function injectTableStyles(){
    if (document.getElementById('mbTablesOnlyStyle')) return;
    const style=document.createElement('style');
    style.id='mbTablesOnlyStyle';
    style.textContent=`
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
      #tablesBuilder>div[style*="display:flex"]{gap:10px!important;align-items:center!important;margin-top:14px!important;}
      #tablesBuilder input{min-height:42px!important;}
      #tablesBuilder .btn.solid{min-height:42px!important;padding:8px 16px!important;}
      #tableList{display:grid!important;gap:10px!important;margin-top:14px!important;}
      #tableList .table-qr-card{margin-top:0!important;border:1px solid #ffffff17!important;border-radius:12px!important;background:#0b0e12!important;padding:12px!important;}
      #tableList .table-qr-card img{width:104px!important;height:104px!important;border-radius:9px!important;}
      #mbDirectTableTabs,#mbTableTabs{display:none!important;}
    `;
    document.head.appendChild(style);
  }

  function cleanupLegacyTabs(){
    document.querySelectorAll('#mbDirectTableTabs,#mbTableTabs').forEach(node=>node.remove());
  }

  function install(){
    injectTableStyles();
    cleanupLegacyTabs();
    if (typeof window.toggleStudioPanel !== 'function') { setTimeout(install,250); return; }
    if (window.__mbTablesOnlyWrapped) return;
    window.__mbTablesOnlyWrapped = true;

    const originalToggle = window.toggleStudioPanel;
    window.toggleStudioPanel = function(id, force){
      if (id === 'paymentsPanel') {
        const result = originalToggle('tablesPanel', true);
        setTimeout(()=>window.mbSelectTablesTab?.('payment'),0);
        return result;
      }
      if (id === 'tablesPanel') {
        const result = originalToggle(id, force);
        setTimeout(()=>{
          cleanupLegacyTabs();
          if (!document.getElementById('tablesPanel')?.hidden) window.mbSelectTablesTab?.('tables');
        },0);
        return result;
      }
      /* Menu and Design Your Page intentionally use the original application behavior unchanged. */
      return originalToggle(id, force);
    };
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',install,{once:true});
  else install();
})();
