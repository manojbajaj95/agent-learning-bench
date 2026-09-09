import { createRequire } from "node:module";
import { appendFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const require = createRequire(
  process.env.WEBARENA_WEBCMD_PACKAGE
    || "/usr/local/lib/node_modules/@agentrhq/webcmd/package.json",
);
const { chromium } = require("playwright-core");

const endpoint = process.argv[2];
const jsonlPath = process.argv[3];
if (!endpoint || !jsonlPath) {
  console.error("usage: har_recorder.mjs CDP_ENDPOINT JSONL_PATH");
  process.exit(1);
}
mkdirSync(dirname(jsonlPath), { recursive: true });

function record(event) {
  appendFileSync(jsonlPath, `${JSON.stringify(event)}\n`);
}

function attachContext(context) {
  context.on("response", (response) => {
    const request = response.request();
    record({
      url: request.url(),
      method: request.method(),
      headers: request.headers(),
      postData: request.postData() || "",
      status: response.status(),
      statusText: response.statusText(),
      startedDateTime: new Date().toISOString(),
    });
  });
}

const browser = await chromium.connectOverCDP(endpoint);
for (const context of browser.contexts()) attachContext(context);
browser.on("context", attachContext);

await new Promise(() => {});
