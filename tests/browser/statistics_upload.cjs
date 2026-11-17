const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const XLSX = require('../../static/vendor/xlsx-0.20.3.min.js');

function largeWorkbook() {
    const labels = ['Intentos Pase','Completos Pase','Para % pases','Puntos Pase',
        '6 Puntos','2 Puntos','1 Puntos','Intercepciones Pase','TD','Conv 1',
        'Conv 2','Sacks','Tacleo','Intercepciones Def','Asistencia'];
    const rows = [['Equipo','Categoria','Estadistica']];
    for (const team of ['Upload Home','Upload Away']) {
        for (const label of labels) {
            const events = team === 'Upload Home'
                ? ({'Intentos Pase':[0],'Para % pases':[0],'Completos Pase':[8],'TD':[8],'Asistencia':[0,8]}[label] || []) : [];
            rows.push([team,'Mix Libre',label,...events]);
        }
    }
    const book = XLSX.utils.book_new();
    const sheet = XLSX.utils.aoa_to_sheet(rows);
    sheet.BB2 = {t:'n',v:999};sheet['!ref']='A1:BB31';
    XLSX.utils.book_append_sheet(book,sheet,'Wk 1');
    XLSX.utils.book_append_sheet(book,XLSX.utils.aoa_to_sheet([
        ['Equipo','Categoria','Estadistica'],...labels.map(label=>[0,0,label,0])
    ]),'Wk 2');
    const archive = XLSX.CFB.read(XLSX.write(book,{type:'buffer',bookType:'xlsx'}),{type:'buffer'});
    // Harmless non-statistical content makes this a real XLSX above 15 MiB.
    XLSX.CFB.utils.cfb_add(archive,'xl/media/unused.bin',Buffer.alloc(16*1024*1024));
    return Buffer.from(XLSX.CFB.write(archive,{type:'buffer',fileType:'zip',compression:false}));
}

(async () => {
    const fixturePath=process.env.STATISTICS_UPLOAD_FIXTURE;
    const source=fixturePath ? fs.readFileSync(fixturePath) : largeWorkbook();
    assert.ok(source.length>15*1024*1024 && source.length<32*1024*1024);
    const template=fs.readFileSync('templates/statistics.html','utf8');
    const content=template.split('{% block content %}')[1].split('{% endblock %}')[0];
    const scripts=template.split('{% block scripts %}')[1].split('{% endblock %}')[0];
    let received,requestError,release;
    const receivedRequest=new Promise(resolve=>{release=resolve;});
    const server=http.createServer(async (req,res) => {
        const path=new URL(req.url,'http://localhost').pathname;
        const json=value=>{res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
        try {
            if(path.startsWith('/static/')) {
                res.writeHead(200,{'Content-Type':path.endsWith('.css')?'text/css':'application/javascript'});
                return fs.createReadStream('.'+path).pipe(res);
            }
            if(path==='/api/statistics/leaderboards')return json(Object.fromEntries(['points','receptions','tackles','interceptions','sacks','completion_percentage'].map(metric=>[metric,[]])));
            if(path==='/api/statistics/import') {
                const buffers=[];for await(const chunk of req)buffers.push(chunk);
                const body=Buffer.concat(buffers),boundary=req.headers['content-type'].match(/boundary=(.*)$/)[1];
                const header=body.indexOf(Buffer.from('name="file"; filename="Stats ALL.xlsx"'));
                assert.ok(header>=0,'original filename is retained');
                const start=body.indexOf(Buffer.from('\r\n\r\n'),header)+4;
                const end=body.indexOf(Buffer.from('\r\n--'+boundary),start);
                received=body.subarray(start,end);
                assert.ok(received.length<=1000*1024,'prepared upload stays below the spool threshold');
                assert.ok(body.length<1024*1024,'whole multipart request fits below 1 MiB');
                assert.match(body.toString('latin1'),/name="existing_records"\r\n\r\npreserve/);
                const prepared=XLSX.read(received,{type:'buffer'});
                if(!fixturePath) {
                    assert.deepEqual(prepared.SheetNames,['Wk 1']);
                    assert.equal(prepared.Sheets['Wk 1'].D2.v,0);
                    assert.equal(prepared.Sheets['Wk 1'].D4.v,0);
                    assert.equal(prepared.Sheets['Wk 1'].D10.v,8);
                    assert.equal(prepared.Sheets['Wk 1'].BB2,undefined);
                }
                release();return json({imported:2,created:2,updated:0,weeks:[1],skipped:[]});
            }
            res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});
            res.end(`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/ui.css"></head><body class="role-league_admin"><main class="content">${content}</main>${scripts}</body></html>`);
        } catch(error) {requestError=error;release();res.writeHead(500);res.end('Mock upload assertion failed');}
    });
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
    const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    try {
        await page.goto(`http://127.0.0.1:${server.address().port}/statistics`);
        await page.getByText('Cargar estadísticas individuales',{exact:false}).click();
        await page.locator('#statistics-import-mode').selectOption('all');
        await page.locator('#statistics-import-form [name=file]').setInputFiles({
            name:'Stats ALL.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:source
        });
        await page.locator('#statistics-import-form button[type=submit]').click();
        let receiveTimeout;
        try {
            await Promise.race([receivedRequest,new Promise((_,reject)=>{
                receiveTimeout=setTimeout(()=>reject(new Error('No prepared upload reached the local server')),45000);
            })]);
        } finally {clearTimeout(receiveTimeout);}
        if(requestError)throw requestError;
        await page.waitForFunction(()=>document.querySelector('#statistics-import-message').textContent.includes('registros procesados'));
        assert.equal(await page.locator('#statistics-import-form button[type=submit]').isEnabled(),true);
        assert.deepEqual(errors,[]);
        console.log(JSON.stringify({original_bytes:source.length,uploaded_bytes:received.length,real_worker:true,original_form:true}));
    } finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exit(1);});
