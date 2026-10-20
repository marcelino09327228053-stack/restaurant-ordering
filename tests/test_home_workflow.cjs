// Run against the app or a static server: HOME_TEST_URL=http://127.0.0.1:8012/home.html
const {chromium} = require('playwright');
const assert = require('assert/strict');
const path = require('path');
const os = require('os');

(async () => {
  const browser = await chromium.launch({headless:true, channel:'chrome'});
  try {
    const page = await browser.newPage({viewport:{width:1672,height:1100}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.env.HOME_TEST_URL || 'http://127.0.0.1:8011/');
    const workflow = page.locator('.workflow');
    assert.equal(await workflow.locator('a,button,input,[onclick],[tabindex]').count(),0);
    assert.equal(await workflow.locator('.workflow-stage').count(),5);
    assert.equal(await page.locator('.feature-card').count(),0);
    assert.equal(await page.locator('.home-slide').count(),9);
    await page.waitForFunction(() => homeSlideIndex === 1, {}, {timeout:4500});
    assert.equal(await page.evaluate(() => [...document.querySelectorAll('.home-background-slide')].findIndex(e => e.classList.contains('is-active'))),1);

    async function seek(time) {
      await workflow.evaluate((root,time) => {
        for (const animation of root.getAnimations({subtree:true})) {
          animation.pause();
          animation.currentTime = time;
        }
      },time);
    }
    for (let i=0;i<5;i++) {
      await seek((16 + i*14)*80);
      const opacity = await page.locator('.workflow-panorama .workflow-device-light')
        .evaluateAll(nodes => nodes.map(n => Number(getComputedStyle(n).opacity)));
      assert(opacity[i] > .5, 'Reached screen illuminates');
      for(let next=i+1;next<5;next++) assert.equal(opacity[next],0,'Future stage stays unlit');
      if(i<4) {
        await seek((24 + i*14)*80);
        const pulses = await page.locator('.workflow-travel').evaluateAll(nodes => nodes.map(n => Number(getComputedStyle(n).opacity)));
        assert(pulses[i] > .9);
        assert.equal(pulses.filter(n => n > .1).length,1,'Only one connector carries the signal');
      }
    }
    await seek(7999);
    const reset = await page.locator('.workflow-panorama .workflow-device-light').evaluateAll(nodes => nodes.every(n => Number(getComputedStyle(n).opacity)<.01));
    assert(reset,'Temporary glow fades before restarting');
    await seek(1400);
    await workflow.screenshot({path:path.join(os.tmpdir(),'workflow-desktop-final.png')});
    for(const width of [320,390,700,768,1280]) {
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),'No overflow at '+width);
      assert.equal(await page.locator('.workflow-panorama').isVisible(),width>700);
      if(width===390) await workflow.screenshot({path:path.join(os.tmpdir(),'workflow-mobile-final.png')});
    }
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await workflow.evaluate(root => root.getAnimations({subtree:true}).length),0);
    assert.deepEqual(errors,[]);
    console.log('PASS: sequential scan workflow, single traveling signal, smooth reset, responsive layout, reduced motion, slideshow, no interactive decorations or JS errors.');
  } finally {await browser.close();}
})().catch(error => {console.error(error);process.exit(1);});
