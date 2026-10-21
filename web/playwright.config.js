import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
export default defineConfig({
  testDir: "./browser",
  workers: 1,
  timeout: 45000,
  use: { baseURL: "http://127.0.0.1:3000", trace: "retain-on-failure" },
  reporter: "list",
  outputDir: "./test-output/results",
  webServer: {
    command: "node server.js",
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    url: "http://127.0.0.1:3000/health",
    reuseExistingServer: false,
    env: {
      NODE_ENV: "development",
      APP_URL: "http://127.0.0.1:3000",
      SETUP_TOKEN: "browser-test-private-setup-token-32-characters",
      PORT: "3000",
    },
  },
});
