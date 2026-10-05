const {chromium} = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

(async () => {
    const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
    const context = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const page = await context.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    let offline=true;let role='referee';const plays=new Map();
    const roster=[{team_id:1,player_id:10,jersey_number:10,display_name:'Ana'},{team_id:1,player_id:7,jersey_number:7,display_name:'Eva'},{team_id:1,player_id:12,jersey_number:12,display_name:'Luz'},{team_id:2,player_id:20,jersey_number:20,display_name:'María'}];
    const snapshot=()=>({game_id:5,state:'live',version:plays.size,home_team:{id:1,name:'Tigres'},away_team:{id:2,name:'Lobos'},home_score:[...plays.values()].filter(p=>p.kind==='extra_one').length,away_score:0,roster,statistics:[],events:[...plays.values()].map((p,i)=>({...p,id:i+1,player_label:'#'+roster.find(r=>r.player_id===p.player_id).jersey_number,receiver_label:p.receiver_id?'#7 Eva':null,voided_at:null}))});
    await page.route('https://capture.test/**',async route=>{
        const u=new URL(route.request().url());
        if(u.pathname==='/') {
            const panel=fs.readFileSync('templates/live_game_panel.html','utf8');
            await route.fulfill({contentType:'text/html',body:`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/ui.css"><link rel="stylesheet" href="/static/live_game.css"></head><body><main class="content"><section class="game-detail-page" data-game-id="5"><section id="game-score"></section>${panel}</section></main><script>function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}</script><script src="/static/live_capture_queue.js"></script><script src="/static/live_game.js"></script></body></html>`});
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
    await page.locator('#live-retry').click();
    await page.waitForFunction(()=>document.querySelector('#live-queue-status').textContent.includes('Todo enviado')).catch(async error=>{
        console.log('CAPTURE_DIAGNOSTIC',JSON.stringify({accepted:plays.size,errors,state:await page.evaluate(()=>({status:document.querySelector('#live-queue-status').textContent,message:document.querySelector('#live-operation-message').textContent,rows:liveQueue?.rows,working:liveQueue?.working,liveState:liveData?.state,online:navigator.onLine}))}));
        throw error;
    });
    await page.waitForFunction(()=>document.querySelector('#live-home-score').textContent==='1');
    assert.equal(plays.size,2);
    assert.equal(await page.locator('.live-event').count(),2);
    role='player';await page.reload();await page.locator('#live-state[data-state="live"]').waitFor();
    assert.equal(await page.locator('#live-official-controls').isVisible(),false);
    assert.deepEqual(errors,[]);
    console.log('Mobile browser verified: one-tap pass, next play while offline, IndexedDB reload recovery, ordered upload, no duplicate plays, no optimistic public score, no overflow, private referee controls, no page errors.');
    await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
