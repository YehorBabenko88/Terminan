const {test,expect}=require('@playwright/test');
test('consumer renders unavailable supervisor without granting authority',async({page})=>{
  await page.goto('http://127.0.0.1:18765');
  await expect(page.locator('#consumer')).toContainText('VERSIONED_SUPERVISOR_CONTRACT_NOT_PUBLISHED');
  await expect(page.locator('#consumer')).toContainText('UNAVAILABLE');
  await expect(page.locator('#consumer')).toContainText('"trading_authorized": false');
});
test('consumer renders stale, gap and synthetic provenance as text',async({page})=>{
  await page.route('**/api/consumer/v1/status?*',route=>route.fulfill({json:{version:1,sources:{grid:{state:'STALE',provenance:'AGGREGATED_HISTORY_NOT_L2'},research:{state:'GAP',provenance:'SYNTHETIC_ONLY'}},supervisor:{state:'UNAVAILABLE'},trading_authorized:false,physical_acceptance:'NOT_RUN'}}));
  await page.goto('http://127.0.0.1:18765');
  for(const label of ['STALE','GAP','SYNTHETIC_ONLY','AGGREGATED_HISTORY_NOT_L2'])await expect(page.locator('#consumer')).toContainText(label);
});
