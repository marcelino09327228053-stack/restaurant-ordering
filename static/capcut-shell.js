(function(){
  if(window.__mbCapcutModuleLoader)return;
  window.__mbCapcutModuleLoader=true;

  function cleanupLegacyTableTabs(){
    document.querySelectorAll('#mbDirectTableTabs,#mbTableTabs').forEach(node=>node.remove());
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',cleanupLegacyTableTabs,{once:true});
  }else{
    cleanupLegacyTableTabs();
  }
  window.addEventListener('load',()=>setTimeout(cleanupLegacyTableTabs,900));

  function load(src){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.async=false;s.onload=resolve;s.onerror=reject;document.head.appendChild(s)})}
  load('/static/capcut-core.js?v=20260913c')
    .then(()=>load('/static/capcut-advanced.js?v=20260913c'))
    .then(()=>load('/static/editor-timeline.js?v=2'))
    .then(()=>load('/static/studio-navigation-fix.js?v=20260914e'))
    .then(()=>{cleanupLegacyTableTabs();setTimeout(cleanupLegacyTableTabs,300);})
    .catch(err=>console.error('MB editor module load failed',err));
})();