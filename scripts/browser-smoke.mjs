import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Use a fresh browser context: test records never share the user's session.
export async function runSmoke(browser, base = "http://localhost:8000") {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
  });
  const page = await context.newPage();
  const errors = [];
  const steps = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const input = page.locator("#text-input");
  const waitIdle = () =>
    page.waitForFunction(
      () => !document.querySelector("#analyze-button").disabled,
    );
  const analyze = async (text, save = false) => {
    await input.fill(text);
    await page.locator("#save-analysis").setChecked(save);
    await page.locator("#analyze-button").click();
    await waitIdle();
    assert.notEqual(await page.locator("#word-count").textContent(), "—");
  };
  try {
    await page.goto(base);
    await page.locator("#refresh-history").waitFor({ state: "visible" });
    await page.locator("#analyze-button").click();
    assert.equal(await input.getAttribute("aria-invalid"), "true");
    await input.fill("Keep this original draft.");
    await page.locator("#sample-button").click();
    await page.locator("#undo-button").click();
    assert.equal(await input.inputValue(), "Keep this original draft.");
    await page.locator("#clear-button").click();
    await page.locator("#undo-button").click();
    assert.equal(await input.inputValue(), "Keep this original draft.");
    steps.push("inline validation and undo");

    await page.locator("#file-input").setInputFiles({
      name: "draft.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Imported UTF-8 text. Сәлем 👋"),
    });
    await page.waitForFunction(() =>
      document.querySelector("#text-input").value.startsWith("Imported"),
    );
    await waitIdle();
    const imported = await input.inputValue();
    await page.locator("#file-input").setInputFiles({
      name: "broken.txt",
      mimeType: "text/plain",
      buffer: Buffer.from([0xc3, 0x28]),
    });
    await waitIdle();
    assert.equal(await input.inputValue(), imported);
    await input.fill("👋".repeat(10001));
    assert.match(await page.locator("#input-counter").textContent(), /10,001/);
    assert.equal(await input.getAttribute("aria-invalid"), "false");
    steps.push("local UTF-8 import and Unicode character counting");

    await analyze("Python makes this saved draft searchable.", true);
    await page.locator(".history-item").first().waitFor();
    await page.route("**/api/text/analyze/", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 350));
      await route.continue();
    });
    await input.fill("Java belongs in another saved draft.");
    await page.locator("#analyze-button").click();
    assert.equal(await page.locator("#clear-history").isDisabled(), true);
    await waitIdle();
    await page.unroute("**/api/text/analyze/");
    await page.waitForFunction(
      () => document.querySelectorAll(".history-item").length === 2,
    );
    await page.locator("#history-search").fill("Python");
    await page
      .locator("#history-search-form")
      .getByRole("button", { name: "Search", exact: true })
      .click();
    await page.waitForFunction(
      () => document.querySelectorAll(".history-item").length === 1,
    );
    assert.match(
      await page.locator(".history-preview").textContent(),
      /Python/,
    );
    await page.locator(".restore-button").click();
    assert.match(await input.inputValue(), /^Python/);
    steps.push("save, search, restore, and save/delete serialization");

    await input.fill("Hello world!");
    for (const [operation, expected] of [
      ["uppercase", "HELLO WORLD!"],
      ["lowercase", "hello world!"],
      ["titlecase", "Hello World!"],
      ["slug", "hello-world"],
      ["compact_whitespace", "Hello world!"],
    ]) {
      await page.locator(`[data-operation="${operation}"]`).click();
      await waitIdle();
      assert.equal(await page.locator("#result-text").inputValue(), expected);
    }
    await page.locator('[data-operation="uppercase"]').click();
    await waitIdle();
    assert.equal(
      await page.locator("#result-text").inputValue(),
      "HELLO WORLD!",
    );
    const downloadEvent = page.waitForEvent("download");
    await page.locator("#download-button").click();
    const downloaded = await downloadEvent;
    assert.equal(
      await readFile(await downloaded.path(), "utf8"),
      "HELLO WORLD!",
    );
    await page.locator("#use-result-button").click();
    assert.equal(await input.inputValue(), "HELLO WORLD!");
    await page.locator("#undo-button").click();
    assert.equal(await input.inputValue(), "Hello world!");
    await page.locator("#save-analysis").uncheck();
    await input.press("Control+Enter");
    await waitIdle();
    assert.equal(await page.locator("#word-count").textContent(), "2");
    const exportEvent = page.waitForEvent("download");
    await page.locator("#export-button").click();
    const exported = await exportEvent;
    const report = JSON.parse(await readFile(await exported.path(), "utf8"));
    assert.equal(report.result.word_count, 2);
    await input.fill("Another draft");
    assert.equal(await page.locator("#export-button").isDisabled(), true);
    steps.push(
      "transform, download, keyboard shortcut, and fresh analysis export",
    );

    await input.fill("ß".repeat(20000));
    await page.locator('[data-operation="uppercase"]').click();
    await waitIdle();
    assert.equal(
      (await page.locator("#result-text").inputValue()).length,
      40000,
    );
    await page.locator("#use-result-button").click();
    assert.equal((await input.inputValue()).length, 20000);
    steps.push("oversized transformation preserves the original draft");

    await page.locator("#clear-history").click();
    await page.locator("#confirm-dialog").waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    assert.equal(await page.locator(".history-item").count(), 1);
    await page.locator("#clear-history").click();
    await page.locator("#confirm-action").click();
    await page.waitForFunction(
      () => document.querySelectorAll(".history-item").length === 0,
    );
    await page.locator("#history-search").fill("");
    await page
      .locator("#history-search-form")
      .getByRole("button", { name: "Search", exact: true })
      .click();
    await page.waitForFunction(
      () => !document.querySelector("#refresh-history").disabled,
    );
    assert.equal(await page.locator("#history-count").textContent(), "0 saved");
    steps.push("confirmed bulk deletion includes hidden search results");

    await page.locator("#sample-button").click();
    await page.locator("#save-analysis").check();
    await page.locator("#analyze-button").click();
    await waitIdle();
    await page.locator(".history-item").first().waitFor();
    await mkdir(path.join(root, "docs/screenshots"), { recursive: true });
    await page.locator("#dismiss-notice").click();
    await page.screenshot({
      path: path.join(root, "docs/screenshots/workspace-desktop.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await page.screenshot({
      path: path.join(root, "docs/screenshots/workspace-mobile.png"),
      fullPage: true,
    });
    steps.push("desktop and mobile layouts");
    assert.deepEqual(errors, []);
    return { passed: true, steps, browserErrors: errors };
  } finally {
    await context.close();
  }
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.BROWSER_CHANNEL
      ? { channel: process.env.BROWSER_CHANNEL }
      : {}),
  });
  try {
    console.log(
      JSON.stringify(await runSmoke(browser, process.env.APP_URL), null, 2),
    );
  } finally {
    await browser.close();
  }
}
