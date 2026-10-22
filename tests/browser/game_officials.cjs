const {chromium} = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
    const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
    const page = await browser.newPage({viewport:{width:1546,height:1000}});
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    let role = 'league_admin', failLoad = true, reject = false, disconnect = false;
    let hold = false, release, started, writes = 0;
    const users = [
        {id:11,display_name:'Alan',roles:['referee'],status:'active'},
        {id:12,display_name:'Bruno',roles:['player','referee'],status:'active'},
        {id:13,display_name:'Santy',role:'referee',status:'active'},
        {id:14,display_name:'Oficial inactivo',roles:['referee'],status:'inactive'},
        {id:15,display_name:'Jugador',roles:['player'],status:'active'}
    ];
    let crew = [{...users[0],position:'referee'}, {...users[3],position:'side_judge'}];
    const template = fs.readFileSync('templates/game_detail.html','utf8');
    const content = template.split('{% block content %}')[1].split('{% endblock %}')[0]
        .replace('{{ game_id }}','237').replace('{% include "live_game_panel.html" %}','');
    const scripts = template.split('{% block scripts %}')[1].split('{% endblock %}')[0]
        .replace(/<script src="\/static\/live_[^>]+><\/script>/g,'');
    const html = fs.readFileSync('templates/base.html','utf8')
        .replace('{% block content %}{% endblock %}',content)
        .replace('{% block scripts %}{% endblock %}',scripts);
    await page.route('https://crew.test/**', async route => {
        const url = new URL(route.request().url()), path = url.pathname;
        const json = (body,status=200) => route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
        if(path.startsWith('/static/'))return route.fulfill({contentType:path.endsWith('.css')?'text/css':path.endsWith('.jpeg')?'image/jpeg':'application/javascript',body:fs.readFileSync('.'+path)});
        if(path==='/api/auth/me')return json({id:1,display_name:'Admin',roles:[role]});
        if(path==='/api/admin/users')return role!=='league_admin'?json({},403):failLoad?json({},503):json(users);
        if(path==='/api/games/237/details')return json({game:{id:237,week:3,start_time:'19:00',field_number:1,
            home_team:{id:1,name:'Equipo A'},away_team:{id:2,name:'Equipo B'}},officials:role==='player'?undefined:crew});
        if(path==='/api/games/237/referees')return json(crew);
        const match = path.match(/^\/api\/games\/237\/referees\/(\d+)$/);
        if(match){
            writes++;
            if(hold)await new Promise(resolve=>{release=resolve;started();});
            if(reject)return json({detail:'Asignación rechazada por el servidor'},409);
            if(disconnect)return route.abort('failed');
            const id=Number(match[1]);
            if(route.request().method()==='DELETE'){
                crew=crew.filter(official=>official.id!==id);return route.fulfill({status:204});
            }
            const {position}=route.request().postDataJSON();
            crew=[...crew.filter(official=>official.position!==position),{...users.find(user=>user.id===id),position}];
            return json({game_id:237,user_id:id,position},201);
        }
        if(path.startsWith('/api/'))return json([]);
        return route.fulfill({contentType:'text/html',body:html});
    });
    await page.goto('https://crew.test/games/237');
    await page.waitForFunction(()=>document.querySelector('#game-official-message').textContent.includes('reintentar'));
    failLoad=false;await page.locator('#game-official-refresh').click();
    const slot = position => page.locator(`[data-official-position="${position}"]`);
    await slot('referee').locator('select').waitFor();
    assert.equal(await page.locator('[data-official-position] select').count(),5);
    assert.equal(await slot('referee').locator('select').inputValue(),'11');
    assert.equal(await slot('side_judge').locator('select').inputValue(),'14');
    assert.equal(await slot('referee').locator('option[value="14"]').evaluate(option=>option.disabled),true);
    assert.equal(await slot('referee').locator('option[value="15"]').count(),0);
    assert.equal(await page.locator('#game-official-form').count(),0);
    // Draft selections for the rest of the crew survive each individual save.
    await slot('field_judge').locator('select').selectOption('13');
    await slot('down_judge').locator('select').selectOption('12');
    hold=true;const held = new Promise(resolve=>{started=resolve;});
    await slot('down_judge').locator('button').click();await held;
    assert.match(await slot('down_judge').locator('button').textContent(),/Guardando/);
    assert.equal(await slot('referee').locator('button').isDisabled(),true);
    await slot('down_judge').evaluate(form=>form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));
    assert.equal(writes,1);
    release();hold=false;
    await page.waitForFunction(()=>document.querySelector('[data-official-position="down_judge"] .form-message').textContent.includes('guardada'));
    assert.equal(await slot('field_judge').locator('select').inputValue(),'13');
    assert.match(await page.locator('#game-officials-list').textContent(),/Bruno/);
    await slot('field_judge').locator('select').selectOption('12');
    await slot('field_judge').locator('button').click();
    assert.match(await slot('field_judge').locator('.form-message').textContent(),/otro puesto/);
    assert.equal(writes,1);
    reject=true;await slot('field_judge').locator('select').selectOption('13');
    await slot('field_judge').locator('button').click();
    await page.waitForFunction(()=>document.querySelector('[data-official-position="field_judge"] .form-message').textContent.includes('rechazada'));
    assert.equal(crew.some(official=>official.position==='field_judge'),false);
    reject=false;await slot('field_judge').locator('button').click();
    await page.waitForFunction(()=>document.querySelector('[data-official-position="field_judge"] .form-message').textContent.includes('guardada'));
    await slot('side_judge').locator('select').selectOption('');await slot('side_judge').locator('button').click();
    await page.waitForFunction(()=>document.querySelector('[data-official-position="side_judge"] .form-message').textContent.includes('sin asignar'));
    // Network uncertainty blocks further edits until the stored crew is reloaded.
    disconnect=true;
    await slot('referee').locator('select').selectOption('');await slot('referee').locator('button').click();
    await page.waitForFunction(()=>document.querySelector('[data-official-position="referee"] .form-message').textContent.includes('comprobar'));
    assert.equal(await slot('down_judge').locator('select').isDisabled(),true);
    disconnect=false;await page.locator('#game-official-refresh').click();
    await page.waitForFunction(()=>document.querySelector('[data-official-position="referee"] select')?.value==='11'&&!document.querySelector('[data-official-position="referee"] select').disabled);
    for(const width of [1546,390,320]){
        await page.setViewportSize({width,height:1000});
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'no overflow at '+width);
    }
    await page.locator('#game-officials').screenshot({path:'/tmp/game-officials-mobile.png'});
    await page.setViewportSize({width:1546,height:1000});
    await page.locator('#game-officials').screenshot({path:'/tmp/game-officials-desktop.png'});
    await page.reload();await slot('field_judge').locator('select').waitFor();
    assert.equal(await slot('field_judge').locator('select').inputValue(),'13');
    assert.equal(await slot('side_judge').locator('select').inputValue(),'');
    role='referee';await page.reload();await page.locator('#game-officials').waitFor();
    assert.match(await page.locator('#game-officials-list').textContent(),/Santy/);
    assert.equal(await page.locator('#game-official-refresh').isVisible(),false);
    role='player';await page.reload();
    assert.equal(await page.locator('#game-officials').isVisible(),false);
    assert.deepEqual(errors,[]);
    await browser.close();
    console.log('Game detail crew: five independent slots, persistence, drafts, duplicates, errors, feedback, mobile and admin access verified.');
})().catch(error=>{console.error(error);process.exit(1);});
