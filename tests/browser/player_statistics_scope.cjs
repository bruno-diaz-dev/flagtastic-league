const {chromium} = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
    const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
    const page = await browser.newPage({viewport:{width:1546,height:1000}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const stats = (points, category) => ({weeks:2, points, receptions:1, tackles:0, interceptions:1,
        sacks:0, passes_completed:1, passes_attempted:category==='u10'?2:1, completion_percentage:category==='u10'?50:100});
    const teams = ['u10','u12'].map((category,i)=>({team_id:i+1, team_name:'Equipo '+category,
        category, branch:'mixto', jersey_number:5, active:true, standing_position:1,
        division_team_count:2, statistics:stats(i?18:6,category)}));
    const profile = {player:{id:7,name:'Jugador de dos categorías',age:12,aka:null,profile_photo_url:null},
        teams,selected_team_id:2,statistics:{...stats(24,'u10'),weeks:5,interceptions:2}};
    const template = name => {
        const page=fs.readFileSync('templates/'+name+'.html','utf8');
        const content=page.split('{% block content %}')[1].split('{% endblock %}')[0].replace('{{ player_id }}','7');
        const scripts=page.split('{% block scripts %}')[1].split('{% endblock %}')[0];
        return fs.readFileSync('templates/base.html','utf8').replace('{% block content %}{% endblock %}',content).replace('{% block scripts %}{% endblock %}',scripts);
    };
    await page.route('https://scope.test/**', async route=>{
        const url=new URL(route.request().url()),path=url.pathname;
        const json=body=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
        if(path.startsWith('/static/'))return route.fulfill({contentType:path.endsWith('.css')?'text/css':path.endsWith('.jpeg')?'image/jpeg':'application/javascript',body:fs.readFileSync('.'+path)});
        if(path==='/api/players/7/profile'||path==='/api/me/dashboard')return json(profile);
        if(path==='/api/auth/me')return json({id:1,name:'Jugador',display_name:'Jugador',roles:['player']});
        if(path==='/api/teams')return json([]);
        if(path.startsWith('/api/'))return json([]);
        return route.fulfill({contentType:'text/html',body:template(path==='/dashboard'?'dashboard':'player_profile')});
    });
    for (const [path,prefix] of [['/players/7?team_id=2','public-player'],['/dashboard','personal']]) {
        await page.goto('https://scope.test'+path);
        const select=page.locator('#'+prefix+'-stats-team');
        const grid=page.locator('#'+prefix+'-stats');
        await select.locator('option').first().waitFor({state:'attached'});
        assert.equal(await select.inputValue(),'2');
        assert.match(await grid.textContent(),/Puntos18/);
        assert.match(await grid.textContent(),/Intercepciones1/);
        assert.match(await grid.textContent(),/Jornadas con estadísticas2/);
        await select.selectOption('1');
        assert.match(await grid.textContent(),/Puntos6/);
        assert.match(await grid.textContent(),/Intercepciones1/);
        assert.match(await page.locator('#'+prefix+'-stats-context').textContent(),/U10/);
        if(prefix==='public-player')assert.match(page.url(),/team_id=1/);
        for(const width of [1546,390,320]) {
            await page.setViewportSize({width,height:1000});
            assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'no overflow at '+width);
        }
    }
    assert.deepEqual(errors,[]);
    await browser.close();
    console.log('Player statistics: separate categories, contextual links, unique weeks and desktop/mobile profiles verified.');
})().catch(error=>{console.error(error);process.exit(1);});
