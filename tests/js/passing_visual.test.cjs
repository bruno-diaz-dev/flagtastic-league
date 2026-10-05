const {test}=require('node:test');
const assert=require('node:assert/strict');
const {totals,fieldMarkup}=require('../../static/passing_visual.js');
test('official passing totals drive illustration without location or live events',()=>{
 assert.deepEqual(totals({completed:32,attempts:45}),{completed:32,attempts:45,incomplete:13,percentage:32/45*100});
 const html=fieldMarkup({completed:32,attempts:45});assert.match(html,/SIN UBICACIONES REALES/);assert.match(html,/32 completos de 45/);assert.equal((html.match(/<circle/g)||[]).length,40);
});
test('empty and inconsistent totals never create negative counts or invalid SVG',()=>{
 assert.deepEqual(totals({completed:3,attempts:0}),{completed:0,attempts:0,incomplete:0,percentage:0});
 assert.equal((fieldMarkup({attempts:0}).match(/<circle/g)||[]).length,0);
 assert.doesNotMatch(fieldMarkup({completed:10,attempts:5}),/NaN|undefined/);
});
