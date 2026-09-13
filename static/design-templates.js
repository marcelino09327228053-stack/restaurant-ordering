/* Local, editable Fabric.js restaurant banner templates. */
window.restaurantTemplates = [
  {id:"cafe", name:"Cozy Coffee", description:"Warm cream · espresso · café", bg:"#eee1cc"},
  {id:"grill", name:"Fire & Grill", description:"Charcoal · orange · bold", bg:"#151515"},
  {id:"coastal", name:"Coastal Kitchen", description:"Ocean blue · white · fresh", bg:"#eaf6f5"},
  {id:"bakery", name:"Sweet Bakery", description:"Blush · burgundy · soft", bg:"#f8e7e1"},
  {id:"garden", name:"Garden Table", description:"Sage · cream · organic", bg:"#edf0df"},
  {id:"diner", name:"Retro Diner", description:"Red · butter yellow · playful", bg:"#fff0c6"},
  {id:"noodle", name:"Noodle House", description:"Ink · vermilion · minimal", bg:"#f4eee4"},
  {id:"night", name:"Midnight Dining", description:"Navy · gold · elegant", bg:"#101c30"},
  {id:"market", name:"Market Brunch", description:"Lilac · citrus · modern", bg:"#ece6fa"}
];
window.buildRestaurantTemplate = function(id, restaurant, tagline) {
  const objects=[];
  const rect=(x,y,w,h,fill,extra={})=>objects.push(new fabric.Rect({left:x,top:y,width:w,height:h,fill,...extra}));
  const circle=(x,y,r,fill,extra={})=>objects.push(new fabric.Circle({left:x,top:y,radius:r,fill,...extra}));
  const text=(value,x,y,w,size,fill,extra={})=>objects.push(new fabric.Textbox(value,{left:x,top:y,width:w,fontSize:size,fill,fontFamily:"Arial",fontWeight:"bold",splitByGrapheme:false,...extra}));
  const title=(x,y,w,size,color,font="Georgia",align="left")=>text(restaurant.toUpperCase(),x,y,w,size,color,{fontFamily:font,textAlign:align,lineHeight:1.03});
  const caption=(x,y,w,color,align="left")=>text(tagline || "Good food, made with care.",x,y,w,17,color,{fontWeight:"normal",textAlign:align});
  const plate=(x,y,r,color)=>{circle(x,y,r,color);circle(x+15,y+15,r-15,"transparent",{stroke:"#ffffff",strokeWidth:2,opacity:.7});};
  switch(id) {
    case "cafe":
      rect(0,0,350,500,"#563a2b");circle(58,108,118,"#bc9268");
      rect(93,177,133,98,"#fff4df",{rx:18,ry:18});circle(203,186,36,"transparent",{stroke:"#fff4df",strokeWidth:14});
      rect(82,285,171,9,"#fff4df",{rx:5,ry:5});
      text("COFFEE & CONVERSATION",402,65,435,17,"#79573c");title(402,120,435,45,"#39291f");
      caption(405,285,415,"#695343");rect(405,374,200,48,"#563a2b",{rx:24,ry:24});text("BREWED WITH LOVE",420,390,180,14,"#fff4df");break;
    case "grill":
      objects.push(new fabric.Polygon([{x:590,y:0},{x:900,y:0},{x:900,y:500},{x:450,y:500}],{fill:"#ed6029"}));
      text("HOT OFF THE GRILL",55,50,455,18,"#ffad57");title(55,101,450,53,"#ffffff","Impact");caption(58,286,395,"#d6d6d6");
      rect(58,372,260,52,"#ed6029");text("BIG FLAVOUR. EVERY DAY.",72,390,242,15,"#ffffff");
      plate(588,130,119,"#202020");text("FIRE\n& FEAST",602,188,213,42,"#ffffff",{textAlign:"center",fontFamily:"Impact"});break;
    case "coastal":
      rect(0,0,900,104,"#126d84");text("FRESH FROM THE COAST",55,40,780,24,"#ffffff",{charSpacing:90});
      title(58,147,510,45,"#174c5c");caption(60,295,465,"#426b76");
      plate(635,156,96,"#80c4ca");
      objects.push(new fabric.Path("M0 425Q150 380 300 425T600 425T900 425L900 500H0Z",{fill:"#126d84"}));
      text("SEAFOOD · SEASONAL · LOCAL",60,449,730,18,"#ffffff");break;
    case "bakery":
      rect(42,35,816,430,"#fff8f1",{rx:100,ry:100});
      circle(50,36,35,"#dd9e9d");circle(780,381,35,"#dd9e9d");
      text("BAKED FRESH EVERY MORNING",150,81,600,16,"#94535c",{textAlign:"center",charSpacing:100});
      title(150,145,600,47,"#713b49","Georgia","center");caption(170,305,560,"#94535c","center");
      rect(330,384,240,42,"#713b49",{rx:21,ry:21});text("A LITTLE MOMENT OF JOY",346,398,209,13,"#fff8f1",{textAlign:"center"});break;
    case "garden":
      rect(565,0,335,500,"#315b44");
      for(let i=0;i<4;i++)objects.push(new fabric.Ellipse({left:605+i*35,top:65+i*76,rx:65,ry:27,fill:i%2?"#a6bd7d":"#d3ddaa",angle:i%2?35:-30}));
      text("ROOTED IN GOODNESS",55,60,455,17,"#62805a");title(55,127,450,46,"#244531");caption(58,294,415,"#54714c");
      rect(58,393,340,3,"#709363");text("SEASONAL PLATES · FRESH INGREDIENTS",58,416,450,13,"#315b44");break;
    case "diner":
      for(let i=0;i<18;i++){rect(i*50,0,50,28,i%2?"#bd3635":"#fff0c6");rect(i*50,472,50,28,i%2?"#fff0c6":"#bd3635");}
      rect(45,65,810,365,"transparent",{stroke:"#bd3635",strokeWidth:4,rx:24,ry:24});
      text("WELCOME, HUNGRY FRIENDS",110,95,680,20,"#bd3635",{textAlign:"center"});title(100,155,700,54,"#bd3635","Impact","center");
      caption(160,319,580,"#614b38","center");text("BURGERS   •   SHAKES   •   GOOD TIMES",150,379,600,18,"#bd3635",{textAlign:"center"});break;
    case "noodle":
      rect(45,45,10,410,"#cf4432");text("HANDCRAFTED & HEARTWARMING",90,65,455,15,"#cf4432");title(90,130,410,46,"#232323");caption(93,298,380,"#62605a");
      circle(594,75,127,"#cf4432");
      objects.push(new fabric.Path("M600 236H838Q820 357 719 357Q618 357 600 236Z",{fill:"#232323"}));
      rect(660,359,115,12,"#232323",{rx:5,ry:5});
      rect(633,164,205,7,"#f4eee4",{angle:-14});rect(639,185,205,7,"#f4eee4",{angle:-14});
      text("SLOW BROTH. FULL FLAVOUR.",90,410,580,18,"#cf4432");break;
    case "night":
      rect(30,30,840,440,"transparent",{stroke:"#b69b64",strokeWidth:2});rect(45,45,810,410,"transparent",{stroke:"#b69b64",strokeWidth:1});
      text("AN EVENING TO REMEMBER",180,89,540,15,"#ccb98c",{textAlign:"center",charSpacing:130});
      title(135,157,630,48,"#f7f0df","Georgia","center");caption(190,319,520,"#ccb98c","center");
      rect(345,390,210,2,"#b69b64");circle(438,57,11,"#b69b64");break;
    case "market":
      rect(0,0,900,45,"#412f67");rect(565,45,335,455,"#d8ec65");
      circle(617,107,106,"#ece6fa");circle(666,156,57,"#412f67");
      text("YOUR NEW FAVOURITE SPOT",55,83,465,17,"#79619f");title(55,142,455,47,"#412f67","Arial");caption(58,318,420,"#6c568e");
      text("BRUNCH\nALL DAY",606,352,250,37,"#412f67",{textAlign:"center"});rect(58,420,320,4,"#412f67");break;
  }
  // Keep long restaurant names and descriptions inside their allotted rows.
  for(const object of objects)if(object.type==="textbox"){
    const limit=object.fontSize>=37?150:65;
    while(object.height>limit && object.fontSize>12){object.set("fontSize",object.fontSize-1);}
  }
  return objects;
};

