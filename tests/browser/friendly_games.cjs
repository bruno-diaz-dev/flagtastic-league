const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const team={id:1,name:'Local de la liga',branch:'mixto',category:'libre'};
 const guest={id:2,name:'Invitados de otra liga',branch:'mixto',category:'libre',is_guest:true};
 const game={id:1,home_team:team,away_team:guest,is_friendly:true,week:1,field_number:1,start_time:'10:00',status:'scheduled',home_score:null,away_score:null};
 let created,imported;
 await page.route('https://friendly.test/**',async route=>{
  const url=new URL(route.request().url()),method=route.request().method();
  if(url.pathname.startsWith('/static/'))return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'application/javascript',body:fs.readFileSync('.'+url.pathname,'utf8')});
  const json=body=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  if(url.pathname==='/api/teams')return json([team]);
  if(url.pathname==='/api/games'&&method==='GET')return json([game]);
  if(url.pathname==='/api/games'&&method==='POST'){created=route.request().postDataJSON();return route.fulfill({status:201,contentType:'application/json',body:JSON.stringify({id:2})});}
  if(url.pathname==='/api/games/schedule/confirm'){imported=route.request().postDataJSON();return json({created:1,updated:0,skipped:0});}
  if(url.pathname.startsWith('/api/'))return json([]);
  let content=fs.readFileSync('templates/games.html','utf8').split('{% block content %}')[1].split('{% endblock %}')[0].replace(/{% for field_number in range\(1, 9\) %}[\s\S]*?{% endfor %}/g,'<option value="1">Campo 1</option>');
  return route.fulfill({contentType:'text/html',body:`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"><link rel="stylesheet" href="/static/ui.css"></head><body><main class="content">${content}</main><script src="/static/api.js"></script><script src="/static/games.js"></script></body></html>`});
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
 await page.evaluate(()=>renderGameScheduleReview({matched:0,unmatched:1,proposals:[{week:2,field_number:1,start_time:'11:00',home_team:'Invitados A',away_team:'Invitados B',home_team_id:null,away_team_id:null,ready:false}]}));
 await page.locator('[data-schedule-friendly="0"]').check();
 await page.locator('[data-schedule-row="0"]').check();
 await page.locator('[data-schedule-branch="0"]').selectOption('mixto');
 await page.locator('[data-schedule-category="0"]').selectOption('libre');
 await page.locator('#confirm-game-schedule').click();
 await page.waitForFunction(()=>document.querySelector('#game-schedule-import-message').textContent.includes('creados'));
 assert.equal(imported.games[0].is_friendly,true);assert.equal(imported.games[0].home_guest_name,'Invitados A');assert.equal(imported.games[0].away_guest_name,'Invitados B');assert.equal(imported.games[0].category,'libre');
 assert.deepEqual(errors,[]);await browser.close();console.log('Friendly calendar, guest registration and reviewed import verified in Chromium.');
})().catch(error=>{console.error(error);process.exit(1);});
