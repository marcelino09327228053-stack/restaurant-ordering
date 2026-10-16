/* Customer Display: one upload, one background selector, one save. */
(() => {
  const defaults={background:'#0b0b0d',text:'#f5f5f4',gradient:false,gradient_color:'#6d28ff',background_image:'',glow:false,intensity:'medium',media_url:'',media_type:'none'};
  let draft,dirty=false,busy=false;
  const $=id=>document.getElementById(id);
  const status=text=>{$('menuEditorStatus').textContent=text;};
  function renderMedia(){
    const box=$('me-media-preview');
    if(!box)return;
    box.style.background=draft.background;
    if(!draft.media_url){
      box.innerHTML='';
      box.hidden=true;
      return;
    }
    box.hidden=false;
    box.innerHTML=draft.media_type==='video'
      ? `<video src="${draft.media_url}" controls playsinline preload="metadata"></video>`
      : `<img src="${draft.media_url}" alt="Customer display media">`;
  }
  function sync(){ $('me-remove').disabled=busy || !draft.media_url;renderMedia(); }
  function changed(){dirty=true;status('Unsaved changes');sync();}
  function lock(value){busy=value;for(const id of ['me-upload','me-save'])$(id).disabled=value;sync();}
  function color(value){draft.background=value;draft.gradient=false;draft.background_image='';changed();}
  async function upload(file){
    if(!file || busy)return;
    const image=['image/jpeg','image/png','image/webp','image/gif'].includes(file.type),video=['video/mp4','video/webm'].includes(file.type);
    if(!image && !video){status('Choose an image or an MP4 / WebM video.');return;}
    if(!file.size){status('This file is empty. Choose another file.');return;}
    lock(true);status('Uploading…');
    try{
      const form=new FormData();form.append('kind',video?'menu_video':'menu_display');form.append('file',file);
      const response=await fetch('/api/owner/upload',{method:'POST',headers:{Authorization:`Bearer ${token()}`},body:form});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(response.status===413?'This file is too large for the server. Try a smaller file.':response.status===401?'Please sign in again.':'Upload failed. Try another file.');
      draft.media_url=data.url;draft.media_type=video?'video':'image';changed();
    }catch(error){status(error instanceof TypeError?'Upload failed. Check your connection or try a smaller file.':error.message);}
    finally{lock(false);}
  }
  function install(){
    if(typeof owner==='undefined' || !owner?.id || !$('menuEditorControls')){setTimeout(install,200);return;}
    draft={...defaults,...owner.custom_design?.menuTheme};
    $('menuEditorControls').innerHTML=`<div class="me-actions" id="customerDisplayActions">
      <button class="btn" type="button" id="me-upload">Upload Media</button>
      <button class="btn" type="button" id="me-remove">Remove</button>
      <button class="btn solid" type="button" id="me-save">Save</button>
      </div>
      <input hidden id="me-media-file" type="file" accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm">
      <div id="me-media-preview" hidden></div>
      <p id="menuEditorStatus" role="status" aria-live="polite"></p>`;
    $('me-upload').onclick=()=>$('me-media-file').click();
    $('me-media-file').onchange=e=>{upload(e.target.files[0]);e.target.value='';};
    $('me-remove').onclick=()=>{draft.media_url='';draft.media_type='none';changed();};
    $('me-save').onclick=async()=>{
      if(busy)return;const config=structuredClone(draft);lock(true);status('Saving…');
      try{owner=await api('/api/owner/menu-appearance',{method:'PATCH',body:JSON.stringify(config)});dirty=JSON.stringify(draft)!==JSON.stringify(config);status(dirty?'Unsaved changes':'Saved');}
      catch{status('Could not save. Please try again.');}finally{lock(false);}
    };
    window.addEventListener('beforeunload',e=>{if(dirty || busy){e.preventDefault();e.returnValue='';}});
    sync();
  }
  install();
})();
