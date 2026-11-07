const { test, expect } = require("@playwright/test");
const F = require("./fixtures.cjs");

test('C3 and mux framing execute in Chromium without Node APIs', async ({page}) => {
  await page.goto('/sync.html');
  await page.addScriptTag({url:'/sync/c3.js'});
  await page.addScriptTag({url:'/sync/mux-stream.js'});
  const result=await page.evaluate(()=>{
    const stream=new TerminanMuxStream.MuxRecords();
    stream.feed('data: {"a":');
    const token=stream.feed('"1.0"}\n\n')[0];
    let rejected=false;
    try{TerminanC3.parse('{"a":1.0}');}catch{rejected=true;}
    return {raw:TerminanC3.text(token),rejected,frozen:Object.isFrozen(TerminanC3.value(token))};
  });
  expect(result).toEqual({raw:'{"a":"1.0"}',rejected:true,frozen:true});
  await expect(page.getByRole('status')).toContainText('UNAVAILABLE');
});
test("unavailable endpoint never fabricates LIVE or sends commands", async ({
  page,
}) => {
  const requests = [];
  page.on("request", (r) => requests.push(r.url()));
  await page.goto("/sync.html");
  await expect(page.getByRole("status")).toContainText("UNAVAILABLE");
  await expect(
    page.getByRole("button", { name: "Submit command" }),
  ).toBeDisabled();
  await expect(page.getByRole("tab")).toHaveCount(14);
  await expect(page.locator("[data-dimension]")).toHaveCount(4);
  await expect(page.locator("[data-dimension] .dimension-state")).toHaveText([
    "UNKNOWN",
    "UNKNOWN",
    "UNKNOWN",
    "UNKNOWN",
  ]);
  expect(requests.some((x) => x.includes("/control/v1"))).toBe(false);
  await expect(page).toHaveScreenshot("unavailable-desktop.png", {
    animations: "disabled",
    maxDiffPixels: 0,
  });
});
test("keyboard navigation and narrow layout", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/sync.html");
  const overview = page.getByRole("tab", { name: "Overview", exact: true });
  await overview.focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "Infrastructure", exact: true }),
  ).toBeFocused();
  await expect(page.getByRole("tabpanel")).toHaveAttribute(
    "aria-labelledby",
    "tab-infrastructure",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page).toHaveScreenshot("unavailable-mobile.png", {
    animations: "disabled",
    maxDiffPixels: 0,
  });
});
test("synthetic integrity keeps four independent states and session expiry clears jobs", async ({
  page,
}) => {
  await page.goto("/sync.html");
  await page.evaluate((snapshot) => {
    const clock = { wall: Date.parse("2026-11-06T12:00:00Z"), mono: 0 };
    const s = new TerminanSync.SyncState({
      clock: () => clock,
      validateDomain: () => true,
    });
    s.install(snapshot);
    s.connection(true);
    s.resources.set("fixture-integrity", {
      resource_id: "fixture-integrity",
      resource_type: "integrity",
      value: {
        byte_integrity: { state: "VERIFIED" },
        source_completeness: { state: "GAPS" },
        redundancy: { state: "UNDER_REPLICATED" },
        authority_freshness: { state: "STALE" },
      },
    });
    TerminanSyncView.render(s, { synthetic: true });
    window.fixtureState = s;
  }, F.snapshot());
  await expect(page.locator("#qualification")).toContainText("SYNTHETIC");
  await expect(page.locator("[data-dimension] .dimension-state")).toHaveText([
    "VERIFIED",
    "GAPS",
    "UNDER_REPLICATED",
    "STALE",
  ]);
  await page.evaluate(() => {
    fixtureState.error({ code: "SESSION_EXPIRED" });
    TerminanSyncView.render(fixtureState, { synthetic: true });
  });
  await expect(page.getByRole("status")).toContainText("AUTH_REQUIRED");
  await expect(page.locator("#resource-rows")).not.toContainText("fixture-job");
  await expect(
    page.getByRole("button", { name: "Submit command" }),
  ).toBeDisabled();
});
