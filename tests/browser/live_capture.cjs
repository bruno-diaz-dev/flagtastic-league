const {chromium} = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

(async () => {
    const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
    const context = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const page = await context.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    let offline=true;let role='referee';let correctionVersion=0;const plays=new Map();
    const roster=[{team_id:1,player_id:10,jersey_number:10,display_name:'Ana'},{team_id:1,player_id:7,jersey_number:7,display_name:'Eva'},{team_id:1,player_id:12,jersey_number:12,display_name:'Luz'},{team_id:2,player_id:20,jersey_number:20,display_name:'María'}];
    const snapshot=()=>({game_id:5,state:'live',version:plays.size+correctionVersion,home_team:{id:1,name:'Tigres'},away_team:{id:2,name:'Lobos'},home_score:[...plays.values()].filter(p=>p.kind==='extra_one').length,away_score:0,roster,attendance:roster.map(r=>({...r,present:[...plays.values()].some(p=>p.kind==='attendance'&&p.player_id===r.player_id),attended_games:0,required_games:5})),statistics:[],events:[...plays.values()].filter(p=>p.kind!=='attendance').map((p,i)=>({...p,id:i+1,player_label:'#'+(roster.find(r=>r.player_id===p.player_id)?.jersey_number||''),receiver_label:p.receiver_id?'#7 Eva':null,voided_at:p.voided_at || null}))});
    await page.route('https://capture.test/**',async route=>{
        const u=new URL(route.request().url());
        if(u.pathname==='/') {
            const panel=fs.readFileSync('templates/live_game_panel.html','utf8');
            await route.fulfill({contentType:'text/html',body:`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/ui.css"><link rel="stylesheet" href="/static/live_game.css"></head><body><main class="content"><section class="game-detail-page" data-game-id="5"><section id="game-score"></section>${panel}</section></main><script>function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}</script><script src="/static/live_capture_queue.js"></script><script src="/static/live_pass_chart.js"></script><script src="/static/live_field.js"></script><script src="/static/live_game.js"></script></body></html>`});
        } else if(u.pathname.startsWith('/static/')) {
            await route.fulfill({contentType:u.pathname.endsWith('.css')?'text/css':'application/javascript',body:fs.readFileSync('.'+u.pathname,'utf8')});
        } else if(u.pathname==='/api/auth/me') {
            await route.fulfill({json:{id:12,role,roles:[role]}});
        } else if(route.request().method()==='POST') {
            if(offline)await route.abort('failed');
            else {const p=route.request().postDataJSON();plays.set(p.client_id,p);await route.fulfill({status:201,json:{id:plays.size}});}
        } else await route.fulfill({json:snapshot()});
    });
    await page.goto('https://capture.test/');
    await page.locator('#live-capture-panel[open]').waitFor();
    await page.locator('[data-live-player="10"][data-live-field="player_id"]').click();
    assert.equal(await page.locator('#live-passer-choices').getAttribute('open'),null);
    await page.locator('[data-live-player="7"][data-live-field="receiver_id"]').click();
    await page.waitForFunction(()=>document.querySelector('#live-queue-status').textContent.includes('1 jugada'));
    await page.locator('[data-live-kind="extra_one"]').click();
    await page.locator('[data-live-player="7"][data-live-field="player_id"]').click();
    await page.waitForFunction(()=>document.querySelector('#live-queue-status').textContent.includes('2 jugadas'));
    assert.equal(plays.size,0);
    assert.equal(await page.locator('#live-home-score').textContent(),'0');
    assert.equal(await page.locator('#live-finish').isDisabled(),true);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
    await page.evaluate(()=>scrollTo(0,0));
    await page.screenshot({path:'mobile-capture.png',fullPage:true});
    await page.reload();
    await page.waitForFunction(()=>document.querySelector('#live-queue-status').textContent.includes('2 jugadas'));
    offline=false;
    // Automatic recovery can empty and hide the outbox before locator actionability.
    await page.evaluate(()=>document.querySelector('#live-retry').click());
    await page.waitForFunction(()=>document.querySelector('#live-queue-status').textContent.includes('Todo enviado')).catch(async error=>{
        console.log('CAPTURE_DIAGNOSTIC',JSON.stringify({accepted:plays.size,errors,state:await page.evaluate(()=>({status:document.querySelector('#live-queue-status').textContent,message:document.querySelector('#live-operation-message').textContent,rows:liveQueue?.rows,working:liveQueue?.working,liveState:liveData?.state,online:navigator.onLine}))}));
        throw error;
    });
    await page.waitForFunction(()=>document.querySelector('#live-home-score').textContent==='1');
    assert.equal(plays.size,2);
    assert.equal(await page.locator('.live-event').count(),2);
    await page.locator('[data-live-field-event="1"]').click();
    assert.equal(await page.locator('#live-field-panel').getAttribute('data-event-id'),'1');
    assert.ok(await page.locator('.live-field-route').getAttribute('d').then(d=>d.includes(' Q ')));
    assert.equal(await page.locator('animateMotion').count(),1);
    // A confirmed touchdown is visual only; no additional capture request is needed.
    plays.set('visual-td',{...plays.values().next().value,client_id:'visual-td',kind:'touchdown',receiver_id:null});
    await page.evaluate(()=>refreshLive(true));
    await page.waitForFunction(()=>document.querySelector('#live-field-stage').textContent.includes('TOUCHDOWN'));
    assert.ok(await page.locator('.live-field-route').getAttribute('d').then(d=>d.includes(' L ')));
    await page.waitForFunction(()=>document.querySelector('#live-field-stage svg').getCurrentTime()>1.5);
    await page.locator('#live-field-panel').screenshot({path:'mobile-field-touchdown.png'});
    // The sticky score must not cover the field, even after timeline replay scrolls it.
    assert.equal(await page.evaluate(()=>{
        const field=document.querySelector('#live-field-stage').getBoundingClientRect();
        const top=document.elementFromPoint(field.left+field.width/2,field.top+field.height/2);
        return Boolean(top?.closest('#live-field-panel'));
    }),true);
    plays.set('visual-td',{...plays.get('visual-td'),voided_at:'2026-10-05'});correctionVersion++;
    await page.evaluate(()=>refreshLive(true));
    await page.waitForFunction(()=>!document.querySelector('#live-field-stage').textContent.includes('TOUCHDOWN'));
    assert.equal(await page.locator('[data-live-field-event="3"]').count(),0);
    // Retain the voided audit record while subsequent events advance the version.

    await page.locator('[data-live-moment="halftime"]').click();
    await page.waitForFunction(()=>document.querySelector('#live-timeline').textContent.includes('Medio tiempo'));
    await page.locator('[data-live-moment="two_minute_warning"]').click();
    await page.waitForFunction(()=>document.querySelector('#live-timeline').textContent.includes('Pausa de los 2 minutos'));
    await page.locator('#live-attendance-panel summary').click();
    await page.locator('[data-live-attendance="10"]').click();
    await page.waitForFunction(()=>document.querySelector('#live-attendance').textContent.includes('Presente en este juego'));
    assert.equal(await page.locator('#live-timeline').textContent().then(t=>t.includes('Asistencia')),false);
    assert.equal(plays.size,6);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.locator('#live-field-replay').click();
    assert.equal(await page.locator('animateMotion').count(),0);
    // Optional placement suppresses automatic dorsal submission; both points persist in the outbox.
    await page.locator('[data-live-kind="pass_complete"]').click();
    await page.locator('#live-location-panel summary').click();
    const before=plays.size;
    // Reload intentionally clears the in-memory passer selection. Select it explicitly.
    await page.locator('[data-live-player="10"][data-live-field="player_id"]').click();
    await page.locator('[data-live-player="7"][data-live-field="receiver_id"]').click();
    assert.equal(plays.size,before);
    await page.locator('#live-location-editor').click({position:{x:150,y:190}});
    await page.locator('#live-location-editor').click({position:{x:80,y:50}});
    await page.locator('#live-save-play').click();
    await page.waitForFunction(()=>document.querySelector('#live-queue-status').textContent.includes('Todo enviado'));
    await page.waitForFunction(()=>document.querySelector('#live-map-count').textContent.startsWith('1 de')).catch(async error=>{console.log('LOCATION_DIAGNOSTIC',JSON.stringify({plays:[...plays.values()],errors,state:await page.evaluate(()=>({message:liveMessage.textContent,selection:liveCapturePayload(),location:LiveLocationCapture.read(liveForm.elements.kind.value),status:document.querySelector('#live-map-count').textContent}))}));throw error;});
    const located=[...plays.values()].at(-1);
    assert.ok(located.field_location && Number.isInteger(located.field_location.end_x));
    assert.equal(plays.size,before+1);
    assert.equal(await page.locator('[data-pass-id]').count(),1);
    await page.locator('#live-chart-passer').selectOption('1:10');
    assert.ok((await page.locator('#live-pass-summary').textContent()).includes('Completos / intentos'));
    await page.locator('#live-field-panel').screenshot({path:'mobile-pass-chart.png'});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
    role='player';await page.reload();await page.locator('#live-state[data-state="live"]').waitFor();
    assert.equal(await page.locator('#live-official-controls').isVisible(),false);
    assert.deepEqual(errors,[]);
    console.log('Mobile browser verified: one-tap pass, next play while offline, IndexedDB reload recovery, ordered upload, no duplicate plays, no optimistic public score, no overflow, private referee controls, no page errors.');
    await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});



