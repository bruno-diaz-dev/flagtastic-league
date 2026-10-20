const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
    function element() {
        return {
            children: [], value: 'libre', classList: {toggle() {}},
            addEventListener() {},
            append(...items) { this.children.push(...items); },
            replaceChildren() { this.children = []; },
            set innerHTML(value) { this.html = value; },
        };
    }
    const elements = new Map();
    const context = vm.createContext({
        document: {
            querySelector(selector) {
                if (!elements.has(selector)) elements.set(selector, element());
                return elements.get(selector);
            },
            createElement: element,
        },
        isUnifiedYouthCategory: () => false,
        FormData: class { get() { return 'libre'; } },
        getLeaderboards: async () => ({ok: false}),
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/statistics.js'), 'utf8'), context);
    return {context, summary: elements.get('#statistics-import-skipped')};
}

test('summary deduplicates numbers per team/week and renders names as text', () => {
    const {context, summary} = setup();
    const row = {week: 1, team_id: 3, team_name: '<img onerror=alert(1)>', branch: 'mixto', category: 'u8', jersey_number: 0};
    context.renderSkippedStatistics({skipped: [row, row, {...row, week: 2}], preserved_weeks: [2]});
    assert.match(summary.children[0].textContent, /^3 registros/);
    assert.equal(summary.children[1].children.length, 2);
    assert.match(summary.children[1].children[0].textContent, /<img onerror=alert\(1\)>/);
    assert.match(summary.children[1].children[0].textContent, /#0$/);
    assert.equal(summary.children[1].children[0].html, undefined);
    assert.match(summary.children[2].textContent, /jornadas 2/);
    context.renderSkippedStatistics({skipped: []});
    assert.equal(summary.children.length, 0);
});

test('incomplete-passing warnings remain visible even with no unregistered jerseys', () => {
    const {context, summary} = setup();
    context.renderSkippedStatistics({warnings: [{sheet: 'Wk 2', row: 392, week: 2,
        team_name: '<b>Diablos</b>', branch: 'femenil', category: 'u14',
        jersey_number: 0, source_completed: 1, source_attempted: 0}]});
    assert.match(summary.children[0].textContent, /pases inconsistentes omitidos/);
    assert.match(summary.children[1].children[0].textContent, /Wk 2, bloque desde fila 392/);
    assert.match(summary.children[1].children[0].textContent, /1 completos y 0 intentos/);
    assert.match(summary.children[1].children[0].textContent, /<b>Diablos<\/b>/);
    assert.equal(summary.children[1].children[0].html, undefined);
});

test('slower category responses cannot replace the most recently requested leaders', async () => {
    const {context} = setup();
    const pending=[];let category='u10';const rendered=[];
    context.FormData=class {constructor(){this.category=category;} get(key){return key==='category'?this.category:'mixto';}};
    context.isUnifiedYouthCategory=()=>true;
    context.getLeaderboards=()=>new Promise(resolve=>pending.push(resolve));
    context.renderLeaderboards=data=>rendered.push(data.category);
    const first=context.loadLeaderboards();
    category='u12';const second=context.loadLeaderboards();
    pending[1]({ok:true,json:async()=>({category:'u12'})});await second;
    pending[0]({ok:true,json:async()=>({category:'u10'})});await first;
    assert.deepEqual(rendered,['u12']);
});

test('leader links retain the ranking team context on the player profile', () => {
    const {context}=setup();
    context.escapeHtml=String;
    const html=context.leaderboardIdentity({player_id:7,team_id:21,player_name:'Player',jersey_number:5,team_name:'U10 team'});
    assert.match(html,/href="\/players\/7\?team_id=21"/);
});
