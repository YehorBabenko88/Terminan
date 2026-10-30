const {defineConfig}=require('@playwright/test');
const {execFileSync}=require('node:child_process');
const git=(cwd,arg)=>execFileSync('git',['-C',cwd,'rev-parse',arg],{encoding:'utf8'}).trim();
module.exports=defineConfig({testDir:'tests/browser',testMatch:'math_lab.spec.cjs',workers:1,timeout:30000,retries:0,
 metadata:{source_head:git('.','HEAD'),source_tree:git('.','HEAD^{tree}'),math_head:process.env.MATH_REPO?git(process.env.MATH_REPO,'HEAD'):null,started_utc:new Date().toISOString()},
 projects:['chromium','firefox'].map(browserName=>({name:browserName,use:{browserName,viewport:{width:1500,height:1050}}})),
 reporter:[['list'],['json',{outputFile:'reports/math-browser.json'}]],outputDir:'reports/math-browser-artifacts'});
