const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1546,height:1000}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 let role='league_admin',fail=false;
 const game=(id,week,position)=>({id,week,position,field_number:7,start_time:'12:00:00',status:'scheduled',home_team:'Rancheros Infantil A.C.',away_team:'Diablos del Sol'});
 const officials=[{id:11,name:'Zoe García',aka:'Zoe',display_name:'Zoe',email:'zoe.garcia@example.test',status:'active',games:[game(1,4,'field_judge'),game(2,3,'down_judge')]},
  {id:12,name:'Zoé Pérez',aka:'Zoé',display_name:'Zoé',email:'zoe.perez@example.test',status:'active',games:[game(2,3,'statistician')]},
  {id:13,name:'Unassigned referee',display_name:'No games',email:'long.email.for.an.unassigned.official@example.test',status:'inactive',games:[]}];
 const template=fs.readFileSync('templates/referees.html','utf8');
 const content=template.split('{% block content %}')[1].split('{% endblock %}')[0];
 const scripts=template.split('{% block scripts %}')[1].split('{% endblock %}')[0];
 const html=fs.readFileSync('templates/base.html','utf8').replace('{% block content %}{% endblock %}',content).replace('{% block scripts %}{% endblock %}',scripts);
 await page.route('https://audit.test/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  const json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
  if(path.startsWith('/static/'))return route.fulfill({contentType:path.endsWith('.css')?'text/css':path.endsWith('.jpeg')?'image/jpeg':'application/javascript',body:fs.readFileSync('.'+path)});
  if(path==='/api/auth/me')return json({id:1,name:'Admin',roles:[role]});
  if(path==='/api/referees/assignments')return role!=='league_admin'?json({},403):fail?json({},503):json({officials,weeks:[4,3]});
  if(path==='/api/referees/me')return json({},403);
  if(path==='/api/referees')return json(officials.map(({id,name,aka,display_name})=>({id,name,aka,display_name,profile_photo_url:null})));
  if(path.startsWith('/api/'))return json([]);
  return route.fulfill({contentType:'text/html',body:html});
 });
 await page.goto('https://audit.test/referees');
 const panel=page.locator('#referee-assignment-audit'),week=page.locator('#referee-audit-week'),search=page.locator('#referee-audit-search');
 const person=id=>page.locator(`[data-referee-account="${id}"]`);
 await person(11).waitFor();
 assert.equal(await week.inputValue(),'4');
 await search.fill('zoe');
 assert.equal(await page.locator('[data-referee-account]').count(),2);
 assert.match(await person(11).textContent(),/Zoe García/);
 assert.match(await person(12).textContent(),/Zoé Pérez/);
 assert.match(await person(11).locator('.referee-audit-total').textContent(),/1 juego/);
 assert.match(await person(12).locator('.referee-audit-total').textContent(),/0 juegos/);
 await person(11).locator('summary').click();await person(12).locator('summary').click();
 assert.match(await person(11).textContent(),/12:00 h · Campo 7/);
 assert.match(await person(11).textContent(),/Field Judge/);
 assert.equal(await person(11).locator('a').getAttribute('href'),'/games/1');
 assert.match(await person(12).textContent(),/Sin juegos asignados/);
 for(const width of [1546,768,390,320]){
  await page.setViewportSize({width,height:1000});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'no page overflow '+width);
 }
 await page.setViewportSize({width:1546,height:1000});await panel.screenshot({path:'/tmp/referee-audit-desktop.png'});
 await page.setViewportSize({width:390,height:1000});await panel.screenshot({path:'/tmp/referee-audit-mobile.png'});
 await week.selectOption('3');
 assert.match(await person(12).locator('.referee-audit-total').textContent(),/1 juego/);
 await search.fill('#12');assert.equal(await page.locator('[data-referee-account]').count(),1);
 assert.equal(await person(12).locator('strong').textContent(),'Zoé');
 fail=true;await page.locator('#referee-audit-refresh').click();
 await page.waitForFunction(()=>document.querySelector('#referee-audit-message').textContent.includes('reintentar'));
 fail=false;await page.locator('#referee-audit-refresh').click();
 await page.waitForFunction(()=>document.querySelector('#referee-audit-message').textContent==='');
 assert.equal(await week.inputValue(),'3');assert.equal(await search.inputValue(),'#12');
 role='player';const denied=page.waitForResponse(response=>response.url().endsWith('/api/referees/assignments')&&response.status()===403);
 await page.reload();await denied;
 assert.equal(await panel.isVisible(),false);
 assert.equal(await page.locator('[data-referee-account]').count(),0);
 assert.deepEqual(errors,[]);await browser.close();
 console.log('Referee audit: separate Zoe accounts, zero assignments, jornada filters, account IDs, game links, retry and admin-only access verified.');
})().catch(error=>{console.error(error);process.exit(1);});
