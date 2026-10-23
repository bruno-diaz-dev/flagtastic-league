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

test("the active image import loads OCR before reading the grid and submits the selected week", async () => {
    const {scripts,context} = setup();
    vm.runInContext(fs.readFileSync('static/schedule_ocr_cells.js','utf8'),context);
    let canvasReads=0, workers=0, terminated=0, payload;
    context.scheduleSourceCanvas=async()=>{canvasReads++;return {width:1200,height:100};};
    context.scheduleGridLines=()=>[0,100];
    context.prepareScheduleCell=()=>({blank:false});
    context.recognizeScheduleCells=async(worker,canvas,cells,options)=>new Map(
        cells.map(cell=>[cell.key,options.whitelist ? '12:00' : cell.key.endsWith(':home') ? 'Nómadas U8' : 'Lobos U8'])
    );
    context.fetch=async(url,options)=>{assert.equal(url,'/api/games/schedule/analyze-cells');payload=JSON.parse(options.body);return {ok:true};};
    const messages=[];
    const first=context.window.analyzeScheduleImageCells('original.jpeg','4',message=>messages.push(message));
    assert.equal(scripts.length,1);
    assert.equal(canvasReads,0,'grid analysis waits for the OCR download');
    assert.match(messages[0],/Cargando lector/);
    context.window.Tesseract={async createWorker(){workers++;return {async terminate(){terminated++;}};}};
    scripts[0].onload();
    assert.equal((await first).ok,true);
    assert.equal(workers,1);assert.equal(terminated,1);
    assert.equal(payload.week,4);
    assert.equal(payload.rows.length,6);
    assert.deepEqual(payload.rows[0],{field_number:1,start_time:'12:00',home_team:'Nómadas U8',away_team:'Lobos U8'});
    await context.window.analyzeScheduleImageCells('second.jpeg','4',()=>{});
    assert.equal(scripts.length,1,'the next image reuses the downloaded reader');
    assert.equal(terminated,2);
});

test("an image import can retry after the reader fails to download", async () => {
    const {scripts,context}=setup();
    vm.runInContext(fs.readFileSync('static/schedule_ocr_cells.js','utf8'),context);
    const first=context.window.analyzeScheduleImageCells('original.jpeg','4',()=>{});
    scripts[0].onerror();
    await assert.rejects(first,/No se pudo descargar/);
    let reachedGrid=false;
    context.scheduleSourceCanvas=async()=>{reachedGrid=true;throw new Error('grid reached');};
    const retry=context.window.analyzeScheduleImageCells('original.jpeg','4',()=>{});
    assert.equal(scripts.length,2);
    context.window.Tesseract={};scripts[1].onload();
    await assert.rejects(retry,/grid reached/);
    assert.equal(reachedGrid,true);
});
