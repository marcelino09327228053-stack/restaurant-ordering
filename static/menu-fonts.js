/* One allowlist and CSS font stack for owner and customer menus. */
(() => {
  const names = Object.freeze(['Poppins', 'Bebas Neue', 'Oswald', 'Playfair Display', 'Merriweather', 'Montserrat', 'Anton', 'Pacifico', 'Lobster', 'Dancing Script', 'Cinzel', 'Abril Fatface', 'Righteous', 'Permanent Marker']);
  const normalize = value => names.includes(value) ? value : 'Poppins';
  const family = value => `"${normalize(value)}", Arial, sans-serif`;
  const size = value => Number.isFinite(value) ? Math.max(12, Math.min(32, value)) : 18;
  function typography(element, theme = {}) {
    if (!element) return;
    element.style.setProperty('--menu-text-align', ['left','center','right'].includes(theme.text_align) ? theme.text_align : 'left');
    element.style.setProperty('--menu-font-size', size(theme.font_size) + 'px');
  }
  window.MenuFonts = Object.freeze({names, normalize, family, size, typography, apply(element, value) {
    if (element) element.style.setProperty('--menu-font', family(value));
  }});
})();
