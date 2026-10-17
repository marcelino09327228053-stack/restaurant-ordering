/* Shared by the public menu, QR menu and owner preview. */
(() => {
  const defaults = {background:'#0b0b0d',text:'#f5f5f4',gradient:false,gradient_color:'#6d28ff',background_image:'',glow:false,intensity:'medium',media_url:'',media_type:'none'};
  const safeURL = value => {
    if (!value) return '';
    try { const u = new URL(value, location.origin); return u.protocol === 'https:' || (u.origin === location.origin && u.pathname.startsWith('/static/uploads/')) ? u.href : ''; } catch { return ''; }
  };
  let preview = null;
  function apply(input = {}) {
    const config = {...defaults, ...input};
    for (const key of ['background','text','gradient_color']) if (!/^#[0-9a-f]{6}$/i.test(config[key])) config[key] = defaults[key];
    document.body.classList.add('menu-appearance');
    const root = document.documentElement;
    MenuFonts.apply(document.getElementById('menu'), config.font);
    MenuFonts.typography(document.getElementById('menu'), config);
    root.style.setProperty('--me-bg', config.background);
    root.style.setProperty('--me-text', config.text);
    const image = safeURL(config.background_image);
    root.style.setProperty('--me-surface', image ? `linear-gradient(#0006,#0006),url(${JSON.stringify(image)})` : config.gradient ? `linear-gradient(135deg,${config.background},${config.gradient_color})` : config.background);
    const strength = {low:8,medium:16,high:26}[config.intensity] || 16;
    root.style.setProperty('--me-glow', config.glow ? `0 0 ${strength}px ${config.background},inset 0 0 0 1px ${config.gradient_color}` : 'none');
    let slot = document.getElementById('menuMediaDisplay');
    const hero = document.getElementById('hero');
    if (!slot && hero) { slot = document.createElement('section'); slot.id = 'menuMediaDisplay'; slot.setAttribute('aria-label','Restaurant media'); hero.before(slot); }
    if (!slot) return;
    const url = safeURL(config.media_url);
    const key = `${config.media_type}:${url}`;
    if (slot.dataset.media === key) return;
    slot.dataset.media = key;
    slot.replaceChildren();
    slot.hidden = !url || config.media_type === 'none';
    if (slot.hidden) return;
    const media = document.createElement(config.media_type === 'video' ? 'video' : 'img');
    media.src = url;
    media.addEventListener('error', () => { slot.hidden = true; });
    if (media.tagName === 'VIDEO') {
      media.controls = true; media.playsInline = true; media.muted = true; media.autoplay = true; media.loop = true; media.preload = 'metadata';
      const sound = document.createElement('button'); sound.type='button'; sound.className='menu-media-sound'; sound.textContent='Sound / Unmute'; sound.setAttribute('aria-pressed','false');
      sound.onclick = () => { media.muted = !media.muted; if (!media.muted) { media.volume = 1; media.play().catch(() => {}); } };
      media.addEventListener('volumechange', () => { sound.textContent = media.muted ? 'Sound / Unmute' : 'Mute sound'; sound.setAttribute('aria-pressed', String(!media.muted)); });
      slot.append(media,sound);
      media.play().catch(() => {});
    } else { media.alt='Restaurant display'; slot.append(media); }
  }
  window.MenuAppearance = {defaults, apply(config) { apply(preview || config); }};
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== parent || parent === window || new URLSearchParams(location.search).get('menuPreview') !== '1') return;
    if (event.data?.type !== 'menu-appearance-preview') return;
    preview = event.data.config; apply(preview);
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    if (parent !== window) parent.postMessage({type:'menu-appearance-ready'}, location.origin);
  });
})();