/* Slideshow editor preview controls. Keeps the saved Fabric box as the source of position/size. */
(function () {
  let timer = null;
  let index = 0;
  let installed = false;

  function heroes() {
    try {
      const images = (typeof owner !== "undefined" && Array.isArray(owner?.hero_images)) ? owner.hero_images : [];
      return images.filter(Boolean);
    } catch (_) {
      return [];
    }
  }

  function slideshowObject() {
    try {
      const canvas = typeof designCanvas !== "undefined" ? designCanvas : window.designCanvas;
      return canvas?.getObjects?.().find(object => object.assetType === "slideshow") || null;
    } catch (_) {
      return window.designCanvas?.getObjects?.().find(object => object.assetType === "slideshow") || null;
    }
  }

  function overlay() {
    const board = document.querySelector(".design-board");
    if (!board) return null;
    let el = document.getElementById("mbSlideshowEditorPreview");
    if (!el) {
      el = document.createElement("div");
      el.id = "mbSlideshowEditorPreview";
      el.style.cssText = "position:absolute;overflow:hidden;border-radius:12px;background:#111;pointer-events:none;z-index:20;box-shadow:inset 0 0 0 2px #f97316;";
      board.appendChild(el);
    }
    return el;
  }

  function syncOverlay() {
    const el = overlay();
    const object = slideshowObject();
    if (!el || !object) {
      if (el) el.hidden = true;
      return;
    }
    el.hidden = false;
    const width = (Number(object.width) || 560) * (Number(object.scaleX) || 1);
    const height = (Number(object.height) || 250) * (Number(object.scaleY) || 1);
    el.style.left = `${((Number(object.left) || 0) / 900) * 100}%`;
    el.style.top = `${((Number(object.top) || 0) / 500) * 100}%`;
    el.style.width = `${(width / 900) * 100}%`;
    el.style.height = `${(height / 500) * 100}%`;
    el.style.transform = `rotate(${Number(object.angle) || 0}deg)`;
    el.style.transformOrigin = "center";
  }

  function show(target) {
    const list = heroes();
    const el = overlay();
    if (!el) return;
    syncOverlay();
    if (!list.length) {
      el.innerHTML = '<div style="height:100%;display:grid;place-items:center;padding:18px;text-align:center;color:#fdba74;font:700 16px Arial">Upload slideshow photos first</div>';
      updateStatus();
      return;
    }
    index = (target + list.length) % list.length;
    el.innerHTML = `<img src="${list[index]}" alt="" style="width:100%;height:100%;object-fit:cover;display:block">`;
    updateStatus();
  }

  function stop() {
    clearInterval(timer);
    timer = null;
    updateStatus();
  }

  function play() {
    const list = heroes();
    if (!list.length) {
      if (typeof window.toast === "function") window.toast("Upload slideshow photos first.");
      show(0);
      return;
    }
    stop();
    show(index);
    if (list.length > 1) timer = setInterval(() => show(index + 1), 3200);
    updateStatus();
  }

  function previous() {
    stop();
    show(index - 1);
  }

  function next() {
    stop();
    show(index + 1);
  }

  function updateStatus() {
    const status = document.getElementById("mbSlideshowPreviewStatus");
    if (!status) return;
    const list = heroes();
    status.textContent = list.length ? `${index + 1} / ${list.length} · ${timer ? "Playing" : "Paused"}` : "No photos yet";
  }

  function installControls() {
    const panel = document.getElementById("slideshowPanel");
    if (!panel || document.getElementById("mbSlideshowPreviewControls")) return;
    const controls = document.createElement("div");
    controls.id = "mbSlideshowPreviewControls";
    controls.style.cssText = "display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:12px 0 8px";
    controls.innerHTML = `
      <button class="btn" type="button" id="mbSlidePrev">◀ Prev</button>
      <button class="btn solid" type="button" id="mbSlidePlay">▶ Play</button>
      <button class="btn" type="button" id="mbSlidePause">⏸ Pause</button>
      <button class="btn" type="button" id="mbSlideNext">Next ▶</button>`;
    const status = document.createElement("p");
    status.id = "mbSlideshowPreviewStatus";
    status.className = "hint";
    status.style.marginTop = "0";
    const saveButton = panel.querySelector('button[onclick="saveSlideshowStyle()"]');
    panel.insertBefore(controls, saveButton || null);
    panel.insertBefore(status, saveButton || null);
    document.getElementById("mbSlidePrev").onclick = previous;
    document.getElementById("mbSlidePlay").onclick = play;
    document.getElementById("mbSlidePause").onclick = stop;
    document.getElementById("mbSlideNext").onclick = next;
    updateStatus();
  }

  function activeDesignCanvas() {
    try { return typeof designCanvas !== "undefined" ? designCanvas : window.designCanvas; } catch (_) { return window.designCanvas; }
  }

  function install() {
    if (installed) return;
    const canvas = activeDesignCanvas();
    if (!canvas || typeof window.ensureSlideshowDesignBox !== "function") {
      setTimeout(install, 250);
      return;
    }
    installed = true;
    installControls();
    canvas.on("object:moving", syncOverlay);
    canvas.on("object:scaling", syncOverlay);
    canvas.on("object:rotating", syncOverlay);
    canvas.on("object:modified", syncOverlay);
    canvas.on("object:added", syncOverlay);
    canvas.on("object:removed", syncOverlay);

    const currentOpen = window.openEditorTool;
    window.openEditorTool = function (id, force) {
      const result = currentOpen(id, force);
      if (id === "slideshow") {
        setTimeout(() => {
          installControls();
          window.ensureSlideshowDesignBox();
          syncOverlay();
          show(index);
        }, 0);
      }
      return result;
    };

    const currentRenderHeroThumbs = window.renderHeroThumbs;
    if (typeof currentRenderHeroThumbs === "function") {
      window.renderHeroThumbs = function () {
        const result = currentRenderHeroThumbs();
        setTimeout(() => {
          installControls();
          index = Math.min(index, Math.max(0, heroes().length - 1));
          show(index);
        }, 0);
        return result;
      };
    }

    const currentSelectStyle = window.selectSlideshowStyle;
    if (typeof currentSelectStyle === "function") {
      window.selectSlideshowStyle = function (style) {
        const result = currentSelectStyle(style);
        show(index);
        return result;
      };
    }

    syncOverlay();
  }

  window.addEventListener("load", () => setTimeout(install, 700));
})();

/* Load the CapCut-style shell as a separate, easy-to-edit module. */
(function () {
  const script = document.createElement("script");
  script.src = "/static/capcut-shell.js?v=20260913a";
  script.defer = true;
  document.head.appendChild(script);
})();
