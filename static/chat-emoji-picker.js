(() => {
  const GROUPS = [
    ["Recent", ["😀","😂","😊","😍","🥰","😎","🤔","😭","😡","👍","❤️","🙏"]],
    ["Smileys", ["😀","😃","😄","😁","😆","😅","😂","🤣","😊","🙂","🙃","😉","😍","🥰","😘","😋","😜","🤪","🤔","🤗","🤭","😴","😭","😢","😡","🤯","😎"]],
    ["Gestures", ["👍","👎","👌","✌️","🤞","🤟","🤘","👏","🙌","🫶","🙏","💪","👋","🤝","☝️"]],
    ["Hearts", ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","💔","💕","💖","💯","🔥","✨","⭐"]],
    ["Food", ["🍔","🍟","🍕","🌭","🍗","🥩","🍚","🍜","🍣","🍤","🥗","🍰","🍦","☕","🥤","🍺"]]
  ];

  const style = document.createElement("style");
  style.textContent = `
    .mb-emoji-wrap{position:relative;display:flex;align-items:center;flex:0 0 auto}
    .mb-emoji-btn{width:42px;height:42px;padding:0!important;border:1px solid var(--line,#333)!important;border-radius:12px!important;background:var(--panel-2,#202024)!important;color:inherit!important;font-size:20px!important;display:grid!important;place-items:center;cursor:pointer}
    .mb-emoji-pop{position:absolute;left:0;bottom:calc(100% + 8px);z-index:9999;width:min(330px,86vw);max-height:300px;overflow:auto;padding:10px;border:1px solid var(--line,#333);border-radius:14px;background:var(--panel,#17171b);box-shadow:0 18px 45px #000a}
    .mb-emoji-pop[hidden]{display:none!important}.mb-emoji-title{margin:7px 4px 5px;color:var(--muted,#999);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.08em}
    .mb-emoji-grid{display:grid;grid-template-columns:repeat(8,1fr);gap:3px}.mb-emoji-grid button{width:34px;height:34px;padding:0!important;border:0!important;border-radius:8px!important;background:transparent!important;font-size:20px!important;cursor:pointer}.mb-emoji-grid button:hover{background:#ffffff14!important}
    @media(max-width:520px){.mb-emoji-pop{position:fixed;left:10px;right:10px;bottom:76px;width:auto;max-height:38vh}.mb-emoji-grid{grid-template-columns:repeat(7,1fr)}}
  `;
  document.head.appendChild(style);

  function install(form, input) {
    if (!form || !input || form.querySelector(".mb-emoji-wrap")) return;
    const wrap = document.createElement("div");
    wrap.className = "mb-emoji-wrap";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "mb-emoji-btn";
    toggle.textContent = "😀";
    toggle.title = "Emoji";
    toggle.setAttribute("aria-label", "Open emoji picker");
    const pop = document.createElement("div");
    pop.className = "mb-emoji-pop";
    pop.hidden = true;
    pop.innerHTML = GROUPS.map(([name, emojis]) => `<div class="mb-emoji-title">${name}</div><div class="mb-emoji-grid">${emojis.map(e => `<button type="button" data-emoji="${e}">${e}</button>`).join("")}</div>`).join("");
    toggle.addEventListener("click", e => { e.stopPropagation(); pop.hidden = !pop.hidden; });
    pop.addEventListener("click", e => {
      const b = e.target.closest("[data-emoji]");
      if (!b) return;
      const emoji = b.dataset.emoji;
      const start = input.selectionStart ?? input.value.length;
      const end = input.selectionEnd ?? input.value.length;
      input.value = input.value.slice(0,start) + emoji + input.value.slice(end);
      const pos = start + emoji.length;
      input.focus(); input.setSelectionRange(pos,pos);
      input.dispatchEvent(new Event("input", {bubbles:true}));
    });
    document.addEventListener("click", e => { if (!wrap.contains(e.target)) pop.hidden = true; });
    wrap.append(toggle,pop);
    input.insertAdjacentElement("afterend", wrap);
  }

  function boot(){
    install(document.getElementById("chatForm") || document.querySelector("#chatSheet .chat-compose"), document.getElementById("chatInput"));
    install(document.getElementById("opsChatForm"), document.getElementById("opsChatInput"));
  }
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
  new MutationObserver(boot).observe(document.documentElement,{childList:true,subtree:true});
})();
