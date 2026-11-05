const {defineConfig}=require('@playwright/test');const path=require('node:path');
const root=process.env.LAB_VIEW_EVIDENCE_ROOT||'reports/lab-view-ci';
module.exports=defineConfig({testDir:'tests/browser',testMatch:'**/lab-view.spec.cjs',timeout:45000,expect:{timeout:8000},workers:1,retries:0,reporter:[['list'],['json',{outputFile:path.resolve(root,'browser.json')}]],outputDir:path.resolve(root,'results'),projects:[{name:'chromium-lab-view',use:{browserName:'chromium'}}]});
