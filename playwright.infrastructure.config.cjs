const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'tests/browser',testMatch:'infrastructure.spec.cjs',workers:1,reporter:'list',use:{browserName:'chromium'}});
