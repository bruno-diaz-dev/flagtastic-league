const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({setTimeout,clearTimeout});
vm.runInContext(fs.readFileSync('static/live_capture_queue.js','utf8'),context);

function memoryStore() {
    const entries = new Map();
    return {
        entries,
        async list() { return [...entries.values()].sort((a,b)=>a.createdAt-b.createdAt); },
        async put(row) { entries.set(row.id, structuredClone(row)); },
        async remove(id) { entries.delete(id); }
    };
}
const labels = {player:'#1 Ana',receiver:'#2 Eva',team:'Tigres'};
const payload = id => ({client_id:id,kind:'pass_complete',team_id:1,player_id:1,receiver_id:2,period:1,minute:5,second:0});
function queue(store,send,extra={}) {
    return new context.LiveCaptureQueue({store,send,onChange(){},onConfirmed(){},onError(){},schedule(){return 1;},cancel(){},...extra});
}

test('capture persists before upload and accepts the next play during an in-flight write',async()=>{
    const store=memoryStore(); let release; const sent=[];
    const q=queue(store,async play=>{sent.push(play.client_id);if(sent.length===1)await new Promise(r=>release=r);});
    await q.enqueue(payload('one'),labels);
    assert.equal(store.entries.size,1);
    const sending=q.flush();
    while(!release)await new Promise(r=>setImmediate(r));
    await q.enqueue(payload('two'),labels);
    assert.equal(store.entries.size,2);
    release();await sending;
    assert.deepEqual(sent,['one','two']);
    assert.equal(store.entries.size,0);
});

test('ambiguous network failure survives reload and reuses the original UUID without duplicates',async()=>{
    const store=memoryStore();const accepted=new Set();let loseResponse=true;
    const send=async play=>{accepted.add(play.client_id);if(loseResponse){loseResponse=false;throw Error('Lost response');}};
    const first=queue(store,send);
    await first.enqueue(payload('same-uuid'),labels);await first.flush();
    assert.equal(store.entries.size,1);assert.equal(first.rows[0].status,'retry');
    const restored=queue(store,send);await restored.reload();await restored.flush();
    assert.equal(accepted.size,1);assert.equal(store.entries.size,0);
});

test('server rejection preserves all plays and blocks following uploads until the rejected selection is corrected',async()=>{
    const store=memoryStore();const sent=[];
    const q=queue(store,async play=>{if(play.player_id===1){const e=Error('Wrong player');e.status=422;throw e;}sent.push(play.client_id);});
    await q.enqueue(payload('bad'),labels);await q.enqueue(payload('next'),labels);await q.flush();
    assert.equal(q.rows[0].status,'blocked');assert.equal(store.entries.size,2);assert.equal(sent.length,0);
    await q.replace('bad',{...payload('unused-new-id'),player_id:3},labels);await q.flush();
    assert.deepEqual(sent,['bad']); // The second still has the original invalid player.
    assert.equal(store.entries.size,1);assert.equal(q.rows[0].id,'next');
});

test('offline capture remains durable and closed games never upload pending plays',async()=>{
    const store=memoryStore();let canSend=false;let sent=0;
    const q=queue(store,async()=>{sent++;},{canSend:()=>canSend});
    await q.enqueue(payload('offline'),labels);await q.flush();
    assert.equal(sent,0);assert.equal(store.entries.size,1);
    canSend=true;await q.flush();assert.equal(sent,1);assert.equal(store.entries.size,0);
});

test('storage failure never reports a play as captured or sends it',async()=>{
    const store=memoryStore();store.put=async()=>{throw Error('Disk full');};let sent=0;
    const q=queue(store,async()=>{sent++;});
    await assert.rejects(q.enqueue(payload('unsaved'),labels),/Disk full/);
    assert.equal(sent,0);assert.equal(store.entries.size,0);
});
