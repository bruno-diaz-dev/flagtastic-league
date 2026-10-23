const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const team={id:1,name:'Local de la liga',branch:'mixto',category:'libre'};
 const secondTeam={id:3,name:'Nómadas',branch:'mixto',category:'libre'};
 const guest={id:2,name:'Invitados de otra liga',branch:'mixto',category:'libre',is_guest:true};
 const game={id:1,home_team:team,away_team:guest,is_friendly:true,week:1,field_number:1,start_time:'10:00',status:'scheduled',home_score:null,away_score:null};
 let created,imported,confirmGate,releaseConfirmation,confirmFailure=false,ocrDownloads=0,imagePayload;
 await page.route('https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js',route=>{
  ocrDownloads++;
  return route.fulfill({contentType:'application/javascript',headers:{'Access-Control-Allow-Origin':'*'},
   body:'window.Tesseract={async createWorker(){return {async terminate(){window.imageWorkerTerminated=(window.imageWorkerTerminated||0)+1;}}}};'});
 });
 await page.route('https://friendly.test/**',async route=>{
  const url=new URL(route.request().url()),method=route.request().method();
  if(url.pathname.startsWith('/static/'))return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'application/javascript',body:fs.readFileSync('.'+url.pathname,'utf8')});
  const json=body=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  if(url.pathname==='/api/teams')return json([team,secondTeam]);
  if(url.pathname==='/api/games'&&method==='GET')return json([game]);
  if(url.pathname==='/api/games'&&method==='POST'){created=route.request().postDataJSON();return route.fulfill({status:201,contentType:'application/json',body:JSON.stringify({id:2})});}
  if(url.pathname==='/api/games/schedule/analyze-cells'){
   imagePayload=route.request().postDataJSON();
   return json({matched:1,unmatched:0,proposals:[{week:imagePayload.week,field_number:1,start_time:'12:00',home_team:team.name,away_team:secondTeam.name,
    home_team_id:1,away_team_id:3,home_match_branch:'mixto',home_match_category:'libre',ready:true}]});
  }
  if(url.pathname==='/api/games/schedule/confirm'){
   imported=route.request().postDataJSON();
   if(confirmGate)await confirmGate;
   if(confirmFailure)return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'El partido ya tiene resultados; revisa el rol.'})});
   return json({created:1,updated:0,skipped:0});
  }
  if(url.pathname.startsWith('/api/'))return json([]);
  let content=fs.readFileSync('templates/games.html','utf8').split('{% block content %}')[1].split('{% endblock %}')[0].replace(/{% for field_number in range\(1, 9\) %}[\s\S]*?{% endfor %}/g,'<option value="1">Campo 1</option>');
  return route.fulfill({contentType:'text/html',body:`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/ui.css"></head><body class="role-league_admin"><main class="content">${content}</main><script>function escapeHtml(v){const el=document.createElement("span");el.textContent=String(v);return el.innerHTML.replace(/"/g,"&quot;");}</script><script src="/static/api.js"></script><script src="/static/ocr_loader.js"></script><script src="/static/schedule_ocr_cells.js"></script><script src="/static/games.js"></script></body></html>`});
 });
 await page.goto('https://friendly.test/');
 await page.locator('.game-card-friendly').waitFor();
 assert.equal(await page.locator('.game-card-friendly .game-friendly-badge').textContent(),'Amistoso');
 for(const width of [320,390,430]){await page.setViewportSize({width,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`calendar overflow ${width}`);}
 await page.setViewportSize({width:390,height:844});
 await page.locator('.game-card-friendly').screenshot({path:'mobile-friendly-game.png'});
 await page.evaluate(()=>document.querySelectorAll('details').forEach(el=>el.open=true));
 await page.locator('#manual-game-type').selectOption('true');
 await page.locator('[name=home_team_id]').selectOption('1');
 await page.locator('[name=away_team_id]').selectOption('guest');
 await page.locator('[name=away_guest_name]').fill('Equipo visitante invitado');
 await page.locator('#game-form button[type=submit]').click();
 await page.waitForFunction(()=>document.querySelector('#game-form-message').textContent.includes('correctamente'));
 assert.equal(created.is_friendly,true);assert.equal(created.home_team_id,1);assert.equal(created.away_team_id,null);assert.equal(created.away_guest_name,'Equipo visitante invitado');
 await page.locator('#manual-game-type').selectOption('true');
 await page.locator('#manual-game-branch').selectOption('varonil');
 await page.locator('#manual-game-category').selectOption('u16');
 await page.locator('#manual-home-team-search').fill('Pitbulls v16');
 await page.locator('#manual-away-team-search').fill('Lobos v16');
 assert.equal(await page.locator('[name=home_team_id]').inputValue(),'guest');
 assert.equal(await page.locator('[name=away_team_id]').inputValue(),'guest');
 assert.equal(await page.locator('[name=home_guest_name]').isVisible(),true);
 assert.equal(await page.locator('[name=home_guest_name]').isEnabled(),true);
 assert.equal(await page.locator('[name=home_guest_name]').inputValue(),'Pitbulls v16');
 assert.equal(await page.locator('[name=away_guest_name]').inputValue(),'Lobos v16');
 await page.locator('[name=home_guest_name]').fill('Pitbulls');
 await page.locator('[name=away_guest_name]').fill('Lobos');
 await page.locator('#game-form button[type=submit]').click();
 await page.waitForFunction(()=>document.querySelector('#game-form-message').textContent.includes('correctamente'));
 assert.equal(created.home_guest_name,'Pitbulls');assert.equal(created.away_guest_name,'Lobos');
 assert.equal(created.branch,'varonil');assert.equal(created.category,'u16');
 await page.evaluate(()=>renderGameScheduleReview({matched:0,unmatched:1,proposals:[{week:2,field_number:1,start_time:'11:00',home_team:'Invitados A',away_team:'Invitados B',home_team_id:null,away_team_id:null,ready:false}]}));
 await page.locator('[data-schedule-friendly="0"]').check();
 await page.locator('[data-schedule-row="0"]').check();
 await page.locator('#confirm-game-schedule').click();
 assert.equal(await page.locator('#game-schedule-confirm-message').isVisible(),true);
 assert.match(await page.locator('#game-schedule-confirm-message').textContent(),/rama y categoría/);
 assert.equal(imported,undefined);
 await page.locator('[data-schedule-branch="0"]').selectOption('mixto');
 await page.locator('[data-schedule-category="0"]').selectOption('libre');
 confirmGate=new Promise(resolve=>{releaseConfirmation=resolve;});
 await page.locator('#confirm-game-schedule').click();
 assert.equal(await page.locator('#confirm-game-schedule').isDisabled(),true);
 assert.equal(await page.locator('#confirm-game-schedule').getAttribute('aria-busy'),'true');
 assert.match(await page.locator('#confirm-game-schedule').textContent(),/Guardando/);
 assert.equal(await page.locator('#game-schedule-save-progress').isVisible(),true);
 assert.equal(await page.locator('#game-schedule-save-progress').getAttribute('aria-valuenow'),null);
 assert.match(await page.locator('#game-schedule-confirm-message').textContent(),/Guardando 1 partido/);
 releaseConfirmation();confirmGate=null;
 await page.waitForFunction(()=>document.querySelector('#game-schedule-import-message').textContent.includes('creados'));
 assert.equal(await page.locator('#game-schedule-save-progress').getAttribute('aria-valuenow'),'100');
 assert.equal(await page.locator('#game-schedule-confirm-message').isVisible(),true);
 assert.match(await page.locator('#game-schedule-confirm-message').textContent(),/creados/);
 assert.equal(imported.games[0].is_friendly,true);assert.equal(imported.games[0].home_guest_name,'Invitados A');assert.equal(imported.games[0].away_guest_name,'Invitados B');assert.equal(imported.games[0].category,'libre');
 // An unresolved label can be assigned to an actual team without becoming a guest.
 await page.evaluate(()=>renderGameScheduleReview({matched:0,unmatched:1,proposals:[{week:3,field_number:7,start_time:'18:00',home_team:'Local abreviado',away_team:'Nomadas',ready:false}]}));
 await page.locator('[data-schedule-home-id="0"]').selectOption('1');
 assert.equal(await page.locator('[data-schedule-row="0"]').isDisabled(),true);
 await page.locator('[data-schedule-away-id="0"]').selectOption('1');
 assert.equal(await page.locator('[data-schedule-row="0"]').isDisabled(),true);
 await page.locator('[data-schedule-away-id="0"]').selectOption('3');
 assert.equal(await page.locator('[data-schedule-row="0"]').isChecked(),true);
 assert.equal(await page.locator('[data-schedule-home="0"]').isVisible(),false);
 confirmFailure=true;
 await page.locator('#confirm-game-schedule').click();
 await page.waitForFunction(()=>document.querySelector('#game-schedule-confirm-message').textContent.includes('ya tiene resultados'));
 assert.equal(await page.locator('#game-schedule-confirm-message').isVisible(),true);
 assert.equal(await page.locator('#game-schedule-save-progress').isVisible(),false);
 assert.equal(await page.locator('#confirm-game-schedule').isEnabled(),true);
 assert.equal(await page.locator('#confirm-game-schedule').getAttribute('aria-busy'),null);
 assert.equal(await page.locator('[data-schedule-away-id="0"]').inputValue(),'3');
 confirmFailure=false;
 await page.locator('#confirm-game-schedule').click();
 await page.waitForFunction(()=>document.querySelector('#game-schedule-import-message').textContent.includes('creados'));
 assert.equal(imported.games[0].home_team_id,1);
 assert.equal(imported.games[0].away_team_id,3);
 assert.equal(imported.games[0].home_guest_name,null);
 assert.equal(imported.games[0].is_friendly,false);
 await page.evaluate(()=>renderGameScheduleReview({matched:1,unmatched:1,proposals:[
  {week:3,field_number:1,start_time:'19:00',home_team:'Seleccion Aguascalientes',away_team:'Diablos del Sol',home_match_branch:'femenil',home_match_category:'libre',ready:true},
  {week:3,field_number:7,start_time:'19:00',home_team:'Lobos del Norte',away_team:'Vikingos',home_match_branch:'varonil',home_match_category:'libre',ready:false}
 ]}));
 for(const width of [1920,1546,1280,390,320]) {
  await page.setViewportSize({width,height:960});
  const layout=await page.evaluate(()=>{
   const row=document.querySelector('#game-schedule-review-body tr:last-child');
   const home=row.querySelector('[data-schedule-home]').getBoundingClientRect();
   const category=row.querySelector('[data-schedule-category]').getBoundingClientRect();
   const status=row.lastElementChild;
   const checkbox=row.querySelector('[type=checkbox]').getBoundingClientRect();
   return {pageFits:document.documentElement.scrollWidth<=innerWidth,homeWidth:home.width,
    headersFit:[...document.querySelectorAll("#game-schedule-review-head th")].every(th=>th.scrollWidth<=th.clientWidth),statusFits:status.scrollWidth<=status.clientWidth,categoryEnds:category.right,statusStarts:status.getBoundingClientRect().left,checkboxWidth:checkbox.width};
  });
  assert.equal(layout.pageFits,true,`review must scroll inside its container at ${width}`);
  assert.ok(layout.homeWidth>=200,`readable team inputs at ${width}: ${layout.homeWidth}`);
  assert.equal(layout.statusFits,true,`warning must wrap at ${width}`);
  assert.equal(layout.headersFit,true,`headers must not overlap at ${width}`);
  assert.ok(layout.categoryEnds<=layout.statusStarts,`category and warning overlap at ${width}`);
  assert.ok(layout.checkboxWidth<=20,`compact checkbox at ${width}`);
  if(width===1546)await page.locator('#game-schedule-review').screenshot({path:'desktop-schedule-review.png'});
 }
 // Exercise the first image upload through the real form and lazy-loader entry point.
 assert.equal(ocrDownloads,0);assert.equal(await page.evaluate(()=>Boolean(window.Tesseract)),false);
 await page.evaluate(()=>{
  scheduleSourceCanvas=async()=>({width:1200,height:100});
  scheduleGridLines=()=>[0,100];prepareScheduleCell=()=>({blank:false});
  recognizeScheduleCells=async(worker,canvas,cells,options)=>new Map(cells.map(cell=>[cell.key,
   options.whitelist?'12:00':cell.key.endsWith(':home')?'Local de la liga':'Nómadas']));
 });
 const imageForm=page.locator('#game-schedule-import-form');
 await imageForm.locator('[name=week_override]').fill('4');
 await imageForm.locator('[name=file]').setInputFiles({name:'rol.jpeg',mimeType:'image/jpeg',buffer:Buffer.from('controlled OCR fixture')});
 await imageForm.locator('button').click();
 await page.waitForFunction(()=>window.imageWorkerTerminated===1);
 await page.waitForFunction(()=>document.querySelector('#game-schedule-import-message').textContent.includes('listos'));
 assert.equal(ocrDownloads,1);assert.equal(imagePayload.week,4);assert.equal(imagePayload.rows[0].start_time,'12:00');
 assert.equal(await page.locator('#game-schedule-review').isVisible(),true);
 await imageForm.locator('button').click();await page.waitForFunction(()=>window.imageWorkerTerminated===2);
 assert.equal(ocrDownloads,1);
 assert.deepEqual(errors,[]);await browser.close();console.log('Friendly calendar, guest registration, reviewed import and lazy OCR image loading verified in Chromium.');
})().catch(error=>{console.error(error);process.exit(1);});
