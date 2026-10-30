const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'tests/browser',testMatch:'math_lab.spec.cjs',workers:1,timeout:30000,retries:0,
 projects:['chromium','firefox'].map(browserName=>({name:browserName,use:{browserName,viewport:{width:1500,height:1050}}})),
 reporter:[['list'],['json',{outputFile:'reports/math-browser.json'}]],outputDir:'reports/math-browser-artifacts'});
