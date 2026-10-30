const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'tests/browser',testMatch:'history_overlay.spec.cjs',workers:1,
 timeout:30000,retries:0,expect:{timeout:7000},
 projects:['chromium','firefox'].map(browserName=>({name:browserName,use:{browserName,viewport:{width:1440,height:1080},timezoneId:'UTC'}})),
 reporter:[['list'],['json',{outputFile:'reports/history-browser.json'}]],outputDir:'reports/history-browser-artifacts'});
