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
    form.elements = Object.fromEntries(['team_id','kind','player_id','receiver_id'].map(key => [key,node(key)]));
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
    assert.equal(form.elements.player_id.required,true);
});

test('start failures describe server and permission problems instead of invalid play data',async()=>{
    const {context}=harness();
    context.fetch=async()=>({ok:false,status:500,json:async()=>{throw Error('Not JSON');}});
    await assert.rejects(context.liveWrite('start'),/servidor/);
    context.fetch=async()=>({ok:false,status:403,json:async()=>({})});
    await assert.rejects(context.liveWrite('start'),/permiso/);
    context.fetch=async()=>({ok:false,status:422,json:async()=>({detail:[{msg:'Selecciona receptor'}]})});
    await assert.rejects(context.liveWrite('events'),/Selecciona receptor/);
});

test('narration comes from statistics without descriptions for every sporting event',()=>{
    const {context,node}=harness();
    const event={player_label:'#12 Ana',receiver_label:'#7 Eva',note:'Manual text must not appear'};
    const expected={
        pass_complete:'completa un pase con #7 Eva',
        pass_incomplete:'Pase incompleto',
        passing_touchdown:'conecta con #7 Eva para touchdown. +6 puntos',
        touchdown:'touchdown por carrera o retorno. +6 puntos',
        extra_one:'conversión de 1 punto',extra_two:'conversión de 2 puntos',
        safety:'safety. +2 puntos',sack:'consigue un sack',
        flag:'retira un flag',interception:'intercepta el pase',attendance:'asistencia',
    };
    for(const [kind,phrase] of Object.entries(expected)) {
        const text=context.liveNarrative({...event,kind},'Tigres');
        assert.ok(text.includes(phrase),kind);
        assert.ok(text.includes('Tigres'));
        assert.ok(!text.includes(event.note));
    }
    context.renderLive(snapshot());
    assert.doesNotMatch(node('#live-timeline').innerHTML,/&lt;script&gt;/);
});
