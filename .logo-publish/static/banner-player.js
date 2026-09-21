/* Shared draft/customer renderer; Fabric.js 5.3.0. */
window.mountBannerPlayer = function(host, banner) {
  host.replaceChildren(); host.style.cssText += ';position:relative;aspect-ratio:9/5;overflow:hidden';
  const element=document.createElement('canvas');host.append(element);
  const canvas=new fabric.StaticCanvas(element,{width:900,height:500,renderOnAddRemove:false});
  element.style.width='100%';element.style.height='100%';
  let stopped=false,index=0,timer,raf,videos=[];
  function clearVideos(){videos.forEach(v=>{v.pause();v.removeAttribute('src');v.load()});videos=[];cancelAnimationFrame(raf);}
  function show(){
    if(stopped || !banner.slides?.length)return;
    clearVideos();
    canvas.loadFromJSON(banner.slides[index],()=>{
      if(stopped)return;
      element.animate([{opacity:0},{opacity:1}],{duration:450});
      canvas.getObjects().slice().forEach((obj,i)=>{
        if(obj.assetType!=='video' || !obj.videoUrl)return;
        const v=document.createElement('video');v.muted=true;v.loop=true;v.playsInline=true;v.src=obj.videoUrl;videos.push(v);
        v.addEventListener('loadeddata',()=>{
          if(stopped || !videos.includes(v))return;
          const image=new fabric.Image(v,{left:obj.left,top:obj.top,angle:obj.angle||0,originX:obj.originX,originY:obj.originY,
            scaleX:obj.width*obj.scaleX/v.videoWidth,scaleY:obj.height*obj.scaleY/v.videoHeight,opacity:obj.opacity,flipX:obj.flipX,flipY:obj.flipY});
          canvas.remove(obj);canvas.insertAt(image,i);v.play().catch(()=>{});
        });
      });
      const draw=()=>{if(stopped)return;canvas.renderAll();raf=requestAnimationFrame(draw)};draw();
      clearTimeout(timer);
      if(banner.slides.length>1)timer=setTimeout(()=>{index=(index+1)%banner.slides.length;show()},Math.max(2,banner.seconds||4)*1000);
    });
  }
  show();
  return {destroy(){stopped=true;clearTimeout(timer);clearVideos();canvas.dispose();host.replaceChildren();}};
};
