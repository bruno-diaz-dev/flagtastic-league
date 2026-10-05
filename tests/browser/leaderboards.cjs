const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
    const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
    const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const metrics=['completion_percentage','receptions','points','tackles','interceptions','sacks'];
    const leaders=Object.fromEntries(metrics.map(metric=>[metric,[
        {player_id:1,team_id:1,player_name:'María Fernanda Nombre Largo Apellido Completo',player_aka:'UnaAliasMuyLargoSinEspaciosParaVerificarElAncho',team_name:'Diablos del Sol Aguascalientes',jersey_number:100,value:metric==='completion_percentage'?75.78:1234,passes_completed:316,passes_attempted:417},
        {player_id:2,team_id:2,player_name:'Ana López',team_name:'Lobos',jersey_number:7,value:metric==='completion_percentage'?70.25:987,passes_completed:281,passes_attempted:400}
    ]]));
    await page.route('https://leaders.test/**',async route=>{
        const url=new URL(route.request().url());
        if(url.pathname==='/api/statistics/passing-visual') return route.fulfill({json:[
            {player_id:1,team_id:1,display_name:'María Fernanda Nombre Largo Apellido Completo',team_name:'Diablos del Sol Aguascalientes',jersey_number:100,completed:4,attempts:5},
            {player_id:2,team_id:2,display_name:'Ana López',team_name:'Lobos',jersey_number:7,completed:281,attempts:400}
        ]});
        if(url.pathname.startsWith('/static/')) return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'application/javascript',body:fs.readFileSync('.'+url.pathname,'utf8')});
        const content=fs.readFileSync('templates/statistics.html','utf8').split('{% block content %}')[1].split('{% endblock %}')[0];
        await route.fulfill({contentType:'text/html',body:`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/ui.css"></head><body><main class="content">${content}</main><script>const data=${JSON.stringify(leaders)};function getLeaderboards(){return Promise.resolve({ok:true,json:async()=>data});}function isUnifiedYouthCategory(){return false;}function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}</script><script src="/static/passing_visual.js"></script><script src="/static/statistics.js"></script></body></html>`});
    });
    for(const width of [320,360,390,430,1280]){
        await page.setViewportSize({width,height:844});await page.goto('https://leaders.test/');
        await page.locator('.leaderboard-panel').last().waitFor();
        assert.equal(await page.locator('.leaderboard-panel').count(),6);
        await page.locator('#passing-visual-player:not([disabled])').waitFor();
        assert.equal(await page.locator('#passing-visual-field .passing-marker').count(),5);
        assert.equal(await page.locator('#passing-visual-field [data-result="complete"]').count(),4);
        assert.equal(await page.locator('#passing-visual-field [data-result="incomplete"]').count(),1);
        assert.ok((await page.locator('#passing-visual-summary').textContent()).includes('4/5'));
        assert.ok((await page.locator('#passing-visual-field').textContent()).includes('POSICIONES Y ESCALA ILUSTRATIVAS'));
        await page.locator('#passing-visual-player').selectOption('1');
        assert.ok((await page.locator('#passing-visual-summary').textContent()).includes('281/400'));
        assert.ok(await page.locator('.leaderboard-player').nth(1).textContent().then(text=>text.includes('Ana López')));
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`page overflow at ${width}`);
        if(width<=430){
            assert.equal(await page.evaluate(()=>[...document.querySelectorAll('.leaderboard-panel')].every(el=>el.scrollWidth<=el.clientWidth+1)),true,`panel overflow at ${width}`);
            assert.equal(await page.evaluate(()=>[...document.querySelectorAll('.stat-value')].every(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&el.scrollWidth<=el.clientWidth+1;})),true,`hidden total at ${width}`);
        }
        assert.equal(await page.locator('.stat-value strong').first().textContent(),'75.78%');
        assert.equal(await page.locator('.leaderboard-pass-detail').first().textContent(),'316/417 C/I');
        assert.equal(await page.locator('.leaderboard-panel').nth(2).locator('.stat-value strong').first().textContent(),'1234');
        if(width===390)await page.locator('#passing-visual-player').selectOption('0');
        if(width===390)await page.locator('#passing-visual-panel').screenshot({path:'mobile-passing-statistics.png'});
        if(width===390)await page.locator('.leaderboard-panel').first().screenshot({path:'mobile-leaderboards.png'});
    }
    assert.deepEqual(errors,[]);await browser.close();console.log('Leaderboards verified at 320, 360, 390, 430 and 1280 pixels; names and totals fit without horizontal scrolling.');
})().catch(error=>{console.error(error);process.exit(1);});

