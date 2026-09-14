(function(){
  if(window.__mbCapcutModuleLoader)return;
  window.__mbCapcutModuleLoader=true;

  function installDirectTablesTabs(){
    const body=document.getElementById('tablesPanelBody');
    const paymentSection=document.getElementById('tablePaymentSection');
    const paymentBody=document.getElementById('paymentsPanelBody');

    // setupStudioWorkspace creates/moves the real table + payment content first.
    // Do not build the tabs until that move is finished, otherwise the old
    // accordion gets recreated after us.
    if(!body||!paymentSection||!paymentBody||!paymentSection.contains(paymentBody)){
      setTimeout(installDirectTablesTabs,200);
      return;
    }

    // If an older early install exists, remove it and rebuild from the final DOM.
    document.getElementById('mbDirectTableTabs')?.remove();
    const oldTablePane=document.getElementById('mbDirectTablePane');
    const oldPaymentPane=document.getElementById('mbDirectPaymentPane');
    if(oldTablePane){[...oldTablePane.children].forEach(child=>body.insertBefore(child,paymentSection));oldTablePane.remove();}
    if(oldPaymentPane){if(oldPaymentPane.contains(paymentBody))paymentSection.appendChild(paymentBody);oldPaymentPane.remove();}

    if(!document.getElementById('mbDirectTableTabsStyle')){
      const style=document.createElement('style');
      style.id='mbDirectTableTabsStyle';
      style.textContent=`
        #tablesPanel{left:50%!important;right:auto!important;transform:translateX(-50%)!important;width:min(760px,calc(100% - 32px))!important;max-width:760px!important;}
        #tablesPanelBody{width:100%!important;overflow:auto!important;}
        #mbDirectTableTabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:4px;margin:0 0 16px;border:1px solid #ffffff1f;border-radius:12px;background:#0d1015;position:sticky;top:0;z-index:20}
        #mbDirectTableTabs button{min-height:44px;border:1px solid transparent;border-radius:9px;background:transparent;color:#aeb4bd;font:700 13px Arial,sans-serif;cursor:pointer}
        #mbDirectTableTabs button:hover{color:#fff;background:#ffffff08}
        #mbDirectTableTabs button.active{color:#fff;background:#f97316;border-color:#fb923c;box-shadow:0 6px 20px #f9731626}
        .mb-direct-pane[hidden]{display:none!important}
        .mb-direct-pane{width:100%}
        #mbDirectPaymentPane .block{border:0!important;box-shadow:none!important;padding:0!important;margin:0!important}
        #tablePaymentSection{display:none!important}
      `;
      document.head.appendChild(style);
    }

    const tabs=document.createElement('div');
    tabs.id='mbDirectTableTabs';
    tabs.setAttribute('role','tablist');
    tabs.setAttribute('aria-label','Table orders and payment');
    tabs.innerHTML='<button type="button" class="active" data-tab="tables" role="tab" aria-selected="true">Table & QR</button><button type="button" data-tab="payment" role="tab" aria-selected="false">Payment</button>';

    const tablePane=document.createElement('section');
    tablePane.id='mbDirectTablePane';
    tablePane.className='mb-direct-pane';
    tablePane.setAttribute('role','tabpanel');

    const paymentPane=document.createElement('section');
    paymentPane.id='mbDirectPaymentPane';
    paymentPane.className='mb-direct-pane';
    paymentPane.setAttribute('role','tabpanel');
    paymentPane.hidden=true;

    [...body.children].forEach(child=>{
      if(child!==paymentSection)tablePane.appendChild(child);
    });
    paymentPane.appendChild(paymentBody);
    paymentSection.remove();
    body.replaceChildren(tabs,tablePane,paymentPane);

    function select(name){
      const payment=name==='payment';
      tablePane.hidden=payment;
      paymentPane.hidden=!payment;
      tabs.querySelectorAll('button').forEach(btn=>{
        const active=btn.dataset.tab===name;
        btn.classList.toggle('active',active);
        btn.setAttribute('aria-selected',String(active));
      });
      body.scrollTop=0;
    }

    tabs.querySelector('[data-tab="tables"]').onclick=()=>select('tables');
    tabs.querySelector('[data-tab="payment"]').onclick=()=>select('payment');
    select('tables');
    window.mbSelectTablesTab=select;
  }

  // setupStudioWorkspace runs after the page is initialized, so keep retrying
  // until the final Tables & QR structure exists.
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',()=>setTimeout(installDirectTablesTabs,300),{once:true});
  }else{
    setTimeout(installDirectTablesTabs,300);
  }
  window.addEventListener('load',()=>setTimeout(installDirectTablesTabs,500));

  function load(src){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.async=false;s.onload=resolve;s.onerror=reject;document.head.appendChild(s)})}
  load('/static/capcut-core.js?v=20260913c')
    .then(()=>load('/static/capcut-advanced.js?v=20260913c'))
    .then(()=>load('/static/editor-timeline.js?v=2'))
    .then(()=>load('/static/studio-navigation-fix.js?v=20260914d'))
    .catch(err=>console.error('MB editor module load failed',err));
})();