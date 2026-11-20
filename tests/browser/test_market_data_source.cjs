// Requires playwright-core and CHROME_PATH pointing to an installed Chromium.
// Run from the repository root with node --test tests/browser/test_market_data_source.cjs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { chromium } = require('playwright-core');

test('the MarketData panel clears stale state and never promotes unqualified data', async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH });
  try {
    const page = await browser.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    const html = fs.readFileSync(path.join(__dirname, '../../terminan/index.html'), 'utf8');
    const unavailable = {
      api_version: { major: 1, minor: 0 },
      producer: 'market_data',
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
    let sourceMarked = true;
    let sourceStatus = 'SOURCE_UNQUALIFIED';
    let marketDataCandleRequests = 0;
    let pauseCandle = null;
    await page.route('http://127.0.0.1:8765/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/') {
        await route.fulfill({ contentType: 'text/html', body: html });
      } else if (url.pathname === '/api/market-data/source') {
        if (reply instanceof Promise) await reply;
        if (reply === null) await route.abort();
        else await route.fulfill({ json: reply });
      } else if (url.pathname === '/api/instruments' || url.pathname === '/api/candles') {
        const headers = sourceMarked ? { 'X-Terminan-Data-Status': sourceStatus } : {};
        const candle = { t: 0, o: 100, h: 110, l: 90, c: 105 };
        if (url.pathname === '/api/candles' && url.searchParams.get('timeframe') === '1m' && pauseCandle) {
          await pauseCandle;
        }
        const rows = url.pathname === '/api/instruments' ? ['BTCUSDT'] :
          url.searchParams.get('timeframe') === '5m' ? [candle, { ...candle, t: 300000 }] : [candle];
        await route.fulfill({ headers, json: rows });
      } else {
        if (url.pathname === '/api/market-data/candles') marketDataCandleRequests++;
        await route.fulfill({ json: url.pathname === '/api/status' ? {} : [] });
      }
    });
    const goto = () => page.goto('http://127.0.0.1:8765/');
    const waitForState = state => page.locator(`#market-data-quality[data-state="${state}"]`).waitFor({
      timeout: 4000,
    });
    await goto();
    await waitForState('unavailable');
    await page.locator('#chartmsg').filter({ hasText: 'SOURCE_UNQUALIFIED' }).waitFor({ timeout: 4000 });
    assert.match(await page.locator('#source').innerText(), /SOURCE_UNQUALIFIED/);
    sourceMarked = false;
    await page.locator('#refresh').click();
    await page.locator('#error').filter({ hasText: 'Происхождение данных не указано' }).waitFor({ timeout: 4000 });
    assert.doesNotMatch(await page.locator('#chartmsg').innerText(), /SOURCE_UNQUALIFIED/);
    assert.equal(marketDataCandleRequests, 0);
    // A retired marker must not become an alias for the canonical source status.
    sourceMarked = true;
    sourceStatus = 'OFFLINE_LEGACY_UNVERIFIED';
    const retiredResponse = page.waitForResponse(event => new URL(event.url()).pathname === '/api/candles');
    await page.locator('#refresh').click();
    await retiredResponse;
    await page.locator('#error').filter({ hasText: 'Происхождение данных не указано' }).waitFor({ timeout: 4000 });
    assert.doesNotMatch(await page.locator('#chartmsg').innerText(), /SOURCE_UNQUALIFIED/);
    assert.equal(marketDataCandleRequests, 0);
    sourceStatus = 'SOURCE_UNQUALIFIED';
    sourceMarked = true;
    let resumeCandle;
    pauseCandle = new Promise(resolve => { resumeCandle = resolve; });
    const oldCandle = event => new URL(event.url()).searchParams.get('timeframe') === '1m';
    const oldest = page.waitForRequest(oldCandle, { timeout: 4000 });
    await page.locator('#refresh').click();
    await oldest;
    await page.locator('#tf').selectOption('5m');
    const currentChart = page.locator('#chartmsg').filter({ hasText: '2 свечей' });
    await currentChart.waitFor({ timeout: 4000 });
    const staleResponse = page.waitForResponse(oldCandle, { timeout: 4000 });
    resumeCandle();
    pauseCandle = null;
    await staleResponse;
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(await currentChart.count(), 1);
    const button = page.getByRole('button', { name: 'Проверить MarketData' });
    reply = { ...unavailable, connection: 'CONNECTED_UNQUALIFIED', database: 'READ_ONLY' };
    await button.focus();
    await page.keyboard.press('Enter');
    await waitForState('unqualified');
    assert.match(await page.locator('#market-data-quality').innerText(), /Происхождение не подтверждено/);

    reply = new Promise(resolve => { release = resolve; });
    await button.click();
    await waitForState('checking');
    assert.equal(await button.isDisabled(), true);
    assert.doesNotMatch(await page.locator('#market-data-quality').innerText(), /База доступна/);
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
    assert.equal(await page.locator('#market-data-quality').count(), 1);
    assert.deepEqual(pageErrors, []);
  } finally {
    await browser.close();
  }
});
