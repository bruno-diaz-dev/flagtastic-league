const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '../..');
const XLSX = require(path.join(root, 'static/vendor/xlsx-0.20.3.min.js'));
const context = vm.createContext({File, Error, setTimeout, clearTimeout});
vm.runInContext(fs.readFileSync(path.join(root, 'static/statistics_upload.js'), 'utf8'), context);

test('oversized and invalid source files fail before starting a worker', async () => {
    await assert.rejects(context.prepareStatisticsUpload({name:'test.xlsx',size:16*1024*1024}), /15 MB/);
    await assert.rejects(context.prepareStatisticsUpload({name:'test.csv',size:10}), /xlsx/);
    const file = new File(['test'], 'test.xlsx');
    assert.equal(await context.prepareStatisticsUpload(file), file);
});

test('plain-text platform 413 is reported as a size error', async () => {
    await assert.rejects(context.readStatisticsImportResponse(new Response('FUNCTION_PAYLOAD_TOO_LARGE',{status:413})), /limite de carga/);
    await assert.rejects(context.readStatisticsImportResponse(new Response('Bad gateway',{status:502})), /servidor falló/);
    await assert.rejects(context.readStatisticsImportResponse(new Response(JSON.stringify({detail:'Equipo desconocido'}),{status:422})), /Equipo desconocido/);
});

test('worker preserves source positions, zeroes and cached formulas, removing helper columns', () => {
    const workbook = XLSX.utils.book_new();
    const sheet = XLSX.utils.aoa_to_sheet([['Equipo','Categoria','Estadistica',0],[],['Test','U8','TD',4]]);
    sheet.E3 = {t:'n',v:7,f:'3+4'};
    sheet.BB3 = {t:'n',v:999};
    sheet['!ref'] = 'A1:BB3';
    XLSX.utils.book_append_sheet(workbook, sheet, 'Wk 1');
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([['ignore']]), 'Summary');
    let result;
    const worker = {postMessage: value => {result=value;}};
    const workerContext = vm.createContext({XLSX, self:worker, importScripts:()=>{}});
    vm.runInContext(fs.readFileSync(path.join(root,'static/statistics_upload_worker.js'),'utf8'),workerContext);
    worker.onmessage({data:XLSX.write(workbook,{type:'array',bookType:'xlsx'})});
    assert.equal(result.error,undefined);
    const output=XLSX.read(result.bytes,{type:'array'});
    assert.deepEqual(output.SheetNames,['Wk 1']);
    assert.equal(output.Sheets['Wk 1'].D1.v,0);
    assert.equal(output.Sheets['Wk 1'].D3.v,4);
    assert.equal(output.Sheets['Wk 1'].E3.v,7);
    assert.equal(output.Sheets['Wk 1'].E3.f,undefined);
    assert.equal(output.Sheets['Wk 1'].BB3,undefined);
});


test('file read failures explain local access rather than claiming a network failure', async () => {
    await assert.rejects(context.prepareStatisticsUpload({
        name: 'mobile.xlsx', size: 1024 * 1024,
        arrayBuffer: async () => {throw new TypeError('Read failed');}
    }), /leer el archivo del dispositivo/);
});

test('worker drops unused Wk templates without collapsing blank rows in populated sheets', () => {
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([
        ['Equipo', 'Categoria', 'Estadistica'], [], ['Storms', 'Mix Libre', 'TD', 0, '', 8]
    ]), 'Wk 1');
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([
        ['Equipo', 'Categoria', 'Estadistica'], [null, null, 'Intentos Pase'], [null, null, 'TD']
    ]), 'Wk 2');
    let result;
    const worker = {postMessage: value => {result = value;}};
    vm.runInNewContext(fs.readFileSync(path.join(root, 'static/statistics_upload_worker.js'), 'utf8'), {XLSX, self: worker, importScripts: () => {}});
    worker.onmessage({data: XLSX.write(workbook, {type: 'array', bookType: 'xlsx'})});
    assert.equal(result.error, undefined);
    const output = XLSX.read(result.bytes, {type: 'array'});
    assert.deepEqual(output.SheetNames, ['Wk 1']);
    assert.equal(output.Sheets['Wk 1'].D3.v, 0);
    assert.equal(output.Sheets['Wk 1'].F3.v, 8);
    assert.equal(output.Sheets['Wk 1'].A2, undefined);
});

test('worker also preserves compact and single-sheet import layouts', () => {
    for (const name of ['Estadisticas', 'Hoja1']) {
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([
            ['rama', 'categoria', 'equipo', 'numero'], ['mixto', 'libre', 'Storms', 8]
        ]), name);
        let result;
        const worker = {postMessage: value => {result = value;}};
        vm.runInNewContext(fs.readFileSync(path.join(root, 'static/statistics_upload_worker.js'), 'utf8'), {XLSX, self: worker, importScripts: () => {}});
        worker.onmessage({data: XLSX.write(workbook, {type: 'array', bookType: 'xlsx'})});
        assert.equal(result.error, undefined);
        const output = XLSX.read(result.bytes, {type: 'array'});
        assert.deepEqual(output.SheetNames, [name]);
        assert.equal(output.Sheets[name].D2.v, 8);
    }
});
