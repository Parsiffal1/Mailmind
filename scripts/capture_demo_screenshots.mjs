import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";

const chromePath = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const outputDir = path.resolve("docs/demo/screenshots");
const remotePort = 9222;
const baseUrl = "http://127.0.0.1:8000/?demo=1";

await fs.mkdir(outputDir, { recursive: true });

const chrome = spawn(chromePath, [
  "--headless=new",
  `--remote-debugging-port=${remotePort}`,
  "--disable-gpu",
  "--no-first-run",
  "--no-default-browser-check",
  "--window-size=1600,1000",
  "about:blank",
], { stdio: "ignore" });

try {
  await waitForDevtools();
  const tab = await createTab();
  const client = await connectCdp(tab.webSocketDebuggerUrl);

  await send(client, "Page.enable");
  await send(client, "Runtime.enable");
  await send(client, "Page.navigate", { url: baseUrl });
  await delay(2500);
  await screenshot(client, "01_tasks_overview.png");

  await clickTab(client, "Documents");
  await delay(500);
  await send(client, "Runtime.evaluate", {
    expression: `
      (() => {
        const input = document.querySelector('.aiSearchBar input');
        if (!input) return;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, 'What actions need attention this week?');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.form?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      })()
    `,
  });
  await waitForSelector(client, ".aiAnswerPanel:not(.loadingPanel)", 5000);
  await delay(500);
  await screenshot(client, "02_ai_search_answer.png");

  await delay(900);
  await screenshot(client, "03_indexed_sources.png");

  await clickTab(client, "Settings");
  await delay(900);
  await screenshot(client, "04_settings.png");

  await send(client, "Runtime.evaluate", {
    expression: "window.scrollTo(0, document.body.scrollHeight)",
    awaitPromise: false,
  });
  await delay(500);
  await screenshot(client, "05_settings_privacy_rag.png");

  client.close();
} finally {
  chrome.kill();
}

async function waitForDevtools() {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      await fetch(`http://127.0.0.1:${remotePort}/json/version`);
      return;
    } catch {
      await delay(250);
    }
  }
  throw new Error("Chrome DevTools endpoint did not start.");
}

async function createTab() {
  const response = await fetch(`http://127.0.0.1:${remotePort}/json/new?${encodeURIComponent("about:blank")}`, {
    method: "PUT",
  });
  if (!response.ok) {
    throw new Error(`Could not create Chrome tab: ${response.status}`);
  }
  return response.json();
}

function connectCdp(url) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    const callbacks = new Map();
    let nextId = 1;

    socket.addEventListener("open", () => {
      resolve({
        close: () => socket.close(),
        sendCommand(method, params = {}) {
          const id = nextId++;
          socket.send(JSON.stringify({ id, method, params }));
          return new Promise((res, rej) => callbacks.set(id, { res, rej }));
        },
      });
    });
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !callbacks.has(message.id)) return;
      const callback = callbacks.get(message.id);
      callbacks.delete(message.id);
      if (message.error) callback.rej(new Error(message.error.message));
      else callback.res(message.result);
    });
    socket.addEventListener("error", reject);
  });
}

function send(client, method, params) {
  return client.sendCommand(method, params);
}

async function clickTab(client, label) {
  await send(client, "Runtime.evaluate", {
    expression: `
      (() => {
        const tab = Array.from(document.querySelectorAll('.tab')).find((node) => node.textContent.includes('${label}'));
        if (tab) tab.click();
      })()
    `,
  });
}

async function waitForSelector(client, selector, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await send(client, "Runtime.evaluate", {
      expression: `Boolean(document.querySelector(${JSON.stringify(selector)}))`,
      returnByValue: true,
    });
    if (result.result?.value) return;
    await delay(150);
  }
  throw new Error(`Timed out waiting for selector: ${selector}`);
}

async function screenshot(client, filename) {
  const result = await send(client, "Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: false,
    fromSurface: true,
  });
  await fs.writeFile(path.join(outputDir, filename), Buffer.from(result.data, "base64"));
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
