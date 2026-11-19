// Requires playwright-core and CHROME_PATH pointing to an installed Chromium.
// Run from the repository root with node --test tests/browser/test_grid_source.cjs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { chromium } = require('playwright-core');

test('the Grid panel clears stale state and never promotes unqualified data', async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH });
  try {
    const page = await browser.newPage();
    const html = fs.readFileSync(path.join(__dirname, '../../terminan/index.html'), 'utf8');
    const unavailable = {
      api_version: { major: 1, minor: 0 },
      producer: 'bybit-cluster-grid',
      connection: 'UNAVAILABLE',
      market_data: 'UNAVAILABLE',
      database: 'UNAVAILABLE',
      candles: 'UNAVAILABLE',
      footprint: 'UNAVAILABLE',
      live_l2: false,
      execution_authority: false,
    };
    let reply = unavailable;
    let release;
    await page.route('http://127.0.0.1:8765/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/') {
        await route.fulfill({ contentType: 'text/html', body: html });
      } else if (url.pathname === '/api/grid/source') {
        if (reply instanceof Promise) await reply;
        if (reply === null) await route.abort();
        else await route.fulfill({ json: reply });
      } else {
        await route.fulfill({ json: url.pathname === '/api/status' ? {} : [] });
      }
    });
    const goto = () => page.goto('http://127.0.0.1:8765/');
    const waitForState = state => page.locator(`#grid-quality[data-state="${state}"]`).waitFor({
      timeout: 4000,
    });
    await goto();
    await waitForState('unavailable');
    const button = page.getByRole('button', { name: 'Проверить Grid' });
    reply = { ...unavailable, connection: 'CONNECTED_UNQUALIFIED', database: 'READ_ONLY' };
    await button.focus();
    await page.keyboard.press('Enter');
    await waitForState('unqualified');
    assert.match(await page.locator('#grid-quality').innerText(), /Происхождение не подтверждено/);

    reply = new Promise(resolve => { release = resolve; });
    await button.click();
    await waitForState('checking');
    assert.equal(await button.isDisabled(), true);
    assert.doesNotMatch(await page.locator('#grid-quality').innerText(), /База доступна/);
    reply = { ...unavailable, connection: 'CONNECTED_UNQUALIFIED', live_l2: true };
    release();
    await waitForState('unavailable');

    reply = null;
    await button.click();
    await waitForState('unavailable');
    assert.equal(await button.isEnabled(), true);
    reply = { ...unavailable, connection: 'CONNECTED_UNQUALIFIED' };
    await goto();
    await waitForState('unqualified');
    assert.equal(await page.locator('#grid-quality').count(), 1);
  } finally {
    await browser.close();
  }
});
