/* MB SiteHub - advanced CapCut-style editor tools. Loaded after capcut-core.js. */
(function(){
  if(window.__mbCapcutAdvancedLoaded)return;
  window.__mbCapcutAdvancedLoaded=true;
  const ADV_PROPS=["mbUid","mbName","mbStart","mbDuration","mbBrightness","mbContrast","mbSaturation","mbBlur","mbBorderRadius","mbButtonAction","mbButtonLink","mbVideoMuted","mbVideoLoop","mbVideoAutoplay","mbVideoControls"];
  let videoTick=null;
  const $=id=>document.getElementById(id);
  const canvas=()=>{try{return typeof designCanvas!=="undefined"?designCanvas:window.designCanvas}catch(_){return window.designCanvas}};
  const selected=()=>canvas()?.getActiveObject?.()||null;
  const toast=m=>typeof window.toast==="function"?window.toast(m):console.log(m);
  const uid=()=>"mb"+Date.now().toString(36)+Math.random().toString(36).slice(2,7);
  const isImage=o=>!!o&&o.type==="image";
  const isButton=o=>!!o&&o.assetType==="button";
  const isVideo=o=>!!o&&o.assetType==="video";
  function commit(o){const c=canvas();if(!c)return;if(o?.setCoords)o.setCoords();c.requestRenderAll();try{c.fire("object:modified",{target:o||selected()})}catch(_){}try{window.designSnapshot?.()}catch(_){}setTimeout(refresh,0)}

  function patchSerialization(){if(!window.fabric?.Object||fabric.Object.prototype.__mbAdvancedProps)return;const base=fabric.Object.prototype.toObject;fabric.Object.prototype.toObject=function(extra){const merged=[...(extra||[]),...ADV_PROPS];return base.call(this,[...new Set(merged)])};fabric.Object.prototype.__mbAdvancedProps=true}

  function styles(){if($("mbAdvancedStyle"))return;const s=document.createElement("style");s.id="mbAdvancedStyle";s.textContent=`
    .mb-advanced-section{border-top:1px solid #292e36;padding-top:13px;margin-top:13px}.mb-advanced-section[hidden]{display:none!important}
    .mb-advanced-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.mb-advanced-grid.three{grid-template-columns:repeat(3,1fr)}
    .mb-advanced-note{font-size:10px;color:#7f8792;line-height:1.35;margin:7px 0 0}.mb-advanced-upload{position:relative}
    .mb-advanced-upload input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
    .mb-filter-row{display:grid;grid-template-columns:68px 1fr 38px;gap:6px;align-items:center;margin:7px 0}.mb-filter-row label{font-size:10px;color:#9299a4}.mb-filter-row input{width:100%;margin:0}.mb-filter-row output{text-align:right;font-size:10px;color:#c8ccd2}
    .mb-video-overlay{position:absolute;z-index:24;pointer-events:none;overflow:hidden;background:#050505;border-radius:8px}.mb-video-overlay video{width:100%;height:100%;display:block;object-fit:cover}
    .mb-track-bar{position:relative;transition:margin-left .15s,width .15s}.mb-track-bar::after{content:"";position:absolute;right:0;top:0;bottom:0;width:7px;border-left:1px solid #ffffff55;cursor:ew-resize}
    .mb-link-input{width:100%;height:34px;padding:6px 8px;border-radius:7px;border:1px solid #303640;background:#1a1e24;color:white}
  `;document.head.appendChild(s)}

  async function ownerUpload(kind,file){
    const fd=new FormData();fd.append("kind",kind);fd.append("file",file);
    if(typeof window.api==="function")return window.api("/api/owner/upload",{method:"POST",body:fd});
    const token=localStorage.getItem("owner_token")||"";
    const res=await fetch("/api/owner/upload",{method:"POST",headers:{Authorization:`Bearer ${token}`},body:fd});
    if(!res.ok){let msg="Upload failed.";try{const d=await res.json();msg=d.detail||msg}catch(_){}throw new Error(msg)}
    return res.json();
  }

  function addAdvancedUI(){
    const edit=document.querySelector('.mb-pane[data-pane="edit"]');
    const arrange=document.querySelector('.mb-pane[data-pane="arrange"]');
    const timelineHead=document.querySelector(".mb-timeline-head");
    if(!edit||!arrange||!timelineHead)return false;
    if(!$("mbAdvancedEdit")){
      const sec=document.createElement("div");sec.id="mbAdvancedEdit";sec.className="mb-advanced-section";sec.innerHTML=`
        <p class="mb-title">Layer</p>
        <div class="mb-field"><label>Name</label><input id="mbLayerName" type="text" placeholder="Layer name"></div>
        <div class="mb-field"><label>Start</label><input id="mbLayerStart" type="number" min="0" max="60" step=".1"></div>
        <div class="mb-field"><label>Duration</label><input id="mbLayerDuration2" type="number" min=".2" max="60" step=".1"></div>
        <div class="mb-advanced-grid"><button class="mb-action" id="mbFlipV">Flip V</button><button class="mb-action" id="mbCopyStyle">Copy style</button></div>
        <div id="mbAdvancedImage" class="mb-advanced-section" hidden>
          <p class="mb-title">Crop & image</p>
          <div class="mb-advanced-grid three"><button class="mb-action" data-crop="1">1:1</button><button class="mb-action" data-crop="1.333333">4:3</button><button class="mb-action" data-crop="1.777778">16:9</button></div>
          <div class="mb-advanced-grid" style="margin-top:7px"><button class="mb-action" id="mbCropReset">Reset crop</button><label class="mb-action mb-advanced-upload" style="display:grid;place-items:center">Replace<input id="mbReplaceImage" type="file" accept="image/*"></label></div>
          <div class="mb-filter-row"><label>Brightness</label><input id="mbBrightness" type="range" min="-100" max="100" value="0"><output id="mbBrightnessOut">0</output></div>
          <div class="mb-filter-row"><label>Contrast</label><input id="mbContrast" type="range" min="-100" max="100" value="0"><output id="mbContrastOut">0</output></div>
          <div class="mb-filter-row"><label>Saturation</label><input id="mbSaturation" type="range" min="-100" max="100" value="0"><output id="mbSaturationOut">0</output></div>
          <div class="mb-filter-row"><label>Blur</label><input id="mbBlur" type="range" min="0" max="100" value="0"><output id="mbBlurOut">0</output></div>
          <button class="mb-action" id="mbFiltersReset" style="width:100%">Reset image filters</button>
        </div>
        <div id="mbAdvancedButton" class="mb-advanced-section" hidden>
          <p class="mb-title">Button link</p>
          <div class="mb-field"><label>Action</label><select id="mbButtonAction"><option value="url">Website URL</option><option value="order">Order now</option><option value="menu">Menu</option><option value="call">Call</option><option value="messenger">Messenger</option><option value="facebook">Facebook</option></select></div>
          <input class="mb-link-input" id="mbButtonLink" type="text" placeholder="https://... or phone number">
          <p class="mb-advanced-note">The link is stored with this button so the public page can use it as an interactive action.</p>
        </div>
        <div id="mbAdvancedVideo" class="mb-advanced-section" hidden>
          <p class="mb-title">Video</p>
          <div class="mb-advanced-grid"><button class="mb-action" id="mbVideoPlay">▶ Play</button><button class="mb-action" id="mbVideoPause">⏸ Pause</button></div>
          <div class="mb-advanced-grid" style="margin-top:7px"><button class="mb-action" id="mbVideoMute">Mute</button><button class="mb-action" id="mbVideoLoop">Loop</button></div>
          <div class="mb-advanced-grid" style="margin-top:7px"><button class="mb-action" id="mbVideoAutoplay">Autoplay</button><button class="mb-action" id="mbVideoFit">Fit/Cover</button></div>
        </div>`;
      edit.appendChild(sec);
    }
    if(!$("mbAdvancedArrange")){
      const sec=document.createElement("div");sec.id="mbAdvancedArrange";sec.className="mb-advanced-section";sec.innerHTML=`<p class="mb-title">Group</p><div class="mb-advanced-grid"><button class="mb-action" id="mbGroup">Group selection</button><button class="mb-action" id="mbUngroup">Ungroup</button></div><p class="mb-advanced-note">Shift-click multiple objects on the canvas, then Group selection.</p>`;arrange.appendChild(sec)
    }
    if(!$("mbAddVideo")){
      const b=document.createElement("button");b.className="mb-quick";b.id="mbAddVideo";b.textContent="+ Video";
      const input=document.createElement("input");input.id="mbVideoInput";input.type="file";input.accept="video/mp4,video/webm";input.className="mb-hidden-input";
      timelineHead.insertBefore(b,$("mbPlay")||null);timelineHead.appendChild(input);
    }
    wire();return true;
  }

  function wire(){
    const by=id=>$(id);
    by("mbLayerName").onchange=e=>{const o=selected();if(o){o.mbName=e.target.value.trim();commit(o)}};
    by("mbLayerStart").onchange=e=>{const o=selected();if(o){o.mbStart=Math.max(0,Number(e.target.value)||0);commit(o)}};
    by("mbLayerDuration2").onchange=e=>{const o=selected();if(o){o.mbDuration=Math.max(.2,Number(e.target.value)||4);commit(o)}};
    by("mbFlipV").onclick=()=>{const o=selected();if(o){o.flipY=!o.flipY;commit(o)}};
    by("mbCopyStyle").onclick=copyStyle;
    document.querySelectorAll("[data-crop]").forEach(b=>b.onclick=()=>cropImage(Number(b.dataset.crop)));
    by("mbCropReset").onclick=resetCrop;
    by("mbReplaceImage").onchange=replaceImage;
    [["mbBrightness","mbBrightnessOut","mbBrightness"],["mbContrast","mbContrastOut","mbContrast"],["mbSaturation","mbSaturationOut","mbSaturation"],["mbBlur","mbBlurOut","mbBlur"]].forEach(([id,out,prop])=>{
      by(id).oninput=e=>{by(out).value=e.target.value;const o=selected();if(!isImage(o))return;o[prop]=Number(e.target.value)||0;applyFilters(o,false)};
      by(id).onchange=()=>{const o=selected();if(isImage(o))commit(o)};
    });
    by("mbFiltersReset").onclick=()=>{const o=selected();if(!isImage(o))return;o.mbBrightness=o.mbContrast=o.mbSaturation=o.mbBlur=0;applyFilters(o,true);commit(o)};
    by("mbButtonAction").onchange=e=>{const o=selected();if(isButton(o)){o.mbButtonAction=e.target.value;commit(o)}};
    by("mbButtonLink").onchange=e=>{const o=selected();if(isButton(o)){o.mbButtonLink=e.target.value.trim();o.link=o.mbButtonLink;commit(o)}};
    by("mbGroup").onclick=groupSelection;by("mbUngroup").onclick=ungroupSelection;
    by("mbAddVideo").onclick=()=>by("mbVideoInput").click();by("mbVideoInput").onchange=addVideo;
    by("mbVideoPlay").onclick=()=>videoFor(selected())?.play().catch(()=>{});by("mbVideoPause").onclick=()=>videoFor(selected())?.pause();
    by("mbVideoMute").onclick=()=>toggleVideo("mbVideoMuted");by("mbVideoLoop").onclick=()=>toggleVideo("mbVideoLoop");by("mbVideoAutoplay").onclick=()=>toggleVideo("mbVideoAutoplay");by("mbVideoFit").onclick=()=>{const v=videoFor(selected());if(v){v.dataset.fit=v.dataset.fit==="contain"?"cover":"contain";v.style.objectFit=v.dataset.fit;}}
    const originalImage=$("mbImageInput");if(originalImage&&!originalImage.__mbCloudinary){originalImage.__mbCloudinary=true;originalImage.onchange=addCloudImage}
    const play=$("mbPlay");if(play&&!play.__mbAdvancedPlay){play.__mbAdvancedPlay=true;play.onclick=playAdvancedTimeline}
  }

  let copiedStyle=null;
  function copyStyle(){const o=selected();if(!o)return toast("Select a layer first.");if(copiedStyle){Object.assign(o,copiedStyle);if(isImage(o))applyFilters(o,false);commit(o);copiedStyle=null;toast("Style pasted.");return}copiedStyle={fill:o.fill,stroke:o.stroke,strokeWidth:o.strokeWidth,opacity:o.opacity,shadow:o.shadow,flipX:o.flipX,flipY:o.flipY,fontFamily:o.fontFamily,fontSize:o.fontSize,fontWeight:o.fontWeight,fontStyle:o.fontStyle,textAlign:o.textAlign,mbBrightness:o.mbBrightness||0,mbContrast:o.mbContrast||0,mbSaturation:o.mbSaturation||0,mbBlur:o.mbBlur||0};toast("Style copied. Select another layer and press Copy style again to paste.")}

  function cropImage(ratio){const o=selected();if(!isImage(o))return toast("Select an image first.");const el=o.getElement?.();const sw=el?.naturalWidth||el?.width||o.width,sh=el?.naturalHeight||el?.height||o.height;if(!sw||!sh)return;let w=sw,h=sh;if(sw/sh>ratio)w=sh*ratio;else h=sw/ratio;o.set({cropX:(sw-w)/2,cropY:(sh-h)/2,width:w,height:h});o.setCoords();commit(o)}
  function resetCrop(){const o=selected();if(!isImage(o))return;const el=o.getElement?.();const w=el?.naturalWidth||el?.width;if(!w)return;o.set({cropX:0,cropY:0,width:el.naturalWidth||el.width,height:el.naturalHeight||el.height});o.setCoords();commit(o)}
  function applyFilters(o,reset){if(!isImage(o)||!fabric.Image?.filters)return;if(reset){o.mbBrightness=o.mbContrast=o.mbSaturation=o.mbBlur=0}const f=[];const B=fabric.Image.filters;if(o.mbBrightness&&B.Brightness)f.push(new B.Brightness({brightness:o.mbBrightness/100}));if(o.mbContrast&&B.Contrast)f.push(new B.Contrast({contrast:o.mbContrast/100}));if(o.mbSaturation&&B.Saturation)f.push(new B.Saturation({saturation:o.mbSaturation/100}));if(o.mbBlur&&B.Blur)f.push(new B.Blur({blur:Math.min(1,o.mbBlur/100)}));o.filters=f;o.applyFilters();canvas()?.requestRenderAll()}

  async function replaceImage(e){const file=e.target.files?.[0],o=selected();e.target.value="";if(!file||!isImage(o))return;try{toast("Uploading replacement image…");const data=await ownerUpload("design",file);const url=data.url;if(!url)throw new Error("No upload URL returned.");const w=o.getScaledWidth(),h=o.getScaledHeight(),left=o.left,top=o.top,angle=o.angle,flipX=o.flipX,flipY=o.flipY;o.setSrc(url,()=>{const sx=w/(o.width||1),sy=h/(o.height||1);o.set({left,top,angle,flipX,flipY,scaleX:sx,scaleY:sy});o.setCoords();commit(o);toast("Image replaced.")},{crossOrigin:"anonymous"})}catch(err){toast(err.message||"Image upload failed.")}}
  async function addCloudImage(e){const file=e.target.files?.[0],c=canvas();e.target.value="";if(!file||!c)return;try{toast("Uploading image…");const data=await ownerUpload("design",file);fabric.Image.fromURL(data.url,img=>{const sc=Math.min(500/(img.width||500),300/(img.height||300),1);img.set({left:200,top:100,scaleX:sc,scaleY:sc,crossOrigin:"anonymous"});img.mbDuration=4;img.mbStart=0;img.mbUid=uid();c.add(img);c.setActiveObject(img);commit(img);toast("Image added.")},{crossOrigin:"anonymous"})}catch(err){toast(err.message||"Image upload failed.")}}

  function groupSelection(){const c=canvas(),o=selected();if(!c||!o||o.type!=="activeSelection"||typeof o.toGroup!=="function")return toast("Shift-click two or more layers first.");const g=o.toGroup();g.mbName="Group";g.mbUid=g.mbUid||uid();c.setActiveObject(g);commit(g)}
  function ungroupSelection(){const c=canvas(),o=selected();if(!c||!o||o.type!=="group"||typeof o.toActiveSelection!=="function")return toast("Select a grouped layer first.");const a=o.toActiveSelection();c.setActiveObject(a);commit(a)}

  async function addVideo(e){const file=e.target.files?.[0],c=canvas();e.target.value="";if(!file||!c)return;try{toast("Uploading video…");const data=await ownerUpload("design_video",file);if(!data.url)throw new Error("No video URL returned.");const r=new fabric.Rect({left:240,top:135,width:420,height:236,rx:10,ry:10,fill:"#050505",stroke:"#ff6a1a",strokeWidth:2});r.assetType="video";r.link=data.url;r.mbUid=uid();r.mbName=file.name||"Video";r.mbDuration=8;r.mbStart=0;r.mbVideoMuted=true;r.mbVideoLoop=true;r.mbVideoAutoplay=false;c.add(r);c.setActiveObject(r);commit(r);syncVideos();toast("Video added.")}catch(err){toast(err.message||"Video upload failed.")}}
  function videoFor(o){if(!isVideo(o)||!o.mbUid)return null;return document.querySelector(`.mb-video-overlay[data-uid="${CSS.escape(o.mbUid)}"] video`)}
  function toggleVideo(prop){const o=selected();if(!isVideo(o))return;o[prop]=!o[prop];const v=videoFor(o);if(v){if(prop==="mbVideoMuted")v.muted=!!o[prop];if(prop==="mbVideoLoop")v.loop=!!o[prop];if(prop==="mbVideoAutoplay"&&o[prop])v.play().catch(()=>{});if(prop==="mbVideoAutoplay"&&!o[prop])v.pause()}commit(o)}

  function syncVideos(){const c=canvas(),board=document.querySelector("#designRoom .design-board");if(!c||!board)return;const vids=c.getObjects().filter(isVideo);document.querySelectorAll(".mb-video-overlay").forEach(el=>{if(!vids.some(o=>o.mbUid===el.dataset.uid))el.remove()});vids.forEach(o=>{o.mbUid=o.mbUid||uid();let wrap=document.querySelector(`.mb-video-overlay[data-uid="${CSS.escape(o.mbUid)}"]`);if(!wrap){wrap=document.createElement("div");wrap.className="mb-video-overlay";wrap.dataset.uid=o.mbUid;const v=document.createElement("video");v.src=o.link||"";v.playsInline=true;v.preload="metadata";v.muted=o.mbVideoMuted!==false;v.loop=o.mbVideoLoop!==false;v.autoplay=!!o.mbVideoAutoplay;v.style.objectFit="cover";wrap.appendChild(v);board.appendChild(wrap);if(v.autoplay)v.play().catch(()=>{})}const w=(Number(o.width)||420)*(Number(o.scaleX)||1),h=(Number(o.height)||236)*(Number(o.scaleY)||1);wrap.style.left=`${((Number(o.left)||0)/900)*100}%`;wrap.style.top=`${((Number(o.top)||0)/500)*100}%`;wrap.style.width=`${(w/900)*100}%`;wrap.style.height=`${(h/500)*100}%`;wrap.style.transform=`rotate(${Number(o.angle)||0}deg)`;wrap.style.transformOrigin="center";wrap.style.display=o.visible===false?"none":"block"})}

  function playAdvancedTimeline(){const c=canvas();if(!c)return;const objects=c.getObjects().filter(o=>o.visible!==false),max=Math.max(1,...objects.map(o=>(Number(o.mbStart)||0)+(Number(o.mbDuration)||4)));const playhead=$("mbPlayhead"),timeline=$("mbCapcutTimeline");if(playhead&&timeline){playhead.style.display="block";const start=performance.now();clearInterval(videoTick);videoTick=setInterval(()=>{const t=(performance.now()-start)/1000,k=Math.min(1,t/max);playhead.style.left=`${132+k*Math.max(100,timeline.clientWidth-150)}px`;objects.forEach(o=>{const v=isVideo(o)?videoFor(o):null;if(v&&t>=(Number(o.mbStart)||0)&&t<=(Number(o.mbStart)||0)+(Number(o.mbDuration)||4)&&v.paused)v.play().catch(()=>{});if(v&&t>(Number(o.mbStart)||0)+(Number(o.mbDuration)||4)&&!v.paused)v.pause()});if(k>=1){clearInterval(videoTick);playhead.style.display="none"}},35)}objects.forEach(o=>{if(isVideo(o))return;const start=Math.max(0,Number(o.mbStart)||0)*1000;setTimeout(()=>previewObjectAnimation(o),start)})}
  function previewObjectAnimation(o){const c=canvas();if(!c||!o)return;const n=o.mbAnimation||"none",d=Math.max(.2,Number(o.mbDuration)||1)*1000;if(n==="none")return;const q={left:o.left,top:o.top,scaleX:o.scaleX,scaleY:o.scaleY,opacity:o.opacity??1,angle:o.angle||0};const done=()=>{o.set(q);o.setCoords();c.requestRenderAll()};if(n==="fade"){o.opacity=0;o.animate("opacity",q.opacity,{duration:d,onChange:c.renderAll.bind(c),onComplete:done})}else if(n==="slide"){o.left=q.left-90;o.animate("left",q.left,{duration:d,onChange:c.renderAll.bind(c),onComplete:done})}else if(n==="zoom"||n==="pop"){const k=n==="pop"?.2:.65;o.set({scaleX:q.scaleX*k,scaleY:q.scaleY*k,opacity:n==="zoom"?.25:q.opacity});o.animate("scaleX",q.scaleX,{duration:d,onChange:c.renderAll.bind(c)});o.animate("scaleY",q.scaleY,{duration:d,onChange:c.renderAll.bind(c)});o.animate("opacity",q.opacity,{duration:d,onChange:c.renderAll.bind(c),onComplete:done})}else if(n==="rotate"){o.set({angle:q.angle-45,opacity:.25});o.animate("angle",q.angle,{duration:d,onChange:c.renderAll.bind(c)});o.animate("opacity",q.opacity,{duration:d,onChange:c.renderAll.bind(c),onComplete:done})}}

  function refreshTimelineBars(){const c=canvas(),rows=[...document.querySelectorAll("#mbTracks .mb-track")];if(!c||!rows.length)return;const objs=[...c.getObjects()].reverse(),max=Math.max(12,...objs.map(o=>(Number(o.mbStart)||0)+(Number(o.mbDuration)||4)));rows.forEach((row,i)=>{const o=objs[i],bar=row.querySelector(".mb-track-bar");if(!o||!bar)return;const start=Math.max(0,Number(o.mbStart)||0),dur=Math.max(.2,Number(o.mbDuration)||4);bar.style.width=`${Math.min(100,Math.max(8,dur/max*100))}%`;bar.style.marginLeft=`${Math.min(88,start/max*100)}%`;row.ondblclick=e=>{if(e.target.closest("button"))return;const n=prompt("Layer name",o.mbName||"");if(n!==null){o.mbName=n.trim();commit(o)}}})}

  function refresh(){const o=selected();if(!$("mbAdvancedEdit"))return;const img=$("mbAdvancedImage"),btn=$("mbAdvancedButton"),vid=$("mbAdvancedVideo");img.hidden=!isImage(o);btn.hidden=!isButton(o);vid.hidden=!isVideo(o);if(o){$("mbLayerName").value=o.mbName||"";$("mbLayerStart").value=Number(o.mbStart)||0;$("mbLayerDuration2").value=Number(o.mbDuration)||4;if(isImage(o)){[["mbBrightness","mbBrightnessOut","mbBrightness"],["mbContrast","mbContrastOut","mbContrast"],["mbSaturation","mbSaturationOut","mbSaturation"],["mbBlur","mbBlurOut","mbBlur"]].forEach(([id,out,p])=>{$(id).value=Number(o[p])||0;$(out).value=Number(o[p])||0})}if(isButton(o)){$("mbButtonAction").value=o.mbButtonAction||"url";$("mbButtonLink").value=o.mbButtonLink||o.link||""}if(isVideo(o)){$("mbVideoMute").classList.toggle("active",!!o.mbVideoMuted);$("mbVideoLoop").classList.toggle("active",!!o.mbVideoLoop);$("mbVideoAutoplay").classList.toggle("active",!!o.mbVideoAutoplay)}}syncVideos();refreshTimelineBars()}

  function hookCanvas(){const c=canvas();if(!c)return false;if(c.__mbAdvancedWired)return true;c.__mbAdvancedWired=true;["selection:created","selection:updated","selection:cleared","object:added","object:removed","object:moving","object:scaling","object:rotating","object:modified"].forEach(ev=>c.on(ev,()=>setTimeout(refresh,0)));return true}
  function install(){patchSerialization();styles();if(!addAdvancedUI()){setTimeout(install,250);return}if(!hookCanvas())setTimeout(hookCanvas,300);const mo=new MutationObserver(()=>refreshTimelineBars());const host=$("mbTracks");if(host)mo.observe(host,{childList:true,subtree:true});refresh();setInterval(syncVideos,500)}
  if(document.readyState==="loading")window.addEventListener("DOMContentLoaded",()=>setTimeout(install,500));else setTimeout(install,500);
})();