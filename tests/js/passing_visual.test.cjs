const {test}=require('node:test');
const assert=require('node:assert/strict');
const {totals,fieldMarkup,markerLayout}=require('../../static/passing_visual.js');
test('a five-attempt passer shows exactly four completions and one incompletion',()=>{
 const row={completed:4,attempts:5,player_id:3,team_id:4};
 const html=fieldMarkup(row);
 assert.equal((html.match(/class="passing-marker"/g)||[]).length,5);
 assert.equal((html.match(/data-result="complete"/g)||[]).length,4);
 assert.equal((html.match(/data-result="incomplete"/g)||[]).length,1);
 assert.match(html,/POSICIONES Y ESCALA ILUSTRATIVAS/);
 const locations=markerLayout(row);
 assert.ok(new Set(locations.map(p=>p.y)).size>1);
 assert.deepEqual(markerLayout(row),locations);
});
test('large totals retain exact official numbers while the decorative sample remains bounded',()=>{
 assert.deepEqual(totals({completed:32,attempts:45}),{completed:32,attempts:45,incomplete:13,percentage:32/45*100});
 assert.equal(markerLayout({completed:316,attempts:417}).length,45);
 assert.match(fieldMarkup({completed:316,attempts:417}),/316 completos de 417/);
});
test('empty and inconsistent totals never create negative counts or invalid SVG',()=>{
 assert.deepEqual(totals({completed:3,attempts:0}),{completed:0,attempts:0,incomplete:0,percentage:0});
 assert.equal(markerLayout({attempts:0}).length,0);
 assert.doesNotMatch(fieldMarkup({completed:10,attempts:5}),/NaN|undefined/);
});
