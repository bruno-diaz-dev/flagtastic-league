const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {test} = require('node:test');

function harness(role) {
    const nodes = new Map();
    const node = selector => {
        if (!nodes.has(selector)) nodes.set(selector, {
            dataset:{gameId:'5'}, value:'', innerHTML:'', textContent:'',
            addEventListener(){}, classList:{hidden:false,add(){},toggle(name,value){this[name]=value;}},
            querySelectorAll(){return [];},
        });
        return nodes.get(selector);
    };
    const form = node('#live-event-form');
    form.elements = Object.fromEntries(['team_id','kind','player_id','receiver_id','note'].map(key => [key,node(key)]));
    form.elements.kind.value = 'pass_complete';
    const context = vm.createContext({
        document:{querySelector:node,addEventListener(){},hidden:false},
        window:{addEventListener(){}}, fetch:()=>new Promise(()=>{}),
        clearTimeout(){},setTimeout(){},
        escapeHtml:value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../../static/live_game.js'),'utf8'),context);
    if (role) vm.runInContext(`liveUser={roles:['${role}']}`,context);
    return {node,context,form};
}

function snapshot(state='live',version=2) {
    return {state,version,home_team:{id:1,name:'Home'},away_team:{id:2,name:'Away'},home_score:6,away_score:0,roster:[],statistics:[],events:[{id:1,kind:'touchdown',team_id:1,period:1,minute:12,second:3,player_label:'<Scorer>',note:'<script>',voided_at:null}]};
}

test('public sporting feed escapes text and hides capture/corrections',()=>{
    const {node,context}=harness();context.renderLive(snapshot());
    assert.equal(node('#live-official-controls').classList.hidden,true);
    assert.match(node('#live-timeline').innerHTML,/&lt;Scorer&gt;/);
    assert.doesNotMatch(node('#live-timeline').innerHTML,/<script>|data-void-event/);
    assert.equal(node('#live-home-score').textContent,6);
});

test('referee captures only live games and administrators correct only completed games',()=>{
    const referee=harness('referee');referee.context.renderLive(snapshot());
    assert.equal(referee.node('#live-capture-panel').classList.hidden,false);
    assert.match(referee.node('#live-timeline').innerHTML,/data-void-event/);
    referee.context.renderLive(snapshot('completed',3));
    assert.equal(referee.node('#live-capture-panel').classList.hidden,true);
    assert.doesNotMatch(referee.node('#live-timeline').innerHTML,/data-void-event/);
    const admin=harness('league_admin');admin.context.renderLive(snapshot('completed'));
    assert.equal(admin.node('#live-official-controls').classList.hidden,true);
    assert.match(admin.node('#live-timeline').innerHTML,/data-void-event/);
});

test('stale refresh cannot overwrite newer score and pass fields match event type',()=>{
    const {node,context,form}=harness('referee');context.renderLive(snapshot('live',5));
    context.renderLive({...snapshot('live',4),home_score:0});
    assert.equal(node('#live-home-score').textContent,6);
    form.elements.kind.value='passing_touchdown';context.liveKindControls();
    assert.equal(form.elements.receiver_id.required,true);
    form.elements.kind.value='flag';context.liveKindControls();
    assert.equal(form.elements.receiver_id.disabled,true);
    form.elements.kind.value='note';context.liveKindControls();
    assert.equal(form.elements.player_id.required,false);
    assert.equal(form.elements.note.required,true);
});
