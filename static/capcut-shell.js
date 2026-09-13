/* MB Business Hub - CapCut-inspired visual page editor. Uses the existing Fabric.js canvas and save flow. */
(function () {
  const STYLE_ID = "mb-capcut-shell-style";
  const ROOT_CLASS = "mb-capcut-shell";
  const EXTRA_PROPS = ["assetType","mbAnimation","mbDuration","mbName","link","locked","hiddenByEditor"];
  let history = [];
  let historyIndex = -1;
  let restoring = false;
  let clipboard = null;
  let zoom = 1;
  let timelineTimer = null;

  function activeCanvas() {
    try { return typeof designCanvas !== "undefined" ? designCanvas : window.designCanvas; }
    catch (_) { return window.designCanvas; }
  }

  function toast(message) {
    if (typeof window.toast === "function") window.toast(message);
    else console.log(message);
  }

  function safeText(value) {
    return String(value ?? "").replace(/[&<>\"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]));
  }

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      body.${ROOT_CLASS}{--mb-rail:76px;--mb-panel:286px;--mb-inspector:310px;--mb-timeline:220px;background:#0b0d10}
      body.${ROOT_CLASS} .design-room{background:#0b0d10;grid-template-rows:68px minmax(0,1fr)}
      body.${ROOT_CLASS} .design-top{min-height:68px;padding:0 12px;gap:7px;flex-wrap:nowrap;background:#101216;border-bottom:1px solid #262a31;box-shadow:0 3px 18px #0005;overflow-x:auto}
      body.${ROOT_CLASS} .design-top::before{content:"MB BUSINESS HUB";flex:0 0 auto;margin-right:10px;color:#f4f4f5;font-weight:900;letter-spacing:.02em;font-size:15px}
      body.${ROOT_CLASS} .design-top .btn{min-height:36px;padding:7px 11px;border-radius:9px;background:#15181d;border-color:#2c313a;font-size:.78rem;white-space:nowrap}
      body.${ROOT_CLASS} .design-top .btn:hover{background:#20242a;border-color:#464c56}
      body.${ROOT_CLASS} .design-work{position:relative;grid-template-columns:var(--mb-rail) 0 minmax(0,1fr) var(--mb-inspector);grid-template-rows:minmax(0,1fr) var(--mb-timeline);background:#0b0d10}
      body.${ROOT_CLASS} .design-work.tool-panel-open{grid-template-columns:var(--mb-rail) var(--mb-panel) minmax(0,1fr) var(--mb-inspector)}
      body.${ROOT_CLASS} .tool-rail{grid-column:1;grid-row:1 / span 2;width:var(--mb-rail);padding:10px 7px;gap:7px;background:#101216;border-right:1px solid #262a31}
      body.${ROOT_CLASS} .tool-icon{width:54px;height:48px;border-radius:10px;padding:12px;position:relative}
      body.${ROOT_CLASS} .tool-icon img{width:21px;height:21px}
      body.${ROOT_CLASS} .tool-panel{grid-column:2;grid-row:1 / span 2;width:var(--mb-panel);background:#12151a;border-right:1px solid #292e36}
      body.${ROOT_CLASS} .tool-panel-header{min-height:54px;padding:11px 12px 11px 16px;background:#15181d}
      body.${ROOT_CLASS} #editorToolContents{padding:14px}
      body.${ROOT_CLASS} .design-work>.design-board-wrap{grid-column:3;grid-row:1;padding:34px;align-content:center;justify-content:center;overflow:auto;background:linear-gradient(#ffffff05 1px,transparent 1px),linear-gradient(90deg,#ffffff05 1px,transparent 1px),#0c0f13;background-size:24px 24px}
      body.${ROOT_CLASS} .design-board{box-shadow:0 22px 70px #000c,0 0 0 1px #3b4048;border-radius:2px;overflow:visible;transform-origin:center center;transition:transform .15s ease}
      body.${ROOT_CLASS}.mb-preview-mode .tool-rail,body.${ROOT_CLASS}.mb-preview-mode .tool-panel,body.${ROOT_CLASS}.mb-preview-mode .mb-capcut-inspector,body.${ROOT_CLASS}.mb-preview-mode .mb-capcut-timeline{opacity:.12;pointer-events:none}
      body.${ROOT_CLASS}.mb-preview-mode .design-work{grid-template-columns:0 0 minmax(0,1fr) 0;grid-template-rows:minmax(0,1fr) 0}
      .mb-capcut-toolbar{display:flex;align-items:center;gap:6px;margin-left:auto;flex:0 0 auto}
      .mb-capcut-toolbar button,.mb-capcut-toolbar select{height:34px;border:1px solid #303640;border-radius:8px;background:#181c22;color:#eef0f3;padding:0 9px;font:700 11px Outfit,Arial;cursor:pointer}
      .mb-capcut-toolbar button.primary{background:#ff6a1a;border-color:#ff6a1a;color:#fff}
      .mb-capcut-inspector{grid-column:4;grid-row:1 / span 2;min-width:0;background:#12151a;border-left:1px solid #292e36;display:flex;flex-direction:column;overflow:hidden}
      .mb-capcut-tabs{display:grid;grid-template-columns:repeat(3,1fr);min-height:52px;border-bottom:1px solid #292e36;background:#15181d}
      .mb-capcut-tabs button{border:0;background:transparent;color:#a8adb6;font:700 12px Outfit,Arial;cursor:pointer}
      .mb-capcut-tabs button.active{color:#fff;box-shadow:inset 0 -2px #ff6a1a}
      .mb-capcut-inspector-body{padding:14px;overflow:auto}
      .mb-pane{display:none}.mb-pane.active{display:block}
      .mb-capcut-inspector h4{margin:0 0 12px;font-size:14px}
      .mb-capcut-field{display:grid;grid-template-columns:56px 1fr;gap:7px;align-items:center;margin-bottom:9px}
      .mb-capcut-field label{margin:0;color:#8f96a1;font-size:11px}
      .mb-capcut-field input,.mb-capcut-field select{margin:0;min-width:0;height:34px;padding:6px 8px;border-radius:7px;border:1px solid #303640;background:#1a1e24;color:#fff}
      .mb-row{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:8px}
      .mb-row.three{grid-template-columns:repeat(3,1fr)}
      .mb-action{min-height:34px;border:1px solid #343a44;background:#181c22;color:#e8eaed;border-radius:8px;cursor:pointer;font-size:11px;font-weight:700}
      .mb-action:hover,.mb-action.active{border-color:#ff6a1a99;background:#ff6a1a18}
      .mb-section{border-top:1px solid #292e36;padding-top:13px;margin-top:13px}
      .mb-section-title{color:#9ca3af;font:700 10px Outfit,Arial;text-transform:uppercase;letter-spacing:.08em;margin:0 0 9px}
      .mb-capcut-object-tools{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:13px}
      .mb-capcut-timeline{grid-column:3;grid-row:2;min-width:0;background:#0f1216;border-top:1px solid #292e36;overflow:hidden;display:flex;flex-direction:column}
      .mb-capcut-timeline-head{height:48px;display:flex;align-items:center;gap:7px;padding:0 10px;border-bottom:1px solid #252a32;overflow-x:auto}
      .mb-capcut-timeline-head strong{font-size:12px;margin-right:4px;white-space:nowrap}.mb-capcut-timeline-head span{color:#858c97;font-size:11px;white-space:nowrap}
      .mb-quick-add{height:30px;padding:0 9px;border:1px solid #343a44;border-radius:7px;background:#181c22;color:#eef0f3;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap}
      .mb-quick-add:hover{border-color:#ff6a1a88}
      .mb-ruler{height:24px;display:grid;grid-template-columns:repeat(9,1fr);align-items:end;padding:0 12px 3px 132px;border-bottom:1px solid #20252c;color:#606773;font-size:9px;position:relative}
      .mb-ruler i{font-style:normal;border-left:1px solid #343a44;padding-left:3px}
      .mb-playhead{position:absolute;top:48px;bottom:0;width:2px;background:#ff6a1a;z-index:5;pointer-events:none;left:132px;display:none}.mb-playhead::before{content:"";position:absolute;top:0;left:-4px;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid #ff6a1a}
      .mb-capcut-tracks{overflow:auto;padding:8px 10px 12px}
      .mb-capcut-track{display:grid;grid-template-columns:116px minmax(0,1fr) 58px;align-items:center;gap:7px;min-height:31px;margin-bottom:5px}
      .mb-capcut-track-label{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:#c7cbd2;font-size:11px;cursor:grab}.mb-capcut-track-label small{opacity:.55}
      .mb-capcut-track-bar{height:24px;border-radius:6px;background:linear-gradient(90deg,#315dca,#4379ef);border:1px solid #72a0ff66;cursor:pointer;min-width:24px;transition:opacity .15s}
      .mb-capcut-track[data-type="text"] .mb-capcut-track-bar{background:linear-gradient(90deg,#7447bd,#9b66eb)}
      .mb-capcut-track[data-type="slideshow"] .mb-capcut-track-bar{background:linear-gradient(90deg,#1e7bc1,#36a7e8)}
      .mb-capcut-track[data-type="image"] .mb-capcut-track-bar{background:linear-gradient(90deg,#188b6a,#30b98f)}
      .mb-capcut-track[data-type="button"] .mb-capcut-track-bar{background:linear-gradient(90deg,#c96a20,#ed9148)}
      .mb-capcut-track.selected .mb-capcut-track-bar{box-shadow:0 0 0 2px #ff8a4a}
      .mb-layer-actions{display:flex;gap:3px}.mb-layer-actions button{width:26px;height:25px;padding:0;border:1px solid #303640;border-radius:5px;background:#171b20;color:#aaa;cursor:pointer;font-size:11px}
      .mb-capcut-empty{color:#727985;font-size:12px;padding:12px}
      .mb-upload-hidden{display:none!important}
      .mb-animation-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}
      .mb-animation-grid button{min-height:40px}
      .mb-snap-guide{position:absolute;z-index:80;pointer-events:none;background:#ff4fa3;display:none}.mb-snap-guide.v{top:0;bottom:0;width:1px;left:50%}.mb-snap-guide.h{left:0;right:0;height:1px;top:50%}
      body.${ROOT_CLASS} .design-slideshow{top:76px;left:calc(var(--mb-rail) + 10px);width:var(--mb-panel);border-color:#383e47;background:#12151a;z-index:90}
      @media(max-width:1180px){body.${ROOT_CLASS}{--mb-inspector:260px;--mb-panel:250px}}
      @media(max-width:900px){body.${ROOT_CLASS}{--mb-inspector:0px}.mb-capcut-inspector{display:none}body.${ROOT_CLASS} .design-work,body.${ROOT_CLASS} .design-work.tool-panel-open{grid-template-columns:56px 0 minmax(0,1fr)}body.${ROOT_CLASS} .tool-rail{width:56px}.mb-capcut-timeline{grid-column:3}}
    `;
    document.head.appendChild(style);
  }

  function objectName(object, index) {
    if (!object) return "Layer";
    if (object.mbName) return object.mbName;
    if (object.assetType === "slideshow") return "Slideshow";
    if (object.assetType === "video") return "Video";
    if (object.assetType === "button") return "Button";
    if (["textbox","text","i-text"].includes(object.type)) {
      const text = String(object.text || "Text").trim();
      return text.length > 22 ? text.slice(0,22)+"…" : text || "Text";
    }
    if (object.type === "image") return "Image";
    return `${String(object.type || "Layer").replace(/^./,c=>c.toUpperCase())} ${index+1}`;
  }

  function canvasJSON() {
    const canvas = activeCanvas();
    if (!canvas) return "";
    return JSON.stringify(canvas.toJSON(EXTRA_PROPS));
  }

  function snapshot(force) {
    if (restoring) return;
    const json = canvasJSON();
    if (!json || (!force && history[historyIndex] === json)) return;
    history = history.slice(0, historyIndex + 1);
    history.push(json);
    if (history.length > 60) history.shift();
    historyIndex = history.length - 1;
    updateToolbarState();
    if (typeof window.designSnapshot === "function") {
      try { window.designSnapshot(); } catch (_) {}
    }
  }

  function restore(index) {
    const canvas = activeCanvas();
    if (!canvas || index < 0 || index >= history.length) return;
    restoring = true;
    canvas.loadFromJSON(history[index], () => {
      historyIndex = index;
      canvas.requestRenderAll();
      restoring = false;
      refreshAll();
      updateToolbarState();
    });
  }

  function undo() { if (historyIndex > 0) restore(historyIndex - 1); }
  function redo() { if (historyIndex < history.length - 1) restore(historyIndex + 1); }

  function createTopToolbar() {
    const top = document.querySelector("#designRoom .design-top");
    if (!top || document.getElementById("mbCapcutToolbar")) return;
    const bar = document.createElement("div");
    bar.id = "mbCapcutToolbar";
    bar.className = "mb-capcut-toolbar";
    bar.innerHTML = `
      <button id="mbUndo" title="Undo (Ctrl+Z)">↶ Undo</button>
      <button id="mbRedo" title="Redo (Ctrl+Y)">↷ Redo</button>
      <button id="mbPreview">Preview</button>
      <select id="mbZoom" title="Canvas zoom"><option value="0.5">50%</option><option value="0.75">75%</option><option value="1" selected>100%</option><option value="1.25">125%</option><option value="1.5">150%</option><option value="2">200%</option></select>
      <button id="mbSave">Save</button>
      <button class="primary" id="mbPublish">Publish</button>`;
    top.appendChild(bar);
    document.getElementById("mbUndo").onclick = undo;
    document.getElementById("mbRedo").onclick = redo;
    document.getElementById("mbPreview").onclick = togglePreview;
    document.getElementById("mbZoom").onchange = e => setZoom(Number(e.target.value));
    document.getElementById("mbSave").onclick = () => triggerExistingAction(/save/i, "Save");
    document.getElementById("mbPublish").onclick = () => triggerExistingAction(/publish/i, "Publish");
  }

  function triggerExistingAction(regex, label) {
    const candidates = [...document.querySelectorAll("#designRoom .design-top button,.studio-panel button,#editorToolContents button")]
      .filter(el => !el.closest("#mbCapcutToolbar") && regex.test((el.textContent||"").trim()));
    if (candidates[0]) { candidates[0].click(); return; }
    const names = label === "Save" ? ["saveCustomDesign","saveDesign","saveSiteDesign"] : ["publishSite","publishDesign","publishPage"];
    for (const name of names) if (typeof window[name] === "function") { window[name](); return; }
    toast(`${label} uses the existing page action. Open the matching page panel if needed.`);
  }

  function togglePreview() {
    const on = !document.body.classList.contains("mb-preview-mode");
    document.body.classList.toggle("mb-preview-mode", on);
    const canvas = activeCanvas();
    if (on) canvas?.discardActiveObject?.();
    canvas?.requestRenderAll?.();
    const button = document.getElementById("mbPreview");
    if (button) button.textContent = on ? "Exit Preview" : "Preview";
  }

  function setZoom(value) {
    zoom = Number.isFinite(value) ? value : 1;
    const board = document.querySelector("#designRoom .design-board");
    if (board) board.style.transform = `scale(${zoom})`;
  }

  function updateToolbarState() {
    const u = document.getElementById("mbUndo"), r = document.getElementById("mbRedo");
    if (u) u.disabled = historyIndex <= 0;
    if (r) r.disabled = historyIndex >= history.length - 1;
  }

  function createInspector(work) {
    if (document.getElementById("mbCapcutInspector")) return;
    const aside = document.createElement("aside");
    aside.id = "mbCapcutInspector";
    aside.className = "mb-capcut-inspector";
    aside.innerHTML = `
      <div class="mb-capcut-tabs">
        <button type="button" class="active" data-pane="edit">Edit</button>
        <button type="button" data-pane="animate">Animate</button>
        <button type="button" data-pane="arrange">Arrange</button>
      </div>
      <div class="mb-capcut-inspector-body">
        <div class="mb-capcut-object-tools">
          <button class="mb-action" data-action="duplicate">Duplicate</button>
          <button class="mb-action" data-action="delete">Delete</button>
          <button class="mb-action" data-action="front">Front</button>
        </div>
        <h4 id="mbInspectorTitle">No layer selected</h4>
        <section class="mb-pane active" data-pane-body="edit">
          <div class="mb-capcut-field"><label>X</label><input id="mbPropX" type="number"></div>
          <div class="mb-capcut-field"><label>Y</label><input id="mbPropY" type="number"></div>
          <div class="mb-capcut-field"><label>Width</label><input id="mbPropW" type="number" min="1"></div>
          <div class="mb-capcut-field"><label>Height</label><input id="mbPropH" type="number" min="1"></div>
          <div class="mb-capcut-field"><label>Rotate</label><input id="mbPropAngle" type="number"></div>
          <div class="mb-capcut-field"><label>Opacity</label><input id="mbPropOpacity" type="range" min="0" max="100" value="100"></div>
          <div id="mbTextTools" class="mb-section">
            <p class="mb-section-title">Text</p>
            <div class="mb-capcut-field"><label>Font</label><select id="mbFont"><option>Arial</option><option>Georgia</option><option>Impact</option><option>Verdana</option><option>Trebuchet MS</option><option>Courier New</option></select></div>
            <div class="mb-capcut-field"><label>Size</label><input id="mbFontSize" type="number" min="8" max="180"></div>
            <div class="mb-row three"><button class="mb-action" id="mbBold">Bold</button><button class="mb-action" id="mbItalic">Italic</button><button class="mb-action" id="mbTextCenter">Center</button></div>
          </div>
          <div class="mb-section"><p class="mb-section-title">Style</p>
            <div class="mb-capcut-field"><label>Fill</label><input id="mbFill" type="color" value="#ffffff"></div>
            <div class="mb-capcut-field"><label>Outline</label><input id="mbStroke" type="color" value="#000000"></div>
            <div class="mb-capcut-field"><label>Width</label><input id="mbStrokeWidth" type="number" min="0" max="30" value="0"></div>
            <div class="mb-row"><button class="mb-action" id="mbShadow">Shadow</button><button class="mb-action" id="mbFlipX">Flip H</button></div>
          </div>
          <div id="mbImageTools" class="mb-section"><p class="mb-section-title">Image</p><div class="mb-row"><button class="mb-action" id="mbGray">B&W</button><button class="mb-action" id="mbResetFilter">Reset filter</button></div></div>
        </section>
        <section class="mb-pane" data-pane-body="animate">
          <p class="mb-section-title">Animation</p>
          <div class="mb-animation-grid" id="mbAnimationGrid">
            <button class="mb-action" data-animation="none">None</button><button class="mb-action" data-animation="fade">Fade</button>
            <button class="mb-action" data-animation="slide">Slide</button><button class="mb-action" data-animation="zoom">Zoom</button>
            <button class="mb-action" data-animation="pop">Pop</button><button class="mb-action" data-animation="rotate">Rotate</button>
          </div>
          <div class="mb-capcut-field" style="margin-top:12px"><label>Duration</label><input id="mbAnimDuration" type="number" min="0.2" max="15" step="0.1" value="1"></div>
          <button class="mb-action" id="mbPreviewAnimation" style="width:100%">▶ Preview animation</button>
        </section>
        <section class="mb-pane" data-pane-body="arrange">
          <p class="mb-section-title">Layer order</p>
          <div class="mb-row"><button class="mb-action" data-arrange="front">To front</button><button class="mb-action" data-arrange="back">To back</button></div>
          <div class="mb-row"><button class="mb-action" data-arrange="forward">Forward</button><button class="mb-action" data-arrange="backward">Backward</button></div>
          <p class="mb-section-title">Align</p>
          <div class="mb-row three"><button class="mb-action" data-align="left">Left</button><button class="mb-action" data-align="center">Center</button><button class="mb-action" data-align="right">Right</button></div>
          <div class="mb-row"><button class="mb-action" data-align="top">Top</button><button class="mb-action" data-align="middle">Middle</button></div>
          <div class="mb-section"><div class="mb-row"><button class="mb-action" id="mbLock">Lock</button><button class="mb-action" id="mbHide">Hide</button></div></div>
        </section>
      </div>`;
    work.appendChild(aside);
    wireInspector();
  }

  function selected() { return activeCanvas()?.getActiveObject?.() || null; }
  function commit() { activeCanvas()?.requestRenderAll?.(); snapshot(); refreshAll(); }

  function wireInspector() {
    const aside = document.getElementById("mbCapcutInspector");
    aside.querySelectorAll(".mb-capcut-tabs button").forEach(btn => btn.onclick = () => {
      aside.querySelectorAll(".mb-capcut-tabs button").forEach(b=>b.classList.toggle("active",b===btn));
      aside.querySelectorAll(".mb-pane").forEach(p=>p.classList.toggle("active",p.dataset.paneBody===btn.dataset.pane));
    });
    aside.querySelector('[data-action="delete"]').onclick = deleteSelected;
    aside.querySelector('[data-action="duplicate"]').onclick = duplicateSelected;
    aside.querySelector('[data-action="front"]').onclick = () => arrange("front");

    [["mbPropX","left"],["mbPropY","top"],["mbPropAngle","angle"]].forEach(([id,key])=>{
      document.getElementById(id).onchange=e=>{const o=selected();if(!o)return;o.set(key,Number(e.target.value)||0);o.setCoords();commit();};
    });
    document.getElementById("mbPropW").onchange=e=>resizeSelected("width",Number(e.target.value));
    document.getElementById("mbPropH").onchange=e=>resizeSelected("height",Number(e.target.value));
    document.getElementById("mbPropOpacity").oninput=e=>{const o=selected();if(!o)return;o.set("opacity",Number(e.target.value)/100);activeCanvas().requestRenderAll();};
    document.getElementById("mbPropOpacity").onchange=snapshot;
    document.getElementById("mbFill").oninput=e=>{const o=selected();if(!o)return;o.set("fill",e.target.value);activeCanvas().requestRenderAll();};
    document.getElementById("mbFill").onchange=snapshot;
    document.getElementById("mbStroke").oninput=e=>{const o=selected();if(!o)return;o.set("stroke",e.target.value);activeCanvas().requestRenderAll();};
    document.getElementById("mbStroke").onchange=snapshot;
    document.getElementById("mbStrokeWidth").onchange=e=>{const o=selected();if(!o)return;o.set("strokeWidth",Number(e.target.value)||0);commit();};
    document.getElementById("mbFont").onchange=e=>{const o=selected();if(!isText(o))return;o.set("fontFamily",e.target.value);commit();};
    document.getElementById("mbFontSize").onchange=e=>{const o=selected();if(!isText(o))return;o.set("fontSize",Number(e.target.value)||16);commit();};
    document.getElementById("mbBold").onclick=()=>{const o=selected();if(!isText(o))return;o.set("fontWeight",o.fontWeight==="bold"?"normal":"bold");commit();};
    document.getElementById("mbItalic").onclick=()=>{const o=selected();if(!isText(o))return;o.set("fontStyle",o.fontStyle==="italic"?"normal":"italic");commit();};
    document.getElementById("mbTextCenter").onclick=()=>{const o=selected();if(!isText(o))return;o.set("textAlign","center");commit();};
    document.getElementById("mbFlipX").onclick=()=>{const o=selected();if(!o)return;o.set("flipX",!o.flipX);commit();};
    document.getElementById("mbShadow").onclick=()=>{const o=selected();if(!o)return;o.set("shadow",o.shadow?null:new fabric.Shadow({color:"rgba(0,0,0,.45)",blur:14,offsetX:4,offsetY:6}));commit();};
    document.getElementById("mbGray").onclick=()=>applyGray(true);
    document.getElementById("mbResetFilter").onclick=()=>applyGray(false);
    document.querySelectorAll("[data-animation]").forEach(btn=>btn.onclick=()=>setAnimation(btn.dataset.animation));
    document.getElementById("mbAnimDuration").onchange=e=>{const o=selected();if(!o)return;o.mbDuration=Math.max(.2,Number(e.target.value)||1);commit();};
    document.getElementById("mbPreviewAnimation").onclick=()=>previewAnimation(selected());
    document.querySelectorAll("[data-arrange]").forEach(btn=>btn.onclick=()=>arrange(btn.dataset.arrange));
    document.querySelectorAll("[data-align]").forEach(btn=>btn.onclick=()=>alignSelected(btn.dataset.align));
    document.getElementById("mbLock").onclick=toggleLock;
    document.getElementById("mbHide").onclick=toggleHide;
  }

  function isText(o) { return !!o && ["textbox","text","i-text"].includes(o.type); }
  function resizeSelected(axis,target){const o=selected();if(!o||!Number.isFinite(target)||target<=0)return;const base=Number(o[axis])||1;o.set(axis==="width"?"scaleX":"scaleY",target/base);o.setCoords();commit();}
  function deleteSelected(){const c=activeCanvas(),o=selected();if(!c||!o)return;c.remove(o);c.discardActiveObject();commit();}
  function duplicateSelected(){const c=activeCanvas(),o=selected();if(!c||!o||typeof o.clone!=="function")return;o.clone(clone=>{clone.set({left:(Number(o.left)||0)+24,top:(Number(o.top)||0)+24});c.add(clone);c.setActiveObject(clone);commit();});}

  function arrange(action){const c=activeCanvas(),o=selected();if(!c||!o)return;if(action==="front")c.bringToFront(o);if(action==="back")c.sendToBack(o);if(action==="forward")c.bringForward(o);if(action==="backward")c.sendBackwards(o);commit();}
  function alignSelected(where){const c=activeCanvas(),o=selected();if(!c||!o)return;const w=o.getScaledWidth(),h=o.getScaledHeight();if(where==="left")o.set("left",0);if(where==="center")o.set("left",(900-w)/2);if(where==="right")o.set("left",900-w);if(where==="top")o.set("top",0);if(where==="middle")o.set("top",(500-h)/2);o.setCoords();commit();}
  function toggleLock(){const o=selected();if(!o)return;const locked=!o.locked;o.locked=locked;o.set({lockMovementX:locked,lockMovementY:locked,lockScalingX:locked,lockScalingY:locked,lockRotation:locked});commit();}
  function toggleHide(){const c=activeCanvas(),o=selected();if(!c||!o)return;o.hiddenByEditor=!o.hiddenByEditor;o.set("visible",!o.hiddenByEditor);c.discardActiveObject();commit();}

  function applyGray(on){const o=selected();if(!o||o.type!=="image"||!fabric.Image?.filters)return;o.filters=on?[new fabric.Image.filters.Grayscale()]:[];o.applyFilters();commit();}

  function setAnimation(name){const o=selected();if(!o)return;o.mbAnimation=name;o.mbDuration=o.mbDuration||1;document.querySelectorAll("[data-animation]").forEach(b=>b.classList.toggle("active",b.dataset.animation===name));snapshot();previewAnimation(o);refreshTimeline();}
  function previewAnimation(o){const c=activeCanvas();if(!c||!o)return;const name=o.mbAnimation||"none",duration=(Number(o.mbDuration)||1)*1000;if(name==="none"){c.requestRenderAll();return;}const original={left:o.left,top:o.top,scaleX:o.scaleX,scaleY:o.scaleY,opacity:o.opacity??1,angle:o.angle||0};const done=()=>{o.set(original);o.setCoords();c.requestRenderAll();};if(name==="fade"){o.set("opacity",0);o.animate("opacity",original.opacity,{duration,onChange:c.renderAll.bind(c),onComplete:done});}else if(name==="slide"){o.set("left",original.left-90);o.animate("left",original.left,{duration,easing:fabric.util.ease.easeOutCubic,onChange:c.renderAll.bind(c),onComplete:done});}else if(name==="zoom"){o.set({scaleX:original.scaleX*.65,scaleY:original.scaleY*.65,opacity:.2});o.animate("scaleX",original.scaleX,{duration,onChange:c.renderAll.bind(c)});o.animate("scaleY",original.scaleY,{duration,onChange:c.renderAll.bind(c)});o.animate("opacity",original.opacity,{duration,onChange:c.renderAll.bind(c),onComplete:done});}else if(name==="pop"){o.set({scaleX:original.scaleX*.2,scaleY:original.scaleY*.2});o.animate("scaleX",original.scaleX,{duration,easing:fabric.util.ease.easeOutBack,onChange:c.renderAll.bind(c)});o.animate("scaleY",original.scaleY,{duration,easing:fabric.util.ease.easeOutBack,onChange:c.renderAll.bind(c),onComplete:done});}else if(name==="rotate"){o.set({angle:original.angle-45,opacity:.25});o.animate("angle",original.angle,{duration,onChange:c.renderAll.bind(c)});o.animate("opacity",original.opacity,{duration,onChange:c.renderAll.bind(c),onComplete:done});}}

  function createTimeline(work){
    if(document.getElementById("mbCapcutTimeline"))return;
    const timeline=document.createElement("section");timeline.id="mbCapcutTimeline";timeline.className="mb-capcut-timeline";
    timeline.innerHTML=`<div class="mb-capcut-timeline-head"><strong>Timeline / Layers</strong><button class="mb-quick-add" id="mbAddText">+ Text</button><button class="mb-quick-add" id="mbAddRect">+ Shape</button><button class="mb-quick-add" id="mbAddButton">+ Button</button><button class="mb-quick-add" id="mbAddImage">+ Image</button><button class="mb-quick-add" id="mbPlayTimeline">▶ Play</button><button class="mb-quick-add" id="mbBgColor">Background</button><input class="mb-upload-hidden" id="mbImageInput" type="file" accept="image/*"><input class="mb-upload-hidden" id="mbBgInput" type="color" value="#ffffff"></div><div class="mb-ruler">${Array.from({length:9},(_,i)=>`<i>${i*2}s</i>`).join("")}</div><div class="mb-playhead" id="mbPlayhead"></div><div class="mb-capcut-tracks" id="mbCapcutTracks"></div>`;
    work.appendChild(timeline);
    document.getElementById("mbAddText").onclick=addText;
    document.getElementById("mbAddRect").onclick=addShape;
    document.getElementById("mbAddButton").onclick=addButton;
    document.getElementById("mbAddImage").onclick=()=>document.getElementById("mbImageInput").click();
    document.getElementById("mbImageInput").onchange=uploadLocalImage;
    document.getElementById("mbPlayTimeline").onclick=playTimeline;
    document.getElementById("mbBgColor").onclick=()=>document.getElementById("mbBgInput").click();
    document.getElementById("mbBgInput").oninput=e=>{const c=activeCanvas();if(!c)return;c.setBackgroundColor(e.target.value,c.renderAll.bind(c));};
    document.getElementById("mbBgInput").onchange=snapshot;
  }

  function addText(){const c=activeCanvas();if(!c)return;const o=new fabric.Textbox("Add your text",{left:250,top:180,width:400,fontSize:42,fontFamily:"Arial",fontWeight:"bold",fill:"#ffffff",textAlign:"center"});o.mbDuration=4;c.add(o);c.setActiveObject(o);commit();}
  function addShape(){const c=activeCanvas();if(!c)return;const o=new fabric.Rect({left:315,top:180,width:270,height:140,rx:18,ry:18,fill:"#ff6a1a"});o.mbDuration=4;c.add(o);c.setActiveObject(o);commit();}
  function addButton(){const c=activeCanvas();if(!c)return;const rect=new fabric.Rect({width:210,height:58,rx:29,ry:29,fill:"#ff6a1a",originX:"center",originY:"center"});const text=new fabric.Text("ORDER NOW",{fontSize:20,fontWeight:"bold",fill:"#fff",originX:"center",originY:"center"});const group=new fabric.Group([rect,text],{left:345,top:300});group.assetType="button";group.mbName="Order Button";group.mbDuration=4;c.add(group);c.setActiveObject(group);commit();}
  function uploadLocalImage(e){const file=e.target.files?.[0],c=activeCanvas();if(!file||!c)return;const reader=new FileReader();reader.onload=()=>fabric.Image.fromURL(reader.result,img=>{const maxW=500,maxH=300;const scale=Math.min(maxW/img.width,maxH/img.height,1);img.set({left:200,top:100,scaleX:scale,scaleY:scale});img.mbDuration=4;c.add(img);c.setActiveObject(img);commit();});reader.readAsDataURL(file);e.target.value="";}

  function playTimeline(){const c=activeCanvas();if(!c)return;clearInterval(timelineTimer);const objects=c.getObjects().filter(o=>o.visible!==false);objects.forEach((o,i)=>setTimeout(()=>previewAnimation(o),i*180));const head=document.querySelector(".mb-capcut-timeline"),playhead=document.getElementById("mbPlayhead");if(!head||!playhead)return;playhead.style.display="block";let start=performance.now(),total=8000;timelineTimer=setInterval(()=>{const p=Math.min(1,(performance.now()-start)/total);const left=132+p*Math.max(100,head.clientWidth-150);playhead.style.left=`${left}px`;if(p>=1){clearInterval(timelineTimer);playhead.style.display="none";}},30);}

  function refreshInspector(){const c=activeCanvas(),o=selected(),title=document.getElementById("mbInspectorTitle");if(!title)return;const ids=["mbPropX","mbPropY","mbPropW","mbPropH","mbPropAngle","mbPropOpacity","mbFill","mbStroke","mbStrokeWidth","mbAnimDuration"];ids.forEach(id=>{const el=document.getElementById(id);if(el)el.disabled=!o;});if(!o){title.textContent="No layer selected";return;}const list=c.getObjects();title.textContent=objectName(o,Math.max(0,list.indexOf(o)));document.getElementById("mbPropX").value=Math.round(Number(o.left)||0);document.getElementById("mbPropY").value=Math.round(Number(o.top)||0);document.getElementById("mbPropW").value=Math.round(o.getScaledWidth?.()||0);document.getElementById("mbPropH").value=Math.round(o.getScaledHeight?.()||0);document.getElementById("mbPropAngle").value=Math.round(Number(o.angle)||0);document.getElementById("mbPropOpacity").value=Math.round((o.opacity??1)*100);document.getElementById("mbStrokeWidth").value=Number(o.strokeWidth)||0;document.getElementById("mbAnimDuration").value=Number(o.mbDuration)||1;document.getElementById("mbTextTools").style.display=isText(o)?"block":"none";document.getElementById("mbImageTools").style.display=o.type==="image"?"block":"none";if(isText(o)){document.getElementById("mbFont").value=o.fontFamily||"Arial";document.getElementById("mbFontSize").value=Math.round(Number(o.fontSize)||16);}document.querySelectorAll("[data-animation]").forEach(b=>b.classList.toggle("active",b.dataset.animation===(o.mbAnimation||"none")));document.getElementById("mbLock").textContent=o.locked?"Unlock":"Lock";document.getElementById("mbHide").textContent=o.visible===false?"Show":"Hide";}

  function refreshTimeline(){const c=activeCanvas(),host=document.getElementById("mbCapcutTracks");if(!host||!c)return;const objects=c.getObjects(),sel=selected();if(!objects.length){host.innerHTML='<div class="mb-capcut-empty">Add text, images, slideshow, video, shapes, or buttons to build your page.</div>';return;}host.innerHTML="";[...objects].reverse().forEach((o,ri)=>{const idx=objects.length-1-ri,row=document.createElement("div");row.className="mb-capcut-track"+(o===sel?" selected":"");row.dataset.type=o.assetType||o.type||"layer";row.draggable=true;const duration=Math.max(.2,Number(o.mbDuration)||4);row.innerHTML=`<span class="mb-capcut-track-label">${safeText(objectName(o,idx))} <small>${duration.toFixed(1)}s</small></span><div class="mb-capcut-track-bar" style="width:${Math.min(100,Math.max(18,duration/12*100))}%;opacity:${o.visible===false?.28:1}"></div><span class="mb-layer-actions"><button data-layer="visible" title="Show/hide">${o.visible===false?"○":"●"}</button><button data-layer="lock" title="Lock">${o.locked?"🔒":"🔓"}</button></span>`;row.onclick=e=>{if(e.target.closest("button"))return;c.setActiveObject(o);o.setCoords();c.requestRenderAll();refreshAll();};row.querySelector('[data-layer="visible"]').onclick=e=>{e.stopPropagation();o.hiddenByEditor=!o.hiddenByEditor;o.visible=!o.hiddenByEditor;commit();};row.querySelector('[data-layer="lock"]').onclick=e=>{e.stopPropagation();c.setActiveObject(o);toggleLock();};row.ondragstart=e=>e.dataTransfer.setData("text/plain",String(idx));row.ondragover=e=>e.preventDefault();row.ondrop=e=>{e.preventDefault();const from=Number(e.dataTransfer.getData("text/plain"));if(Number.isNaN(from))return;c.moveTo(objects[from],idx);commit();};host.appendChild(row);});}

  function refreshAll(){refreshInspector();refreshTimeline();updateToolbarState();}

  function snapObject(e){const o=e.target;if(!o||o.locked)return;const threshold=7,w=o.getScaledWidth(),h=o.getScaledHeight(),cx=(Number(o.left)||0)+w/2,cy=(Number(o.top)||0)+h/2;let sv=false,sh=false;if(Math.abs(cx-450)<threshold){o.set("left",450-w/2);sv=true;}if(Math.abs(cy-250)<threshold){o.set("top",250-h/2);sh=true;}const board=document.querySelector("#designRoom .design-board");if(board){let v=board.querySelector(".mb-snap-guide.v"),hline=board.querySelector(".mb-snap-guide.h");if(!v){v=document.createElement("i");v.className="mb-snap-guide v";board.appendChild(v);}if(!hline){hline=document.createElement("i");hline.className="mb-snap-guide h";board.appendChild(hline);}v.style.display=sv?"block":"none";hline.style.display=sh?"block":"none";}}
  function hideGuides(){document.querySelectorAll(".mb-snap-guide").forEach(el=>el.style.display="none");}

  function wireCanvas(){const c=activeCanvas();if(!c||c.__mbCapcutWired)return false;c.__mbCapcutWired=true;c.on("selection:created",refreshAll);c.on("selection:updated",refreshAll);c.on("selection:cleared",refreshAll);c.on("object:added",()=>{if(!restoring){refreshAll();}});c.on("object:removed",()=>{if(!restoring){refreshAll();}});c.on("object:moving",snapObject);c.on("object:modified",()=>{hideGuides();snapshot();refreshAll();});c.on("object:scaling",refreshInspector);c.on("object:rotating",refreshInspector);setTimeout(()=>snapshot(true),200);refreshAll();return true;}

  function wireKeyboard(){if(document.body.dataset.mbCapcutKeys)return;document.body.dataset.mbCapcutKeys="1";document.addEventListener("keydown",e=>{const tag=e.target?.tagName;if(["INPUT","TEXTAREA","SELECT"].includes(tag)||e.target?.isContentEditable)return;const mod=e.ctrlKey||e.metaKey;if(mod&&e.key.toLowerCase()==="z"){e.preventDefault();e.shiftKey?redo():undo();return;}if(mod&&e.key.toLowerCase()==="y"){e.preventDefault();redo();return;}if(mod&&e.key.toLowerCase()==="c"){const o=selected();if(o?.clone)o.clone(x=>clipboard=x);return;}if(mod&&e.key.toLowerCase()==="v"){if(!clipboard?.clone)return;clipboard.clone(x=>{x.set({left:(Number(x.left)||0)+20,top:(Number(x.top)||0)+20});activeCanvas().add(x);activeCanvas().setActiveObject(x);clipboard=x;commit();});return;}if(e.key==="Delete"||e.key==="Backspace"){deleteSelected();return;}const o=selected();if(!o)return;const step=e.shiftKey?10:1;if(e.key==="ArrowLeft")o.left-=step;else if(e.key==="ArrowRight")o.left+=step;else if(e.key==="ArrowUp")o.top-=step;else if(e.key==="ArrowDown")o.top+=step;else return;e.preventDefault();o.setCoords();activeCanvas().requestRenderAll();});document.addEventListener("keyup",e=>{if(["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(e.key)&&selected())snapshot();});}

  function install(){const room=document.getElementById("designRoom"),work=room?.querySelector(".design-work");if(!room||!work){setTimeout(install,250);return;}document.body.classList.add(ROOT_CLASS);injectStyles();createTopToolbar();createInspector(work);createTimeline(work);wireKeyboard();if(!wireCanvas())setTimeout(wireCanvas,400);const timer=setInterval(()=>{if(wireCanvas())clearInterval(timer);},500);}
  window.addEventListener("load",()=>setTimeout(install,250));
})();