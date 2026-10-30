const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
  testDir:'tests/browser',testIgnore:['**/math_lab.spec.cjs','**/r3.spec.cjs','**/r4.spec.cjs','**/saved.spec.cjs'],timeout:45000,expect:{timeout:10000},workers:1,
  retries:0,reporter:[['list'],['json',{outputFile:'reports/r2-browser.json'}]],
  outputDir:'test-results',
  projects:['chromium','firefox'].flatMap(browserName=>[1,1.5,2].map(dpr=>({
    name:browserName+'-dpr'+dpr,use:{browserName,deviceScaleFactor:dpr,viewport:{width:1440,height:1100},locale:'en-US',timezoneId:'UTC'}
  })))
});
