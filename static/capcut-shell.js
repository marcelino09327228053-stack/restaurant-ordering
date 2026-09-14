(function(){
  if(window.__mbCapcutModuleLoader)return;
  window.__mbCapcutModuleLoader=true;
  function load(src){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.async=false;s.onload=resolve;s.onerror=reject;document.head.appendChild(s)})}
  load('/static/capcut-core.js?v=20260913c')
    .then(()=>load('/static/capcut-advanced.js?v=20260913c'))
    .then(()=>load('/static/editor-timeline.js?v=1'))
    .then(()=>load('/static/studio-navigation-fix.js?v=20260914c'))
    .catch(err=>console.error('MB editor module load failed',err));
})();