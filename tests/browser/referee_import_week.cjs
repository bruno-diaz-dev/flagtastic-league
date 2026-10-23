const {chromium} = require('playwright');
const fs = require('node:fs'), assert = require('node:assert/strict');
(async () => {
    const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
    const page=await browser.newPage({viewport:{width:390,height:1000}}), errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    const template=fs.readFileSync('templates/referee_games.html','utf8');
    const content=template.split('{% block content %}')[1].split('{% endblock %}')[0];
    const scripts=template.split('{% block scripts %}')[1].split('{% endblock %}')[0];
    const html=fs.readFileSync('templates/base.html','utf8')
        .replace('{% block content %}{% endblock %}',content)
        .replace('{% block scripts %}{% endblock %}',scripts);
    let confirmed=null;
    await page.route('https://import.test/**',async route=>{
        const path=new URL(route.request().url()).pathname;
        const json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
        if(path.startsWith('/static/'))return route.fulfill({contentType:path.endsWith('.css')?'text/css':path.endsWith('.jpeg')?'image/jpeg':'application/javascript',body:fs.readFileSync('.'+path)});
        if(path==='/api/auth/me')return json({id:1,display_name:'Admin',roles:['league_admin','referee']});
        if(path==='/api/admin/users')return json([
            {id:11,display_name:'Cam',roles:['referee'],status:'active'},
            {id:12,display_name:'Alan',roles:['referee'],status:'active'}]);
        if(path==='/api/games/referee-schedule/analyze'){
            const request=route.request().postData();
            assert.match(request,/name="week"\r\n\r\n4/);
            assert.match(request,/filename="historial.csv"/);
            return json({selected_week:4,proposals:[{game_id:84,game_label:'J4: Nómadas vs Lobos',field_number:1,
                scheduled_time:'12:00',source_text:'Semana 4!4',officials:[{user_id:11,position:'referee'},{user_id:12,position:'down_judge'}]}]});
        }
        if(path==='/api/games/referee-schedule/confirm'){
            confirmed=route.request().postDataJSON();return json({updated:1});
        }
        if(path.startsWith('/api/'))return json([]);
        return route.fulfill({contentType:'text/html',body:html});
    });
    await page.goto('https://import.test/referees/me');
    const form=page.locator('#referee-schedule-form');
    await page.getByText('Cargar rol de árbitros',{exact:false}).click();
    await form.locator('[name=file]').setInputFiles({name:'historial.csv',mimeType:'text/csv',buffer:Buffer.from('synthetic multi-week fixture')});
    await form.locator('[name=week]').fill('4');
    await form.locator('button').click();
    await page.waitForFunction(()=>document.querySelector('#schedule-review-scope').textContent.includes('Solo jornada 4'));
    assert.equal(await page.locator('#schedule-review-body tr').count(),1);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    // Changing the scope invalidates the preview before another analysis.
    await form.locator('[name=week]').fill('3');await form.locator('[name=week]').press('Tab');
    assert.equal(await page.locator('#schedule-review').isVisible(),false);
    await form.locator('[name=week]').fill('4');await form.locator('button').click();
    await page.locator('#confirm-schedule').click();
    await page.waitForFunction(()=>document.querySelector('#official-schedule-confirm-message').textContent.includes('actualizado'));
    assert.deepEqual(confirmed.assignments.map(assignment=>assignment.game_id),[84]);
    assert.deepEqual(confirmed.assignments[0].officials,[{user_id:11,position:'referee'},{user_id:12,position:'down_judge'}]);
    assert.deepEqual(errors,[]);await browser.close();
    console.log('Referee import: original file and selected week, explicit scope, invalidation and confirmation verified.');
})().catch(error=>{console.error(error);process.exit(1);});
