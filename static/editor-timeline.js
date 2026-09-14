/* Deterministic editing timeline; leaves the design canvas unchanged during preview. */
(function(){
  const timing=o=>({start:Math.max(0,Number(o.mbStart)||0),duration:Math.max(.2,Number(o.mbDuration)||4),offset:Math.max(0,Number(o.mbMediaOffset)||0)});
  const split=(o,time)=>{const t=timing(o),cut=time-t.start;if(cut<.2||cut>t.duration-.2)return null;return {left:cut,right:t.duration-cut,start:time,offset:t.offset+cut}};
  if(typeof module!=="undefined")module.exports={timing,split};
  if(typeof document==="undefined")return;
  const $=id=>document.getElementById(id), cv=()=>typeof designCanvas!=="undefined"?designCanvas:null;
  let time=0, playing=false, raf=0, preview=null, base=[],media=[],last=0,busy=false;
  const props=["mbStart","mbDuration","mbMediaOffset","mbVolume","mbAnimation","assetType","videoUrl","link","mbName"];
  function duration(){return Math.max(4,...(cv()?.getObjects()||[]).map(o=>{const t=timing(o);return t.start+t.duration}))}
  function changed(o){o?.setCoords();cv().fire("object:modified",{target:o});cv().requestRenderAll();render()}
  function closePreview(){playing=false;cancelAnimationFrame(raf);media.forEach(m=>{m.el.pause();m.el.removeAttribute("src");m.el.load()});media=[];preview?.dispose();preview=null;base=[];if($("mbPlayback").open)$("mbPlayback").close();$("mbRun").textContent="Play"}
  function frame(t){
    time=Math.max(0,Math.min(duration(),t));$("mbSeek").value=time;$("mbTime").textContent=time.toFixed(1)+" / "+duration().toFixed(1)+" s";
    if(!preview)return;
    base.forEach(({o,p})=>{const q=timing(o),active=time>=q.start&&time<q.start+q.duration;const k=Math.min(1,Math.max(0,(time-q.start)/.5));o.set({...p,visible:p.visible!==false&&active});
      if(o.mbAnimation==='fade')o.opacity=p.opacity*k;
      if(o.mbAnimation==='slide')o.left=p.left-70*(1-k);
      if(['zoom','pop'].includes(o.mbAnimation)){o.scaleX=p.scaleX*(.65+.35*k);o.scaleY=p.scaleY*(.65+.35*k)}
      if(o.mbAnimation==='rotate')o.angle=p.angle-35*(1-k);
    });
    media.forEach(m=>{const q=timing(m.o),active=time>=q.start&&time<q.start+q.duration,target=q.offset+Math.max(0,time-q.start);if(Number.isFinite(m.el.duration)&&Math.abs(m.el.currentTime-target)>.2)m.el.currentTime=Math.min(target,Math.max(0,m.el.duration-.01));if(active&&playing)m.el.play().catch(()=>{});else m.el.pause()});
    preview.renderAll();
  }
  function tick(now){if(!playing)return;time+=(now-last)/1000;last=now;if(time>=duration()){playing=false;time=duration();$("mbRun").textContent='Play'}frame(time);if(playing)raf=requestAnimationFrame(tick)}
  function play(){if(!preview)return;playing=!playing;$("mbRun").textContent=playing?'Pause':'Play';cancelAnimationFrame(raf);if(playing){if(time>=duration())time=0;last=performance.now();raf=requestAnimationFrame(tick)}else frame(time)}
  function openPreview(){
    closePreview();$("mbPlayback").showModal();preview=new fabric.StaticCanvas('mbPreviewCanvas',{width:900,height:500});const current=preview;
    preview.loadFromJSON(cv().toJSON(props),()=>{if(preview!==current)return;
      base=preview.getObjects().map(o=>({o,p:{left:o.left,top:o.top,scaleX:o.scaleX,scaleY:o.scaleY,angle:o.angle||0,opacity:o.opacity??1,visible:o.visible}}));
      base.slice().forEach(({o,p},i)=>{if(o.assetType!=='video')return;const el=document.createElement('video');el.src=o.videoUrl||o.link||'';el.muted=o.mbVideoMuted!==false;el.volume=Math.max(0,Math.min(1,Number(o.mbVolume??1)));el.playsInline=true;el.preload='auto';media.push({el,o});el.onloadeddata=()=>{if(preview!==current)return;const im=new fabric.Image(el,{...p,width:el.videoWidth,height:el.videoHeight,scaleX:o.width*p.scaleX/el.videoWidth,scaleY:o.height*p.scaleY/el.videoHeight});props.forEach(k=>im[k]=o[k]);preview.remove(o);preview.insertAt(im,i);base[i]={o:im,p:{...p,scaleX:im.scaleX,scaleY:im.scaleY}};frame(time)};});
      frame(time);
    });
  }
  function render(){if(!cv()||!$('mbTimelineRows'))return;const host=$('mbTimelineRows');host.replaceChildren();$('mbSeek').max=duration();
    cv().getObjects().slice().reverse().forEach(o=>{const t=timing(o),row=document.createElement('div');row.className='mt-row';
      const name=document.createElement('button');name.textContent=o.mbName||o.text||o.assetType||o.type;name.title=name.textContent;name.onclick=()=>{cv().setActiveObject(o);cv().requestRenderAll()};
      const lane=document.createElement('div');lane.className='mt-lane';const bar=document.createElement('button');bar.className='mt-clip';bar.textContent=t.duration.toFixed(1)+'s';bar.title='Drag to move. Shift + drag to trim the end.';bar.style.left=t.start/duration()*100+'%';bar.style.width=t.duration/duration()*100+'%';
      bar.onpointerdown=e=>{if(o.locked||o.lockMovementX)return;e.preventDefault();bar.setPointerCapture(e.pointerId);const x=e.clientX,start=t.start,total=duration(),width=lane.clientWidth,trimming=e.shiftKey;bar.onpointermove=ev=>{if(trimming){o.mbDuration=Math.max(.2,Math.round((t.duration+(ev.clientX-x)/width*total)*10)/10);bar.style.width=o.mbDuration/total*100+'%'}else{o.mbStart=Math.max(0,Math.round((start+(ev.clientX-x)/width*total)*10)/10);bar.style.left=o.mbStart/total*100+'%'}};bar.onpointerup=()=>{bar.onpointermove=null;changed(o)}};
      lane.append(bar);const trim=document.createElement('input');trim.type='number';trim.min='.2';trim.step='.1';trim.value=t.duration;trim.title='Clip duration in seconds';trim.onchange=()=>{if(o.locked)return;o.mbDuration=Math.max(.2,Number(trim.value)||4);changed(o)};row.append(name,lane,trim);host.append(row);
    });frame(time)
  }
  function splitSelected(){const o=cv().getActiveObject();if(!o||o.locked)return;const cut=split(o,time);if(!cut){toast('Place the playhead inside the selected clip.');return;}o.clone(copy=>{o.mbDuration=cut.left;copy.mbStart=cut.start;copy.mbDuration=cut.right;copy.mbMediaOffset=cut.offset;copy.mbUid='clip'+Date.now();cv().add(copy);cv().setActiveObject(copy);changed(copy)},props)}
  async function save(publish){if(busy)return;busy=true;try{const json=cv().toJSON(props),custom={...owner.custom_design,editorDraft:json};if(publish){custom.canvas=json;custom.enabled=true;}owner=await api('/api/owner/site',{method:'PATCH',body:JSON.stringify({custom_design:custom})});toast(publish?'Design published.':'Draft saved. Live design unchanged.',true)}catch(e){toast(e.message)}finally{busy=false}}
  function install(){if(!$('mbAdvancedEdit')||!$('mbCapcutTimeline')||!cv()){setTimeout(install,300);return;}
    const style=document.createElement('style');style.textContent=`/* Duplicate actions are hidden only outside the original left toolbar. */
#mbCapcutToolbar #mbUndo,#mbCapcutToolbar #mbRedo,#mbCapcutToolbar #mbSave,#mbCapcutToolbar #mbPreview,
#mbCapcutTimeline #mbAddText,#mbCapcutTimeline #mbAddShape,#mbCapcutTimeline #mbAddImage,#mbCapcutTimeline #mbAddVideo,#mbCapcutTimeline #mbBackground,
#mbCapcutInspector [data-act="front"],#mbCapcutInspector #mbResetFilter{display:none!important}
#mbTracks,#mbCapcutTimeline>.mb-ruler,#mbPlayhead{display:none!important}.mt-row{display:grid;grid-template-columns:110px 1fr 65px;gap:8px;align-items:center;margin:6px}.mt-row button{color:#ddd;background:#232933;border:0;border-radius:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;height:26px}.mt-lane{position:relative;height:28px;background:#171b23}.mt-clip{position:absolute;background:#365c83!important;touch-action:none;cursor:grab}.mt-row input{width:65px;padding:3px}#mbTimelineRows{max-height:125px;overflow:auto}#mbPlayback{width:min(1000px,94vw);background:#15191f;color:white;border:1px solid #555;border-radius:12px}#mbPreviewCanvas{width:100%!important;height:auto!important}#mbCapcutTimeline{overflow:auto}.mb-preview-mode .mb-video-overlay{display:none}`;document.head.append(style);
    const head=document.createElement('div');head.style.cssText='display:flex;gap:10px;align-items:center;padding:6px';head.innerHTML='<button class="mb-quick" id="mbSplit">Split clip</button><label>Playhead <input id="mbSeek" type="range" min="0" step=".05" value="0"></label><span id="mbTime"></span>';
    const rows=document.createElement('div');rows.id='mbTimelineRows';$('mbCapcutTimeline').append(head,rows);
    const dialog=document.createElement('dialog');dialog.id='mbPlayback';dialog.innerHTML='<button id="mbClosePlayback">Back to editor</button> <button id="mbRun">Play</button><input id="mbPreviewSeek" aria-label="Preview playhead" type="range" min="0" step=".05" value="0" style="width:100%"><canvas id="mbPreviewCanvas"></canvas>';document.body.append(dialog);dialog.oncancel=closePreview;$('mbClosePlayback').onclick=closePreview;$('mbRun').onclick=play;
    $('mbPreviewSeek').oninput=e=>frame(Number(e.target.value));$('mbSeek').oninput=e=>frame(Number(e.target.value));$('mbSplit').onclick=splitSelected;$('mbPlay').onclick=openPreview;$('mbPreview').onclick=openPreview;
    $('mbSave').textContent='Save Draft';$('mbSave').onclick=()=>save(false);$('mbPublish').onclick=()=>save(true);
    ['object:added','object:removed','object:modified'].forEach(event=>cv().on(event,()=>{if(!preview)render()}));
    const volume=document.createElement('label');volume.textContent='Video volume ';const slider=document.createElement('input');slider.type='range';slider.min=0;slider.max=1;slider.step=.05;slider.value=1;slider.onchange=()=>{const o=cv().getActiveObject();if(o?.assetType==='video'&&!o.locked){o.mbVolume=Number(slider.value);o.mbVideoMuted=o.mbVolume===0;changed(o)}};volume.append(slider);head.append(volume);
    const original=fabric.Object.prototype.toObject;fabric.Object.prototype.toObject=function(extra){return original.call(this,[...new Set([...(extra||[]),...props])])};
    render();
  }
  setTimeout(install,600);
})();
