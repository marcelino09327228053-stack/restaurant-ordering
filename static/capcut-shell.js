/* CapCut-inspired MB Business Hub editor shell. Preserves existing Fabric editor behavior. */
(function () {
  const STYLE_ID = "mb-capcut-shell-style";
  const ROOT_CLASS = "mb-capcut-shell";

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      body.${ROOT_CLASS} { --mb-rail:76px; --mb-panel:286px; --mb-inspector:300px; --mb-timeline:188px; }
      body.${ROOT_CLASS} .design-room { background:#0b0d10; grid-template-rows:68px minmax(0,1fr); }
      body.${ROOT_CLASS} .design-top {
        min-height:68px; padding:0 14px; gap:8px; flex-wrap:nowrap;
        background:#101216; border-bottom:1px solid #262a31; box-shadow:0 3px 18px #0005;
      }
      body.${ROOT_CLASS} .design-top::before {
        content:"MB BUSINESS HUB"; flex:0 0 auto; margin-right:14px; color:#f4f4f5;
        font-weight:900; letter-spacing:.02em; font-size:15px;
      }
      body.${ROOT_CLASS} .design-top::after {
        content:"Design Your Page"; order:-1; display:none;
      }
      body.${ROOT_CLASS} .design-top .btn {
        min-height:36px; padding:7px 11px; border-radius:9px; background:#15181d;
        border-color:#2c313a; font-size:.78rem;
      }
      body.${ROOT_CLASS} .design-top .btn:hover { background:#20242a; border-color:#464c56; }
      body.${ROOT_CLASS} .design-top .btn[aria-pressed="true"],
      body.${ROOT_CLASS} .design-top .btn[aria-expanded="true"] { background:#ff6a1a22; border-color:#ff6a1a99; color:#ffd2ba; }
      body.${ROOT_CLASS} .design-work {
        position:relative;
        grid-template-columns:var(--mb-rail) 0 minmax(0,1fr) var(--mb-inspector);
        grid-template-rows:minmax(0,1fr) var(--mb-timeline);
        background:#0b0d10;
      }
      body.${ROOT_CLASS} .design-work.tool-panel-open {
        grid-template-columns:var(--mb-rail) var(--mb-panel) minmax(0,1fr) var(--mb-inspector);
      }
      body.${ROOT_CLASS} .tool-rail {
        grid-column:1; grid-row:1 / span 2; width:var(--mb-rail); padding:10px 7px; gap:7px;
        background:#101216; border-right:1px solid #262a31;
      }
      body.${ROOT_CLASS} .tool-icon { width:54px; height:48px; border-radius:10px; padding:12px; position:relative; }
      body.${ROOT_CLASS} .tool-icon img { width:21px; height:21px; }
      body.${ROOT_CLASS} .tool-panel {
        grid-column:2; grid-row:1 / span 2; width:var(--mb-panel); background:#12151a;
        border-right:1px solid #292e36;
      }
      body.${ROOT_CLASS} .tool-panel-header { min-height:54px; padding:11px 12px 11px 16px; background:#15181d; }
      body.${ROOT_CLASS} .tool-panel-header h3 { font-size:.92rem; }
      body.${ROOT_CLASS} #editorToolContents { padding:14px; }
      body.${ROOT_CLASS} .design-work > .design-board-wrap {
        grid-column:3; grid-row:1; padding:26px; align-content:center; justify-content:center;
        background:
          linear-gradient(#ffffff05 1px,transparent 1px),
          linear-gradient(90deg,#ffffff05 1px,transparent 1px),
          #0c0f13;
        background-size:24px 24px;
      }
      body.${ROOT_CLASS} .design-board {
        box-shadow:0 22px 70px #000c,0 0 0 1px #3b4048;
        border-radius:2px; overflow:visible;
      }
      body.${ROOT_CLASS} .studio-panel,
      body.${ROOT_CLASS} .design-slideshow { z-index:35; }
      .mb-capcut-inspector {
        grid-column:4; grid-row:1 / span 2; min-width:0; background:#12151a;
        border-left:1px solid #292e36; display:flex; flex-direction:column; overflow:hidden;
      }
      .mb-capcut-tabs { display:grid; grid-template-columns:repeat(3,1fr); min-height:52px; border-bottom:1px solid #292e36; background:#15181d; }
      .mb-capcut-tabs button { border:0; background:transparent; color:#a8adb6; font:700 12px Outfit,Arial; cursor:pointer; }
      .mb-capcut-tabs button.active { color:#fff; box-shadow:inset 0 -2px #ff6a1a; }
      .mb-capcut-inspector-body { padding:16px; overflow:auto; }
      .mb-capcut-inspector h4 { margin:0 0 14px; font-size:14px; }
      .mb-capcut-field { display:grid; grid-template-columns:34px 1fr; gap:7px; align-items:center; margin-bottom:9px; }
      .mb-capcut-field label { margin:0; color:#8f96a1; font-size:11px; }
      .mb-capcut-field input { margin:0; min-width:0; height:34px; padding:7px 9px; border-radius:7px; border:1px solid #303640; background:#1a1e24; }
      .mb-capcut-group { border-top:1px solid #292e36; padding-top:14px; margin-top:14px; }
      .mb-capcut-actions { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
      .mb-capcut-actions button { min-height:35px; border:1px solid #343a44; border-radius:8px; background:#1a1e24; color:#eef0f3; font-weight:700; cursor:pointer; }
      .mb-capcut-actions button:hover { border-color:#ff6a1a88; }
      .mb-capcut-timeline {
        grid-column:3; grid-row:2; min-width:0; background:#0f1216; border-top:1px solid #292e36;
        overflow:hidden; display:flex; flex-direction:column;
      }
      .mb-capcut-timeline-head { height:42px; display:flex; align-items:center; gap:8px; padding:0 12px; border-bottom:1px solid #252a32; }
      .mb-capcut-timeline-head strong { font-size:12px; }
      .mb-capcut-timeline-head span { color:#858c97; font-size:11px; }
      .mb-capcut-tracks { overflow:auto; padding:8px 10px 12px; }
      .mb-capcut-track { display:grid; grid-template-columns:120px minmax(0,1fr); align-items:center; gap:8px; min-height:30px; margin-bottom:5px; }
      .mb-capcut-track-label { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; color:#c7cbd2; font-size:11px; }
      .mb-capcut-track-bar { height:24px; border-radius:6px; background:linear-gradient(90deg,#315dca,#4379ef); border:1px solid #72a0ff66; cursor:pointer; min-width:24px; }
      .mb-capcut-track[data-type="text"] .mb-capcut-track-bar { background:linear-gradient(90deg,#7447bd,#9b66eb); }
      .mb-capcut-track[data-type="slideshow"] .mb-capcut-track-bar { background:linear-gradient(90deg,#1e7bc1,#36a7e8); }
      .mb-capcut-track[data-type="image"] .mb-capcut-track-bar { background:linear-gradient(90deg,#188b6a,#30b98f); }
      .mb-capcut-track.selected .mb-capcut-track-bar { box-shadow:0 0 0 2px #ff8a4a; }
      .mb-capcut-empty { color:#727985; font-size:12px; padding:12px; }
      .mb-capcut-object-tools { display:flex; gap:6px; margin-bottom:14px; }
      .mb-capcut-object-tools button { flex:1; min-height:34px; border:1px solid #343a44; background:#181c22; color:#e8eaed; border-radius:8px; cursor:pointer; font-size:11px; font-weight:700; }
      .mb-capcut-object-tools button:hover { border-color:#ff6a1a88; }
      body.${ROOT_CLASS} .design-slideshow {
        top:76px; left:calc(var(--mb-rail) + 10px); width:var(--mb-panel); border-color:#383e47; background:#12151a;
      }
      @media (max-width:1180px) {
        body.${ROOT_CLASS} { --mb-inspector:250px; --mb-panel:250px; }
      }
      @media (max-width:900px) {
        body.${ROOT_CLASS} { --mb-inspector:0px; }
        .mb-capcut-inspector { display:none; }
        body.${ROOT_CLASS} .design-work,
        body.${ROOT_CLASS} .design-work.tool-panel-open { grid-template-columns:56px 0 minmax(0,1fr); }
        body.${ROOT_CLASS} .tool-rail { width:56px; }
        body.${ROOT_CLASS} .tool-icon { width:42px; height:42px; }
        .mb-capcut-timeline { grid-column:3; }
      }
    `;
    document.head.appendChild(style);
  }

  function objectName(object, index) {
    if (!object) return "Layer";
    if (object.assetType === "slideshow") return "Slideshow";
    if (object.assetType === "video") return "Video";
    if (object.type === "textbox" || object.type === "text" || object.type === "i-text") {
      const text = String(object.text || "Text").trim();
      return text.length > 22 ? text.slice(0, 22) + "…" : text || "Text";
    }
    if (object.type === "image") return "Image";
    return `${String(object.type || "Layer").replace(/^./, c => c.toUpperCase())} ${index + 1}`;
  }

  function activeCanvas() {
    try { return typeof designCanvas !== "undefined" ? designCanvas : window.designCanvas; } catch (_) { return window.designCanvas; }
  }

  function createInspector(work) {
    if (document.getElementById("mbCapcutInspector")) return;
    const aside = document.createElement("aside");
    aside.id = "mbCapcutInspector";
    aside.className = "mb-capcut-inspector";
    aside.innerHTML = `
      <div class="mb-capcut-tabs">
        <button type="button" class="active">Edit</button><button type="button">Animate</button><button type="button">Arrange</button>
      </div>
      <div class="mb-capcut-inspector-body">
        <div class="mb-capcut-object-tools">
          <button type="button" data-action="duplicate">Duplicate</button>
          <button type="button" data-action="delete">Delete</button>
          <button type="button" data-action="front">Front</button>
        </div>
        <h4 id="mbInspectorTitle">No layer selected</h4>
        <div class="mb-capcut-field"><label>X</label><input id="mbPropX" type="number" step="1"></div>
        <div class="mb-capcut-field"><label>Y</label><input id="mbPropY" type="number" step="1"></div>
        <div class="mb-capcut-field"><label>W</label><input id="mbPropW" type="number" step="1" min="1"></div>
        <div class="mb-capcut-field"><label>H</label><input id="mbPropH" type="number" step="1" min="1"></div>
        <div class="mb-capcut-field"><label>°</label><input id="mbPropAngle" type="number" step="1"></div>
        <div class="mb-capcut-group">
          <label style="font-size:11px;color:#8f96a1">Opacity</label>
          <input id="mbPropOpacity" type="range" min="0" max="100" value="100" style="width:100%">
        </div>
      </div>`;
    work.appendChild(aside);

    const tabs = [...aside.querySelectorAll(".mb-capcut-tabs button")];
    tabs.forEach(btn => btn.addEventListener("click", () => {
      tabs.forEach(b => b.classList.toggle("active", b === btn));
    }));

    aside.querySelector('[data-action="delete"]').addEventListener("click", () => {
      const canvas = activeCanvas(); const obj = canvas?.getActiveObject?.();
      if (!obj) return;
      canvas.remove(obj); canvas.discardActiveObject(); canvas.requestRenderAll();
      if (typeof window.designSnapshot === "function") window.designSnapshot();
      refreshAll();
    });
    aside.querySelector('[data-action="front"]').addEventListener("click", () => {
      const canvas = activeCanvas(); const obj = canvas?.getActiveObject?.();
      if (!obj) return;
      canvas.bringToFront(obj); canvas.requestRenderAll();
      if (typeof window.designSnapshot === "function") window.designSnapshot();
      refreshAll();
    });
    aside.querySelector('[data-action="duplicate"]').addEventListener("click", () => {
      const canvas = activeCanvas(); const obj = canvas?.getActiveObject?.();
      if (!canvas || !obj || typeof obj.clone !== "function") return;
      obj.clone(clone => {
        clone.set({ left:(Number(obj.left)||0)+24, top:(Number(obj.top)||0)+24 });
        canvas.add(clone); canvas.setActiveObject(clone); canvas.requestRenderAll();
        if (typeof window.designSnapshot === "function") window.designSnapshot();
        refreshAll();
      });
    });

    const bindings = [
      ["mbPropX","left",v => Number(v)], ["mbPropY","top",v => Number(v)],
      ["mbPropAngle","angle",v => Number(v)]
    ];
    bindings.forEach(([id,key,parse]) => {
      document.getElementById(id).addEventListener("change", e => {
        const canvas = activeCanvas(); const obj = canvas?.getActiveObject?.(); if (!obj) return;
        obj.set(key, parse(e.target.value)); obj.setCoords(); canvas.requestRenderAll();
        if (typeof window.designSnapshot === "function") window.designSnapshot(); refreshAll();
      });
    });
    document.getElementById("mbPropW").addEventListener("change", e => resizeActive("width", Number(e.target.value)));
    document.getElementById("mbPropH").addEventListener("change", e => resizeActive("height", Number(e.target.value)));
    document.getElementById("mbPropOpacity").addEventListener("input", e => {
      const canvas = activeCanvas(); const obj = canvas?.getActiveObject?.(); if (!obj) return;
      obj.set("opacity", Number(e.target.value)/100); canvas.requestRenderAll();
    });
    document.getElementById("mbPropOpacity").addEventListener("change", () => {
      if (typeof window.designSnapshot === "function") window.designSnapshot();
    });
  }

  function resizeActive(axis, target) {
    const canvas = activeCanvas(); const obj = canvas?.getActiveObject?.();
    if (!obj || !Number.isFinite(target) || target <= 0) return;
    const base = Number(obj[axis]) || 1;
    obj.set(axis === "width" ? "scaleX" : "scaleY", target/base);
    obj.setCoords(); canvas.requestRenderAll();
    if (typeof window.designSnapshot === "function") window.designSnapshot();
    refreshAll();
  }

  function createTimeline(work) {
    if (document.getElementById("mbCapcutTimeline")) return;
    const timeline = document.createElement("section");
    timeline.id = "mbCapcutTimeline";
    timeline.className = "mb-capcut-timeline";
    timeline.innerHTML = '<div class="mb-capcut-timeline-head"><strong>Timeline / Layers</strong><span>Click a track to select it on the canvas</span></div><div class="mb-capcut-tracks" id="mbCapcutTracks"></div>';
    work.appendChild(timeline);
  }

  function refreshInspector() {
    const canvas = activeCanvas();
    const object = canvas?.getActiveObject?.();
    const title = document.getElementById("mbInspectorTitle");
    if (!title) return;
    const inputs = ["mbPropX","mbPropY","mbPropW","mbPropH","mbPropAngle","mbPropOpacity"].map(id => document.getElementById(id));
    inputs.forEach(el => { if (el) el.disabled = !object; });
    if (!object) { title.textContent = "No layer selected"; return; }
    const list = canvas.getObjects();
    title.textContent = objectName(object, Math.max(0,list.indexOf(object)));
    document.getElementById("mbPropX").value = Math.round(Number(object.left)||0);
    document.getElementById("mbPropY").value = Math.round(Number(object.top)||0);
    document.getElementById("mbPropW").value = Math.round((Number(object.width)||0)*(Number(object.scaleX)||1));
    document.getElementById("mbPropH").value = Math.round((Number(object.height)||0)*(Number(object.scaleY)||1));
    document.getElementById("mbPropAngle").value = Math.round(Number(object.angle)||0);
    document.getElementById("mbPropOpacity").value = Math.round((object.opacity ?? 1)*100);
  }

  function refreshTimeline() {
    const canvas = activeCanvas(); const host = document.getElementById("mbCapcutTracks");
    if (!host || !canvas) return;
    const objects = canvas.getObjects(); const selected = canvas.getActiveObject?.();
    if (!objects.length) { host.innerHTML = '<div class="mb-capcut-empty">Add text, images, slideshow, video, or shapes to build your page.</div>'; return; }
    host.innerHTML = "";
    [...objects].reverse().forEach((object, reverseIndex) => {
      const originalIndex = objects.length - 1 - reverseIndex;
      const row = document.createElement("div");
      row.className = "mb-capcut-track" + (object === selected ? " selected" : "");
      row.dataset.type = object.assetType || object.type || "layer";
      row.innerHTML = `<span class="mb-capcut-track-label">${objectName(object, originalIndex).replace(/</g,"&lt;")}</span><div class="mb-capcut-track-bar"></div>`;
      row.addEventListener("click", () => { canvas.setActiveObject(object); object.setCoords(); canvas.requestRenderAll(); refreshAll(); });
      host.appendChild(row);
    });
  }

  function refreshAll() { refreshInspector(); refreshTimeline(); }

  function wireCanvas() {
    const canvas = activeCanvas();
    if (!canvas || canvas.__mbCapcutWired) return false;
    canvas.__mbCapcutWired = true;
    ["selection:created","selection:updated","selection:cleared","object:added","object:removed","object:modified","object:moving","object:scaling","object:rotating"].forEach(event => canvas.on(event, refreshAll));
    refreshAll();
    return true;
  }

  function install() {
    const room = document.getElementById("designRoom");
    const work = room?.querySelector(".design-work");
    if (!room || !work) { setTimeout(install, 250); return; }
    document.body.classList.add(ROOT_CLASS);
    injectStyles();
    createInspector(work);
    createTimeline(work);
    if (!wireCanvas()) setTimeout(wireCanvas, 400);
    const timer = setInterval(() => { if (wireCanvas()) clearInterval(timer); }, 500);
  }

  window.addEventListener("load", () => setTimeout(install, 250));
})();
