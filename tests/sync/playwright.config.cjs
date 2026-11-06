const { defineConfig } = require("@playwright/test");
module.exports = defineConfig({
  testDir: __dirname,
  testMatch: "test_browser.spec.cjs",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8896",
    browserName: "chromium",
    viewport: { width: 1440, height: 1000 },
    colorScheme: "dark",
    locale: "en-US",
    timezoneId: "UTC",
  },
  snapshotPathTemplate: "{testDir}/snapshots/{arg}{ext}",
  outputDir: "../../test-results/sync",
  webServer: {
    cwd: require("node:path").join(__dirname, "../.."),
    command: "python terminan/sync/serve.py --port 8896",
    url: "http://127.0.0.1:8896/sync.html",
    reuseExistingServer: false,
    timeout: 15000,
  },
});
