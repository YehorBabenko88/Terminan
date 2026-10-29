const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'tests/browser',testMatch:'consumer.spec.cjs',workers:1,retries:0,
  use:{browserName:'chromium'},
  webServer:{command:'python -m terminan',url:'http://127.0.0.1:18765',reuseExistingServer:false,env:{TERMINAN_PORT:'18765',TERMINAN_STRATTESTER_DB:'',TERMINAN_RESULTS_DB:'',TERMINAN_GRID_DSN:''}},
});
