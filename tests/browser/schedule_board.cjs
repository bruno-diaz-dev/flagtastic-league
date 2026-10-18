const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1546,height:960}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 const teams=[{id:1,name:'RANCHEROS INFANTIL A.C.',branch:'femenil',category:'libre'},{id:2,name:'Diablos del Sol',branch:'femenil',category:'libre'}];
 const game=(id,field,time,status='scheduled')=>({id,week:3,field_number:field,start_time:time,status,home_team:teams[0],away_team:teams[1],home_score:status==='completed'?6:null,away_score:status==='completed'?0:null});
 const games=[game(1,1,'12:00'),game(2,2,'13:00'),game(3,3,'12:00','completed')];
 const officials=[{id:11,name:'Ref Uno',role:'referee',status:'active'}, {id:12,name:'Ref Dos',roles:['player','referee'],status:'active'}, {id:13,name:'Ref Tres',role:'referee',status:'active'}, {id:14,name:'Inactivo',role:'referee',status:'inactive'}];
 const crews={1:[{id:11,name:'Ref Uno',position:'referee'}],2:[{id:13,name:'Ref Tres',position:'down_judge'}]};
 let officialWrites=0,rejectOfficial=false,holdCrew=false,releaseCrew,crewStarted;
 let writes=0,reject=false,release,hold=false,heldStarted;
 await page.route('https://board.test/**',async route=>{
  const url=new URL(route.request().url());
  const json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
  if(url.pathname.startsWith('/static/'))return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'application/javascript',body:fs.readFileSync('.'+url.pathname,'utf8')});
  if(url.pathname==='/api/teams')return json(teams);
  if(url.pathname==='/api/admin/users')return json(officials);
  const crewMatch=url.pathname.match(/^\/api\/games\/(\d+)\/referees(?:\/(\d+))?$/);
  if(crewMatch){
   const id=Number(crewMatch[1]),userId=Number(crewMatch[2]),method=route.request().method();
   if(method==='GET'){
    const rows=[...(crews[id]||[])];
    if(holdCrew&&id===1)await new Promise(resolve=>{releaseCrew=resolve;crewStarted();});
    return json(rows);
   }
   officialWrites++;
   if(rejectOfficial)return json({detail:'Asignación rechazada por el servidor'},409);
   if(method==='DELETE'){crews[id]=(crews[id]||[]).filter(official=>official.id!==userId);return route.fulfill({status:204});}
   const {position}=route.request().postDataJSON();
   const person=officials.find(user=>user.id===userId);
   crews[id]=[...(crews[id]||[]).filter(official=>official.position!==position),{id:userId,name:person.name,position}];
   return json({game_id:id,user_id:userId,position},201);
  }
  if(/\/api\/games\/\d+\/status$/.test(url.pathname)){
   const id=Number(url.pathname.split('/')[3]),change=route.request().postDataJSON();
   const current=games.find(g=>g.id===id);current.status=change.status;
   return json({id,status:current.status});
  }
  if(url.pathname==='/api/games')return json(games);
  if(/\/api\/games\/\d+\/schedule/.test(url.pathname)){
   writes++;const change=route.request().postDataJSON(),id=Number(url.pathname.split('/')[3]);
   if(hold)await new Promise(resolve=>{release=resolve;heldStarted();});
   if(reject)return json({detail:'Ese campo ya tiene otro partido'},409);
   const current=games.find(g=>g.id===id);Object.assign(current,change);return json({id,week:3,status:current.status,...change});
  }
  if(url.pathname.startsWith('/api/'))return json([]);
  const content=fs.readFileSync('templates/games.html','utf8').split('{% block content %}')[1].split('{% endblock %}')[0].replace(/{% for field_number in range\(1, 9\) %}[\s\S]*?{% endfor %}/g,Array.from({length:8},(_,i)=>`<option value="${i+1}">Campo ${i+1}</option>`).join(''));
  return route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/ui.css"></head><body class="role-league_admin"><main class="content">${content}</main><script>function escapeHtml(v){const n=document.createElement('span');n.textContent=String(v);return n.innerHTML.replace(/"/g,'&quot;');}</script><script src="/static/api.js"></script><script src="/static/games.js"></script><script src="/static/schedule_board.js"></script></body></html>`});
 });
 await page.goto('https://board.test/');
 const board=page.locator('#admin-schedule-board');
 const disclosure=board.locator('details.ui-disclosure');
 assert.equal(await disclosure.evaluate(node=>node.open),false);
 assert.equal(await page.locator('#schedule-board-grid').isVisible(),false);
 await disclosure.locator('summary').click();
 await board.locator('[data-board-game="1"]').waitFor();
 await disclosure.locator('summary').press('Enter');
 assert.equal(await page.locator('#schedule-board-grid').isVisible(),false);
 await disclosure.locator('summary').press('Enter');
 assert.equal(await page.locator('#schedule-board-grid').isVisible(),true);
 const slot=position=>board.locator(`[data-board-position="${position}"]`);
 await slot('referee').locator('select').waitFor();
 assert.equal(await board.locator('[data-board-position] select').count(),5);
 assert.equal(await slot('referee').locator('select').inputValue(),'11');
 assert.equal(await slot('down_judge').locator('select').inputValue(),'');
 assert.equal(await slot('referee').locator('option[value="14"]').count(),0);
 await slot('down_judge').locator('select').selectOption('12');
 await slot('down_judge').locator('button').click();
 await page.waitForFunction(()=>document.querySelector('[data-board-position="down_judge"] .form-message').textContent.includes('guardada'));
 assert.equal(officialWrites,1);assert.equal(await slot('referee').locator('select').inputValue(),'11');
 await slot('field_judge').locator('select').selectOption('12');
 await slot('field_judge').locator('button').click();
 assert.match(await slot('field_judge').locator('.form-message').textContent(),/otro puesto/);assert.equal(officialWrites,1);
 rejectOfficial=true;
 await slot('field_judge').locator('select').selectOption('13');
 await slot('field_judge').locator('button').click();
 await page.waitForFunction(()=>document.querySelector('[data-board-position="field_judge"] .form-message').textContent.includes('rechazada'));
 assert.equal(await slot('field_judge').locator('select').inputValue(),'13');
 assert.equal(await slot('down_judge').locator('select').inputValue(),'12');
 rejectOfficial=false;await slot('field_judge').locator('button').click();
 await page.waitForFunction(()=>document.querySelector('[data-board-position="field_judge"] .form-message').textContent.includes('guardada'));
 await slot('down_judge').locator('select').selectOption('');await slot('down_judge').locator('button').click();
 await page.waitForFunction(()=>document.querySelector('[data-board-position="down_judge"] .form-message').textContent.includes('sin asignar'));
 assert.equal(await slot('field_judge').locator('select').inputValue(),'13');
 // A late crew response for one match cannot overwrite another match's editor.
 holdCrew=true;const heldCrew=new Promise(resolve=>{crewStarted=resolve;});
 await page.locator('#schedule-board-refresh-officials').click();await heldCrew;
 await page.locator('#schedule-board-edit [name=game_id]').selectOption('2');
 await page.waitForFunction(()=>document.querySelector('[data-board-position="down_judge"] select')?.value==='13');
 const oldResponse=page.waitForResponse(response=>response.url().endsWith('/api/games/1/referees'));
 releaseCrew();holdCrew=false;await oldResponse;
 assert.equal(await slot('down_judge').locator('select').inputValue(),'13');
 await page.locator('#schedule-board-edit [name=game_id]').selectOption('1');
 await page.waitForFunction(()=>document.querySelector('[data-board-position="referee"] select')?.value==='11');
 assert.equal(await slot('down_judge').locator('select').inputValue(),'');
 assert.equal(await slot('field_judge').locator('select').inputValue(),'13');
 assert.equal(await board.locator('[data-board-game="3"]').isDisabled(),true);
 for(const width of [1546,390,320]){await page.setViewportSize({width,height:960});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`page overflow ${width}`);}
 await page.setViewportSize({width:1546,height:960});
 async function drag(source, target) {
  await source.scrollIntoViewIfNeeded();
  const from=await source.boundingBox();
  await page.mouse.move(from.x+from.width/2,from.y+from.height/2);
  await page.mouse.down();
  await page.mouse.move(from.x+from.width/2+12,from.y+from.height/2,{steps:4});
  await target.hover();
  const to=await target.boundingBox();
  await page.mouse.move(to.x+to.width/2+1,to.y+to.height/2+1);
  await page.mouse.up();
 }
 await board.screenshot({path:'admin-schedule-board.png'});
 const target=board.locator('[data-board-time="14:00"][data-board-field="4"]');
 await drag(board.locator('[data-board-game="1"]'),target);
 await page.waitForFunction(()=>document.querySelector('#schedule-board-message').textContent.includes('Cambio guardado'));
 assert.equal(await target.locator('[data-board-game="1"]').count(),1);assert.equal(writes,1);
 // Occupied destination is rejected before sending a request.
 await drag(board.locator('[data-board-game="1"]'),board.locator('[data-board-time="13:00"][data-board-field="2"]'));
 assert.match(await page.locator('#schedule-board-message').textContent(),/otro partido/);assert.equal(writes,1);
 // Mobile/keyboard controls use the same update and retain the old slot on rejection.
 await page.setViewportSize({width:390,height:844});
 await board.screenshot({path:'mobile-schedule-board.png'});
 await board.locator('[data-board-game="1"]').click();
 await page.locator('#schedule-board-edit [name=start_time]').fill('15:30');
 await page.locator('#schedule-board-edit [name=field_number]').selectOption('5');
 reject=true;await page.locator('#schedule-board-edit button').click();
 await page.waitForFunction(()=>!document.querySelector('#admin-schedule-board').hasAttribute('aria-busy'));
 assert.equal(await target.locator('[data-board-game="1"]').count(),1);
 reject=false;hold=true;
 const requestHeld=new Promise(resolve=>{heldStarted=resolve;});
 await page.locator('#schedule-board-edit [name=start_time]').fill('15:30');
 await page.locator('#schedule-board-edit [name=field_number]').selectOption('5');
 await page.locator('#schedule-board-edit button').click();
 assert.equal(await page.locator('#schedule-board-edit button').isDisabled(),true);
 assert.match(await page.locator('#schedule-board-message').textContent(),/Guardando/);
 await requestHeld;release();hold=false;
 await page.waitForFunction(()=>document.querySelector('[data-board-time="15:30"][data-board-field="5"] [data-board-game="1"]'));
 assert.equal(await board.locator('[data-board-game="1"]').count(),1);
 // Card editor also updates the existing ID and keeps the board in sync.
 await page.evaluate(()=>document.querySelector('#game-filter-week').value='3');
 await page.evaluate(()=>renderFilteredGames());
 const form=page.locator('.game-time-form[data-game-id="1"]');
 await form.evaluate(node=>node.closest('details').open=true);
 await form.locator('[name=start_time]').fill('16:00');await form.locator('[name=field_number]').selectOption('6');
 await form.locator('button').click();
 await page.waitForFunction(()=>document.querySelector('[data-board-time="16:00"][data-board-field="6"] [data-board-game="1"]'));
 assert.match(await page.locator('.game-time-form[data-game-id="1"] .game-time-message').textContent(),/actualizados/);
 await page.setViewportSize({width:320,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.evaluate(()=>{document.body.className='role-referee';});assert.equal(await board.isVisible(),false);
 assert.equal(await page.locator('.game-time-form[data-game-id="1"]').isVisible(),false);
 await page.evaluate(()=>{document.body.className='role-player';});assert.equal(await board.isVisible(),false);
 // Restore an accidentally postponed game through the visible admin controls.
 games.push(game(4,4,'17:00','postponed'));
 await page.reload();
 await page.locator('#game-filter-status').selectOption('postponed');
 const restore=page.locator('[data-game-status="4"]');
 await restore.waitFor({state:'attached'});
 assert.equal(await page.locator('#games .game-card').count(),1);
 await restore.evaluate(node=>node.closest('details').open=true);
 await restore.click();
 await page.waitForFunction(()=>document.querySelector('#game-schedule-update-message').textContent.includes('Partido restablecido'));
 assert.equal(await page.locator('[data-game-status="4"]').count(),0);
 await page.locator('#game-filter-status').selectOption('scheduled');
 await page.locator('[data-game-status="4"]').waitFor({state:'attached'});
 assert.equal(games.find(g=>g.id===4).status,'scheduled');
 assert.deepEqual(errors,[]);await browser.close();console.log('Schedule board: drag/drop, conflicts, mobile controls, save feedback, card editor and admin visibility verified.');
})().catch(error=>{console.error(error);process.exit(1);});
