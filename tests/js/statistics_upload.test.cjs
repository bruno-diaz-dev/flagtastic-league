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
    await assert.rejects(context.readStatisticsImportResponse(new Response('Bad gateway',{status:502})), /No se pudo importar/);
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
