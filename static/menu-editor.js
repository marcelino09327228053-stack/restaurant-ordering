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
    box.hidden=false;
    const key=draft.media_type+':'+draft.media_url;
    if(box.dataset.media===key)return;
    box.dataset.media=key;
    box.replaceChildren();
    if(!draft.media_url || draft.media_type==='none')return;
    const media=document.createElement(draft.media_type==='video'?'video':'img');
    media.src=draft.media_url;
    if(draft.media_type==='video'){media.controls=true;media.playsInline=true;media.preload='metadata';}
    else media.alt='Customer display media';
    media.onerror=()=>{box.replaceChildren();};
    box.append(media);
  }
  function sync(){ if($('me-background'))$('me-background').value=draft.background; $('me-remove').disabled=busy || !draft.media_url;renderMedia(); }
  function changed(){dirty=true;status('Unsaved changes');sync();}
  function lock(value){busy=value;for(const id of ['me-upload','me-save'])$(id).disabled=value;sync();}
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
      <button class="btn" type="button" id="customerDisplayBackgroundButton" aria-controls="customerDisplayBackgroundPanel" aria-expanded="false">Background</button>
      <button class="btn solid" type="button" id="me-save">Save</button>
      </div>
      <input hidden id="me-media-file" type="file" accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm">
      <div id="customerDisplayBackgroundPanel" hidden aria-label="Background color"><div id="me-swatches"></div><label>Custom<input id="me-background" type="color" aria-label="Custom background color"></label></div>
      <div id="me-media-preview" aria-label="Customer display media"></div>
      <p id="menuEditorStatus" role="status" aria-live="polite"></p>`;
    const panel=open=>{$('customerDisplayBackgroundPanel').hidden=!open;$('customerDisplayBackgroundButton').setAttribute('aria-expanded',String(open));};
    $('customerDisplayBackgroundButton').onclick=()=>panel($('customerDisplayBackgroundPanel').hidden);
    const color=value=>{draft.background=value;draft.gradient=false;draft.background_image='';changed();};
    for(const [name,value] of [['Green','#39ff14'],['Blue','#0066ff'],['Red','#ff2038'],['Pink','#ff1493'],['Purple','#a020f0'],['Orange','#ff7900'],['Cyan','#00e5ff']]){
      const button=document.createElement('button');button.type='button';button.title=name;button.setAttribute('aria-label',name);button.style.background=value;button.onclick=()=>color(value);$('me-swatches').append(button);
    }
    $('me-background').oninput=e=>color(e.target.value);
    document.addEventListener('keydown',e=>{if(e.key==='Escape')panel(false);});
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
