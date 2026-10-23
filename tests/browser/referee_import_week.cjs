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
    let confirmed=null, releaseSave;
    const proposals=[
        {game_id:84,game_label:'J4: Sel AGS Var U17 vs Sel AGS Var U15',field_number:1,scheduled_time:'11:00'},
        {game_id:85,game_label:'J4: RANCHEROS INFANTIL A.C. vs DIABLOS DEL SOL TINTO',field_number:4,scheduled_time:'15:00'},
        {game_id:86,game_label:'J4: Eagles Flag vs Nómadas',field_number:7,scheduled_time:'19:00'}
    ].map(proposal=>({...proposal,source_text:`Semana 4!4: ${proposal.game_label} | Cam / Alan`,
        officials:[{user_id:11,position:'referee'},{user_id:12,position:'down_judge'}]}));
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
            return json({selected_week:4,proposals});
        }
        if(path==='/api/games/referee-schedule/confirm'){
            confirmed=route.request().postDataJSON();
            await new Promise(resolve=>{releaseSave=resolve;});
            return json({updated:3});
        }
        if(path.startsWith('/api/'))return json([]);
        return route.fulfill({contentType:'text/html',body:html});
    });
    await page.goto('https://import.test/referee/games');
    const form=page.locator('#referee-schedule-form');
    await page.getByText('Cargar rol de árbitros',{exact:false}).click();
    await form.locator('[name=file]').setInputFiles({name:'historial.csv',mimeType:'text/csv',buffer:Buffer.from('synthetic multi-week fixture')});
    await form.locator('[name=week]').fill('4');
    await form.locator('button').click();
    await page.waitForFunction(()=>document.querySelector('#schedule-review-scope').textContent.includes('Solo jornada 4'));
    const cards=page.locator('.schedule-review-card');
    assert.equal(await cards.count(),3);
    for(const width of [1709,1546,768,390,320]){
        await page.setViewportSize({width,height:1000});
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'page width '+width);
        for(let index=0;index<3;index++){
            const card=cards.nth(index),field=card.locator('[name=field_number]');
            assert.equal(await field.inputValue(),String(proposals[index].field_number));
            assert.equal(await field.locator('option:checked').textContent(),`Campo ${proposals[index].field_number}`);
            assert.match(await card.locator('.schedule-review-time').textContent(),new RegExp(proposals[index].scheduled_time));
            const bounds=await field.boundingBox();
            assert.ok(bounds.width>=140,'readable field select at '+width);
            assert.equal(await card.evaluate(node=>node.scrollWidth<=node.clientWidth),true,'card width '+width);
        }
    }
    await page.setViewportSize({width:1709,height:1000});
    assert.equal(await cards.first().locator('.schedule-referees').evaluate(node=>getComputedStyle(node).gridTemplateColumns.split(' ').length),5);
    assert.ok((await cards.first().boundingBox()).height<320,'compact desktop crew');
    await page.locator('#schedule-review').screenshot({path:'/tmp/referee-review-desktop.png'});
    await page.setViewportSize({width:390,height:1000});
    await cards.first().screenshot({path:'/tmp/referee-review-mobile.png'});
    // Changing the scope invalidates the preview before another analysis.
    await form.locator('[name=week]').fill('3');await form.locator('[name=week]').press('Tab');
    assert.equal(await page.locator('#schedule-review').isVisible(),false);
    await form.locator('[name=week]').fill('4');await form.locator('button').click();
    await cards.nth(1).locator('[name=field_number]').selectOption('8');
    await page.locator('#confirm-schedule').click();
    await page.waitForFunction(()=>document.querySelector('#confirm-schedule').hasAttribute('aria-busy'));
    assert.equal(await cards.first().locator('[name=field_number]').isDisabled(),true);
    while(!releaseSave)await new Promise(resolve=>setTimeout(resolve,10));
    releaseSave();
    await page.waitForFunction(()=>document.querySelector('#official-schedule-confirm-message').textContent.includes('actualizado'));
    assert.deepEqual(confirmed.assignments.map(assignment=>[assignment.game_id,assignment.field_number,assignment.scheduled_time]),
        [[84,1,'11:00'],[85,8,'15:00'],[86,7,'19:00']]);
    assert.deepEqual(confirmed.assignments[0].officials,[{user_id:11,position:'referee'},{user_id:12,position:'down_judge'}]);
    assert.deepEqual(errors,[]);await browser.close();
    console.log('Referee import: original file and selected week, explicit scope, invalidation and confirmation verified.');
})().catch(error=>{console.error(error);process.exit(1);});
