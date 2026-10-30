const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'tests/browser',testMatch:'unified_contract.spec.cjs',workers:1,
 timeout:30000,retries:0,expect:{timeout:6000},projects:['chromium','firefox'].map(browserName=>({name:browserName,use:{browserName,viewport:{width:1440,height:1080},timezoneId:'UTC'}})),
 reporter:[['list'],['json',{outputFile:'reports/unified-contract-browser.json'}]],outputDir:'reports/unified-contract-browser-artifacts'});
