const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const session=JSON.parse(fs.readFileSync(path.join(require('node:os').tmpdir(),'restaurant-menu-editor-check/session.json')));
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try {
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:8011';
 await page.addInitScript(token=>localStorage.setItem('owner_token',token),session.token);
 await page.goto(base+'/owner');
 await page.waitForFunction(()=>document.querySelector('#menuGallery strong'));await page.locator('[data-studio-panel="tablesPanel"]').click();await page.locator('#tablesPanel').getByRole('button',{name:'Menu',exact:true}).click();

 const popovers=[['openMenuButton','menuDishForm'],['editMenuButton','menuItemsPanel'],['menuAppearanceButton','menuAppearancePanel']];
 const allClosed=async()=>{for(const [button,panel] of popovers){assert(await page.locator('#'+panel).isHidden());assert.equal(await page.locator('#'+button).getAttribute('aria-expanded'),'false');}};
 for(const [button,panel] of popovers){
  await page.locator('#'+button).click();await page.locator('#'+panel).waitFor();
  await page.locator('#'+panel).click({position:{x:10,y:10}});assert(await page.locator('#'+panel).isVisible());
  await page.mouse.click(5,200);await allClosed();
  await page.locator('#'+button).click();await page.keyboard.press('Escape');await allClosed();
  await page.locator('#'+button).click();await page.locator('#'+button).click();await allClosed();
  for(const tab of ['Payment','Table & QR']){
   await page.locator('#'+button).click();await page.locator('#tablesPanel').getByRole('button',{name:tab,exact:true}).click();await allClosed();
   await page.locator('#tablesPanel').getByRole('button',{name:'Menu',exact:true}).click();
  }
 }
 for(const [button,panel] of popovers){await page.locator('#'+button).click();for(const [other,otherPanel] of popovers)assert.equal(await page.locator('#'+otherPanel).isVisible(),other===button);}
 await page.locator('[data-studio-panel="menuPanel"]').click();await allClosed();
 await page.locator('[data-studio-panel="tablesPanel"]').click();
 await page.locator('#openMenuButton').click();await page.evaluate(()=>document.getElementById('tablesPanel').hidden=true);await page.waitForFunction(()=>document.getElementById('menuDishForm').hidden);await allClosed();
 await page.locator('[data-studio-panel="tablesPanel"]').click();
 await page.locator('#menuAppearanceButton').click();
 await page.locator('#menuFontButton').click();
 assert.equal(await page.locator('#menuFontOptions').getByRole('option').count(),14);
 for(const font of ['Pacifico','Bebas Neue','Cinzel','Playfair Display']){
  if(await page.locator('#menuFontOptions').isHidden()) await page.locator('#menuFontButton').click();
  await page.locator('#menuFontOptions').getByRole('option',{name:font,exact:true}).click();
  assert.match(await page.locator('#menuGallery strong').first().evaluate(e=>getComputedStyle(e).fontFamily),new RegExp(font));
 }
 await page.locator('#menuFontButton').click();await page.keyboard.press('Escape');assert(await page.locator('#menuFontOptions').isHidden());
 await page.locator('#menuFontButton').press('ArrowDown');await page.keyboard.press('Home');await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');assert.equal(await page.locator('#menuFont').inputValue(),'Bebas Neue');
 await page.locator('#menuFontButton').click();await page.locator('#menuFontOptions').getByRole('option',{name:'Bebas Neue',exact:true}).click();
 await page.locator('#menuCurrency').selectOption('USD');
 await page.locator('#menuPriceColor').fill('#123456');await page.locator('#menuPriceColor').dispatchEvent('input');
 const saved=page.waitForResponse(r=>r.url().endsWith('/api/owner/menu-appearance')&&r.request().method()==='PATCH');
 await page.getByRole('button',{name:'Save Appearance',exact:true}).click();assert.equal((await saved).status(),200);
 await page.reload();await page.waitForFunction(()=>document.querySelector('#menuGallery strong'));await page.locator('[data-studio-panel="tablesPanel"]').click();await page.locator('#tablesPanel').getByRole('button',{name:'Menu',exact:true}).click();await page.locator('#menuAppearanceButton').click();assert.equal(await page.locator('#menuFontButton').innerText(),'Bebas Neue');assert.equal(await page.locator('#menuCurrency').inputValue(),'USD');
 await page.locator('#menuFontButton').click();await page.locator('#menuAppearancePanel h2').click();assert(await page.locator('#menuFontOptions').isHidden());
 await page.setViewportSize({width:390,height:844});await page.locator('#menuFontButton').click();assert(await page.locator('#menuFontOptions').getByRole('option',{name:'Bebas Neue',exact:true}).isVisible());
 await page.screenshot({path:path.join(require('node:os').tmpdir(),'restaurant-menu-editor-check/fonts.png')});
 const loaded=await page.evaluate(async()=>{for(const font of MenuFonts.names){const faces=await document.fonts.load(`16px "${font}"`);if(!faces.length){console.log("Missing font",font);return false;}}return true;});assert(loaded);
 for(const route of ['/order?table='+session.table,'/phone-order?table='+session.table,'/r/editor-test']){
  await page.goto(base+route);await page.locator('#menu .card').first().waitFor();
  for(const selector of ['h3','.desc','.price']) assert.match(await page.locator('#menu '+selector).first().evaluate(e=>getComputedStyle(e).fontFamily),/Bebas Neue/);
  assert.equal(await page.locator('#menu .price').first().evaluate(e=>getComputedStyle(e).color),'rgb(18, 52, 86)');
  assert.match(await page.locator('#menu .price').first().innerText(),/\$/);
  await page.evaluate(()=>MenuFonts.apply(document.getElementById('menu'),'invalid-font'));assert.match(await page.locator('#menu h3').first().evaluate(e=>getComputedStyle(e).fontFamily),/Poppins/);
 }
 assert.deepEqual(errors,[]);console.log('PASS: popup outside/Escape/toggle/exclusivity/tab switches/workspace hidden; font previews, keyboard, outside click, mobile, save/reload, public fonts/colors/currency, invalid fallback; Bebas Neue loaded.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});


