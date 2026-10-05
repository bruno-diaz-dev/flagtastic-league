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
            listeners:{}, addEventListener(name,handler){this.listeners[name]=handler;}, classList:{hidden:false,add(){},toggle(name,value){this[name]=value;}},
            querySelectorAll(){return [];},
        });
        return nodes.get(selector);
    };
    const form = node('#live-event-form');
    form.elements = Object.fromEntries(['team_id','kind','player_id','receiver_id','period','minute','second'].map(key => [key,node(key)]));
    form.reportValidity = () => true;
    form.elements.kind.value = 'pass_complete';
    const context = vm.createContext({
        document:{querySelector:node,addEventListener(){},hidden:false},
        window:{addEventListener(){}}, fetch:()=>new Promise(()=>{}),
        AbortController, crypto: require('node:crypto').webcrypto, navigator:{onLine:true},
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

test('quick capture remembers each team passer and does not retain the previous receiver',()=>{
    const {context,form,node}=harness('referee');
    form.elements.team_id.value='1';
    const data={...snapshot(),roster:[{team_id:1,player_id:10,jersey_number:10,display_name:'Ana'},{team_id:1,player_id:11,jersey_number:11,display_name:'Eva'},{team_id:2,player_id:20,jersey_number:20,display_name:'Luz'}]};
    context.renderLive(data);
    form.elements.player_id.value='10';context.liveRememberPlayer();
    assert.equal(node('#live-passer-choices').open,false);
    form.elements.receiver_id.value='11';context.liveSelectKind('passing_touchdown');
    assert.equal(form.elements.player_id.value,'10');assert.equal(form.elements.receiver_id.value,'');
    context.liveSelectTeam(2);form.elements.player_id.value='20';context.liveRememberPlayer();
    context.liveSelectTeam(1);assert.equal(form.elements.player_id.value,'10');
    context.liveSelectKind('flag');assert.equal(form.elements.player_id.value,'');
    context.liveSelectKind('pass_complete');assert.equal(form.elements.player_id.value,'10');
});

test('next play is captured durably while an earlier upload is in progress; public score is not guessed',async()=>{
    const {context,form,node}=harness('referee');form.elements.team_id.value='1';context.renderLive(snapshot());
    form.elements.player_id.value='10';form.elements.receiver_id.value='11';
    form.elements.period.value='2';form.elements.minute.value='8';form.elements.second.value='12';
    const captured=[];
    context.mockQueue={working:true,rows:[{id:'previous'}],async enqueue(play){captured.push(play);},async flush(){}};
    vm.runInContext('liveQueue=mockQueue',context);
    await context.liveCapturePlay();
    assert.equal(captured.length,1);assert.equal(captured[0].minute,8);assert.ok(captured[0].client_id);
    assert.equal(form.elements.player_id.value,'10');assert.equal(form.elements.receiver_id.value,'');
    assert.equal(node('#live-home-score').textContent,6);
    assert.match(node('#live-operation-message').textContent,/Guardada en este dispositivo/);
});

test('finalization is blocked by pending plays even if the button handler is invoked directly',async()=>{
    const {context,node}=harness('referee');context.renderLive(snapshot());let writes=0;
    context.mockQueue={rows:[{id:'pending'}],working:false,async reload(){}};
    context.fetch=async()=>{writes++;throw Error('Unexpected write');};
    vm.runInContext('liveQueue=mockQueue',context);
    await node('#live-finish').listeners.click();
    assert.equal(writes,0);assert.match(node('#live-operation-message').textContent,/sin confirmar/);
});


test('attendance stays out of sporting feed and moments require no player',async()=>{
    const {context,node,form}=harness('referee');
    const data=snapshot();data.events.push({id:2,kind:'attendance',team_id:1,player_label:'Ana'});
    context.renderLive(data);
    assert.doesNotMatch(node('#live-kind-buttons').innerHTML,/attendance/);
    assert.doesNotMatch(node('#live-timeline').innerHTML,/Asistencia|Ana/);
    assert.equal(context.liveNarrative({kind:'halftime'},'Away'),'Medio tiempo del partido.');
    assert.equal(context.liveNarrative({kind:'two_minute_warning'},'Away'),'Pausa de los 2 minutos.');
    const captured=[];
    context.mockQueue={async enqueue(p){captured.push(p);},async flush(){}};
    vm.runInContext('liveQueue=mockQueue',context);
    form.elements.period.value='1';form.elements.minute.value='2';form.elements.second.value='0';
    await context.liveCaptureAdministrative('two_minute_warning');
    assert.equal(captured.length,1);assert.equal(captured[0].team_id,null);assert.equal(captured[0].player_id,null);
    form.elements.second.value='60';await context.liveCaptureAdministrative('halftime');
    assert.equal(captured.length,1);
});
