(() => {
  const paths = {
    dining:'M4 3v6c0 3 4 3 4 0V3M6 3v18M16 3v18M16 3c6 3 6 9 0 9',
    cart:'M2 3h3l3 12h11l3-9H6M9 20h.01M19 20h.01',
    wrench:'M14 6l4 4 4-4c1 6-4 9-8 7L6 21a2 2 0 0 1-3-3l8-8c-2-4 1-9 7-8z',
    scissors:'M9 9l11 12M9 15L20 3M7 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6M7 13a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
    chart:'M3 21V13h4v8zM10 21V8h4v13zM17 21V3h4v18z',
    grid:'M3 3h6v6H3zM15 3h6v6h-6zM3 15h6v6H3zM15 15h6v6h-6z',
    gear:'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8',
    cloud:'M6 19a5 5 0 0 1-1-10 7 7 0 0 1 13-2 6 6 0 0 1 1 12z',
    store:'M3 3h18l1 5H2zM4 8v13h16V8M9 21v-6h6v6M7 11h1M16 11h1',
    people:'M9 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6M17 5a2 2 0 1 0 0 4 2 2 0 0 0 0-4M2 21v-5c0-6 14-6 14 0v5zM18 12c4 0 4 4 4 9h-3',
    headset:'M3 14V11a9 9 0 0 1 18 0v7c0 4-5 4-9 4M3 12h3v7H3zM18 12h3v7h-3z'
  };
  document.querySelectorAll('[data-icon]').forEach(el => {
    el.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[el.dataset.icon] || paths.grid}"/></svg>`;
  });
  const info = {
    Features:'Build your business page, organize your menu, create table QR codes, manage orders and payments, and connect customers with your cashier.',
    Solutions:'Start with restaurant ordering. The other business types in this home design illustrate the platform’s future direction; their specialist tools are not available yet.',
    Pricing:'Pricing has not been published yet. Sign in to access your existing business workspace.',
    About:'MB SiteHub brings your business page, restaurant menu, orders, payments, and cashier tools together in one place.',
    'Watch Demo':'Create your page in Design Your Page, add your dishes in Menu, then create a table QR code. Customers scan it to order, and the cashier manages incoming orders and payments.'
  };
  const dialog=document.getElementById('infoDialog');
  function showInfo(title){document.getElementById('infoTitle').textContent=title;document.getElementById('infoBody').textContent=info[title];dialog.showModal();}
  document.querySelectorAll('[data-info]').forEach(button=>button.addEventListener('click',()=>showInfo(button.dataset.info)));
  document.getElementById('watchDemo').addEventListener('click',()=>showInfo('Watch Demo'));
  dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
  document.querySelectorAll('[data-industry]').forEach(button=>button.addEventListener('click',()=>{
    const selected=button.dataset.industry;
    document.querySelectorAll('[data-industry]').forEach(item=>{
      const active=item.dataset.industry===selected;
      item.classList.toggle(item.closest('.dots')?'active':'selected',active);
      item.setAttribute('aria-pressed',String(active));
    });
    document.querySelector('.hero-background').style.backgroundPosition=`${['20%','35%','50%','65%','80%'][Number(selected)]} top`;
  }));
  document.querySelectorAll('.stats article').forEach(card=>card.title='Sample statistic from the supplied design; not live platform data.');
})();
