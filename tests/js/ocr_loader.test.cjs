const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function setup() {
    const scripts = [];
    const context = vm.createContext({
        window: {},
        document: {
            createElement: () => ({remove() { this.removed = true; }}),
            head: {appendChild: script => scripts.push(script)}
        }
    });
    vm.runInContext(fs.readFileSync("static/ocr_loader.js", "utf8"), context);
    return {scripts, context};
}

test("OCR loads only on demand and shares concurrent downloads", async () => {
    const {scripts, context} = setup();
    assert.equal(scripts.length, 0);
    const first = context.loadScheduleOcr();
    assert.equal(context.loadScheduleOcr(), first);
    assert.equal(scripts.length, 1);
    assert.equal(scripts[0].async, true);
    context.window.Tesseract = {recognize() {}};
    scripts[0].onload();
    assert.equal(await first, context.window.Tesseract);
    assert.equal(await context.loadScheduleOcr(), context.window.Tesseract);
    assert.equal(scripts.length, 1);
});

test("failed OCR download can be retried", async () => {
    const {scripts, context} = setup();
    const failed = context.loadScheduleOcr();
    scripts[0].onerror();
    await assert.rejects(failed, /No se pudo descargar/);
    assert.equal(scripts[0].removed, true);
    const retry = context.loadScheduleOcr();
    assert.equal(scripts.length, 2);
    context.window.Tesseract = {};
    scripts[1].onload();
    await retry;
});
