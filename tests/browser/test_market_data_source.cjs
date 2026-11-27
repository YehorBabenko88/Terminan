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
    // Exact Grid 5m is NOT a generic /api/candles chart. The old UI
    // incorrectly displayed two unqualified fabricated 5m candles; after
    // source qualification it must fail closed when the MTF receipt is absent.
    const currentChart = page.locator('#qualified-receipt').filter({
      hasText: 'UNAVAILABLE · точная MTF-квитанция отсутствует',
    });
    await currentChart.waitFor({ timeout: 4000 });
    assert.doesNotMatch(await page.locator('#chartmsg').innerText(), /2 свечей/);
    const staleResponse = page.waitForResponse(oldCandle, { timeout: 4000 });
    resumeCandle();
    pauseCandle = null;
    await staleResponse;
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(await currentChart.count(), 1);
    assert.doesNotMatch(await page.locator('#chartmsg').innerText(), /2 свечей/);
    assert.equal(marketDataCandleRequests, 0);
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

test('real Chromium displays strict source-qualified LIVE 5m and 15m Decimal MTF without legacy fallback', async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH });
  try {
    const page = await browser.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    const html = fs.readFileSync(path.join(__dirname, '../../terminan/index.html'), 'utf8');
    const minute = 60000;
    const now = Date.now();
    const end = Math.floor((now - minute) / 900000) * 900000;
    const decimal = '20000000000000008.01';
    const finger = 'a'.repeat(64);
    let trustFailure = false;
    const requests = [];
    function liveReceipt(tf, tampered = false) {
      const width = tf === '5m' ? 300000 : 900000;
      return {
        status: 'PARTIAL', reason: 'EXCHANGE_COMPLETENESS_UNATTESTED',
        timeframe: tf, source_timeframe: '1m', source_minutes: tf === '5m' ? 25 : 75,
        read_only: true, record_integrity: 'VERIFIED',
        source_authenticity: 'NOT_INDEPENDENTLY_ATTESTED',
        quality_attestation: 'NOT_INDEPENDENTLY_ATTESTED',
        storage_immutability: 'NOT_ATTESTED',
        source_numeric_precision: 'STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW',
        volume_precision: 'EXACT_STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW',
        exchange_completeness_attested: false,
        paper_admitted: false, trading_authorized: false, execution_authority: false,
        dataset_fingerprint: finger,
        rows: Array.from({ length: 5 }, (_, i) => {
          const t = end - width * (5 - i);
          return {
            t, closed_at_ms: t + width, o: 100, h: 110, l: 90, c: 105,
            v: decimal,
            volume_precision: 'EXACT_STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW',
            volume_decimal: decimal, buy_volume_decimal: decimal,
            sell_volume_decimal: '0', delta_decimal: '0.01',
          };
        }).map((row, i) => tampered && i === 4 ? { ...row, delta_decimal: '-0' } : row),
      };
    }
    await page.route('http://127.0.0.1:8765/**', async route => {
      const url = new URL(route.request().url());
      requests.push(url.pathname + url.search);
      if (url.pathname === '/') {
        await route.fulfill({ contentType: 'text/html', body: html });
      } else if (url.pathname === '/api/instruments') {
        await route.fulfill({
          headers: { 'X-Terminan-Data-Status': 'SOURCE_UNQUALIFIED' }, json: ['BTCUSDT'],
        });
      } else if (url.pathname === '/api/candles') {
        await route.fulfill({
          headers: { 'X-Terminan-Data-Status': 'SOURCE_UNQUALIFIED' },
          json: [{ t: 0, o: 1, h: 1, l: 1, c: 1 }],
        });
      } else if (url.pathname === '/api/market-data/qualified/timeframe') {
        const tf = url.searchParams.get('timeframe');
        await route.fulfill({ json: liveReceipt(tf, trustFailure) });
      } else if (url.pathname === '/api/market-data/source') {
        await route.fulfill({
          json: { api_version: { major: 1, minor: 0 }, producer: 'market_data',
            connection: 'UNAVAILABLE', market_data: 'UNAVAILABLE',
            database: 'UNAVAILABLE', candles: 'UNAVAILABLE', footprint: 'UNAVAILABLE',
            live_l2: false, execution_authority: false },
        });
      } else {
        await route.fulfill({ json: url.pathname === '/api/status' ? {} : [] });
      }
    });
    await page.goto('http://127.0.0.1:8765/');
    for (const tf of ['5m', '15m']) {
      await page.locator('#tf').selectOption(tf);
      await page.locator('#chartmsg')
        .filter({ hasText: '5 свечей ' + tf + ' · PARTIAL' }).waitFor({ timeout: 6000 });
      assert.match(await page.locator('#qualified-receipt').innerText(),
        /Объём: 20000000000000008[.]01/);
      assert.match(await page.locator('#qualified-receipt').innerText(), /Delta: 0[.]01/);
      assert.match(await page.locator('#qualified-receipt').innerText(),
        /paper\/trading запрещены/);
    }
    trustFailure = true;
    await page.locator('#refresh').click();
    await page.locator('#qualified-receipt')
      .filter({ hasText: 'UNAVAILABLE · точная MTF-квитанция отсутствует' })
      .waitFor({ timeout: 6000 });
    assert.doesNotMatch(await page.locator('#chartmsg').innerText(), /5 свечей 15m/);
    assert.equal(requests.filter(x => x.includes('/api/market-data/qualified/historical?')).length, 0);
    assert.equal(requests.filter(x => x.includes('/api/candles?') && x.includes('timeframe=5m')).length, 1);
    assert.equal(requests.filter(x => x.includes('/api/candles?') && x.includes('timeframe=15m')).length, 2);
    assert.deepEqual(pageErrors, []);
  } finally {
    await browser.close();
  }
});
