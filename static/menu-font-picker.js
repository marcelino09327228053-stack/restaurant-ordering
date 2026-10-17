(() => {
  const picker = document.getElementById('menuFontPicker');
  const input = document.getElementById('menuFont');
  const button = document.getElementById('menuFontButton');
  const list = document.getElementById('menuFontOptions');
  function set(value) {
    input.value = MenuFonts.normalize(value);
    button.textContent = input.value;
    button.style.fontFamily = MenuFonts.family(input.value);
    for (const option of list.children) {
      const selected = option.dataset.font === input.value;
      option.setAttribute('aria-selected', String(selected));
      option.tabIndex = selected ? 0 : -1;
    }
  }
  function close(restoreFocus = false) {
    if (!list.hidden) list.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    if (restoreFocus) button.focus();
  }
  function open() {
    list.hidden = false;
    button.setAttribute('aria-expanded', 'true');
    list.querySelector('[aria-selected="true"]').focus();
  }
  for (const name of MenuFonts.names) {
    const option = document.createElement('button');
    option.type = 'button';
    option.setAttribute('role', 'option');
    option.dataset.font = name;
    option.textContent = name;
    option.style.fontFamily = MenuFonts.family(name);
    option.onclick = () => { set(name); renderMenuList(); close(true); };
    list.append(option);
  }
  button.onclick = () => list.hidden ? open() : close();
  button.addEventListener('keydown', event => {
    if (['ArrowDown', 'ArrowUp'].includes(event.key)) { event.preventDefault(); open(); }
  });
  list.addEventListener('keydown', event => {
    const options = [...list.children];
    const index = options.indexOf(document.activeElement);
    let next;
    if (event.key === 'ArrowDown') next = (index + 1) % options.length;
    if (event.key === 'ArrowUp') next = (index + options.length - 1) % options.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = options.length - 1;
    if (next !== undefined) { event.preventDefault(); options[next].focus(); }
  });
  picker.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !list.hidden) { event.preventDefault(); event.stopPropagation(); close(true); }
  });
  picker.addEventListener('focusout', event => { if (!picker.contains(event.relatedTarget)) close(); });
  window.MenuFontPicker = {set, close};
  set(input.value);
})();
