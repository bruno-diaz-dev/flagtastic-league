const {test}=require('node:test');
const assert=require('node:assert/strict');
const {passSummary,mapMarkup,valid,point}=require('../../static/live_pass_chart.js');
const e=(kind,extra={})=>({id:1,kind,team_id:1,player_id:10,player_label:'#10 Ana',...extra});
test('pass summary counts passing TD once, excludes voided captures and defensive interceptions',()=>{
 const rows=passSummary([e('pass_complete'),e('passing_touchdown'),e('pass_incomplete'),e('interception'),e('pass_complete',{voided_at:'now'})]);
 assert.deepEqual(rows[0],{key:'1:10',team_id:1,label:'#10 Ana',attempts:3,completed:2,td:1});
});
test('map never invents endpoints, preserves bounds, and escapes sporting labels',()=>{
 const l={start_x:50,start_y:80,end_x:25,end_y:10};assert.equal(valid(l),true);assert.equal(valid({...l,end_x:101}),false);assert.equal(valid({...l,end_x:'25'}),false);
 assert.deepEqual(point(0,100),[20,360]);assert.deepEqual(point(100,0),[450,35]);
 assert.doesNotMatch(mapMarkup([e('pass_complete')],1),/data-pass-id/);
 assert.match(mapMarkup([e('pass_complete',{field_location:l,player_label:'<script>'})],1),/&lt;script&gt;/);
});
