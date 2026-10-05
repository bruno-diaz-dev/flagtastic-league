const {test}=require('node:test');
const assert=require('node:assert/strict');
const {LiveFieldView,fieldMarkup,eligibleEvents}=require('../../static/live_field.js');
function harness(reduced=false) {
    const nodes=new Map();
    const root={dataset:{},querySelector(id){if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',disabled:false,addEventListener(type,cb){this[type]=cb;}});return nodes.get(id);}};
    return {root,nodes,view:new LiveFieldView(root,{reducedMotion:()=>reduced,hidden:()=>false})};
}
const play=(id,kind='pass_complete')=>({id,kind,team_id:1,player_label:'#10 Ana',receiver_label:'#7 Eva',period:1,minute:2,second:30});
const data=events=>({home_team:{id:1,name:'Tigres'},away_team:{id:2,name:'Lobos'},events});
test('confirmed passes draw curves and initial coverage does not auto replay history',()=>{
    const {view,nodes}=harness();view.update(data([play(1)]));
    assert.match(nodes.get('#live-field-stage').innerHTML,/M 145 205 Q/);
    assert.doesNotMatch(nodes.get('#live-field-stage').innerHTML,/animateMotion/);
    view.update(data([play(1),play(2)]));
    assert.match(nodes.get('#live-field-stage').innerHTML,/animateMotion/);
    const previous=nodes.get('#live-field-stage').innerHTML;
    view.update(data([play(1),play(2)]));assert.equal(nodes.get('#live-field-stage').innerHTML,previous);
    view.show(1);assert.equal(view.selectedId,1);
    view.update(data([play(1),play(2)]));assert.equal(view.selectedId,1);
});
test('touchdown runs draw lines and celebrations; reduced motion retains the information',()=>{
    const {view,nodes}=harness(true);view.update(data([]));view.update(data([play(1,'touchdown')]));
    const html=nodes.get('#live-field-stage').innerHTML;
    assert.match(html,/M 145 205 L 540 205/);assert.match(html,/¡TOUCHDOWN!/);
    assert.doesNotMatch(html,/animateMotion|live-field-celebrate/);
    view.show(1,true);assert.doesNotMatch(nodes.get('#live-field-stage').innerHTML,/animateMotion/);
});
test('voided selection is removed while attendance never changes the visual field',()=>{
    const {view,nodes,root}=harness();view.update(data([play(1,'touchdown')]));
    view.update(data([{...play(1,'touchdown'),voided_at:'2026-10-05'},play(2,'attendance')]));
    assert.equal(root.dataset.eventId,'');assert.equal(nodes.get('#live-field-replay').disabled,true);
    assert.doesNotMatch(nodes.get('#live-field-stage').innerHTML,/TOUCHDOWN|live-field-route/);
    assert.equal(eligibleEvents(data([play(1,'note'),play(2,'attendance')])).length,0);
});
test('neutral pauses show no player route and identities are escaped',()=>{
    assert.doesNotMatch(fieldMarkup(play(1,'halftime'),true),/animateMotion|class="live-field-route/);
    assert.match(fieldMarkup(play(1,'two_minute_warning'),false),/Pausa de los 2 minutos/);
    const {view,nodes}=harness();view.update(data([{...play(1),player_label:'<script>',receiver_label:'<img onerror=alert(1)>'}]));
    assert.equal(nodes.get('#live-field-caption').textContent,'Tigres · <script> · → <img onerror=alert(1)> · P1 02:30');
    assert.doesNotMatch(nodes.get('#live-field-stage').innerHTML,/<script>|<img/);
});

