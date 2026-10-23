const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
    const nodes = new Map();
    const document = {querySelector(selector) {
        if (!nodes.has(selector)) nodes.set(selector, {innerHTML: '', textContent: '',
            classList: {toggle() {}, add() {}, remove() {}},
            listeners: {}, attributes: {},
            addEventListener(event, callback) {this.listeners[event] = callback;},
            setAttribute(name, value) {this.attributes[name] = value;},
            removeAttribute(name) {delete this.attributes[name];}});
        return nodes.get(selector);
    }};
    const pending = () => new Promise(() => {});
    const context = vm.createContext({document, window: {location: {assign() {}}},
        getMyRefereeGames: pending, getMyRefereeProfile: pending, getAdminUsers: pending,
        divisionBranchLabel: branch => branch,
        escapeHtml: v => String(v).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;')});
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/referee_games.js'), 'utf8'), context);
    const game = (id, status, week, scores=[null, null], position='referee') => ({
        id, status, week, home_score: scores[0], away_score: scores[1], official_position: position,
        home_team: {id: id * 2, name: `Local ${id}`, branch: 'varonil', category: 'libre'},
        away_team: {id: id * 2 + 1, name: `Visita ${id}`, branch: 'varonil', category: 'libre'},
        start_time: '12:00:00', field_number: 1, officials: []});
    return {context, nodes, game};
}

test('Referee state separates postponed, completed, 0-0 and incomplete scores', () => {
    const {context: c, game} = setup();
    assert.equal(c.refereeGameState(game(1, 'scheduled', 1)), 'pending');
    assert.equal(c.refereeGameState(game(2, 'postponed', 1)), 'postponed');
    assert.equal(c.refereeGameState(game(3, 'scheduled', 1, [0, 0])), 'completed');
    assert.equal(c.refereeGameState(game(4, 'completed', 1)), 'completed');
    assert.equal(c.refereeGameState(game(5, 'scheduled', 1, [7, null])), 'pending');
});

test('Dashboard keeps history and postponed assignments out of upcoming work', async () => {
    const {context: c, nodes, game} = setup();
    const games = [game(1, 'scheduled', 3), game(2, 'postponed', 1),
        game(3, 'completed', 2, [0, 0]), game(4, 'completed', 1, [14, 7], 'down_judge')];
    c.getMyRefereeGames = async () => ({ok: true, status: 200, json: async () => games});
    await c.loadRefereeGames();
    const html = nodes.get('#referee-games').innerHTML;
    const upcoming = html.slice(0, html.indexOf('<details class="referee-postponed-panel">'));
    assert.match(upcoming, /Local 1/);
    assert.doesNotMatch(upcoming, /Local [234]/);
    assert.match(html, /Pospuesto/);
    assert.match(html, /Por reprogramar/);
    assert.match(html, /Mi experiencia arbitral/);
    assert.match(html, /0 - 0/);
    assert.doesNotMatch(html, /<details class="referee-history-week"[^>]*\bopen\b/);
    assert.ok(html.indexOf('Jornada 2 · 1 arbitraje') < html.indexOf('Jornada 1 · 1 arbitraje'));
    assert.match(nodes.get('#referee-summary').innerHTML, /Por arbitrar<\/span><strong>1/);
    assert.match(nodes.get('#referee-summary').innerHTML, /Próxima jornada<\/span><strong>J3/);
});

test('Historical metrics only count completed participation and escape team names', () => {
    const {context: c, game} = setup();
    const g = game(3, 'completed', 2, [0, 0]);
    g.home_team.name = '<script>bad</script>';
    const html = c.renderRefereeHistory([g]);
    assert.match(html, /Partidos arbitrados<\/span><strong>1/);
    assert.match(html, /Jornadas arbitradas<\/span><strong>1/);
    assert.match(html, /&lt;script&gt;bad&lt;\/script&gt;/);
    assert.doesNotMatch(html, /<script>/);
    assert.doesNotMatch(html, /Down Judge/);
});

test('Empty dashboard provides distinct upcoming and experience empty states', async () => {
    const {context: c, nodes} = setup();
    c.getMyRefereeGames = async () => ({ok: true, status: 200, json: async () => []});
    await c.loadRefereeGames();
    assert.match(nodes.get('#referee-games').innerHTML, /Próximas asignaciones/);
    assert.match(nodes.get('#referee-games').innerHTML, /Tu experiencia aparecerá/);
    assert.doesNotMatch(nodes.get('#referee-games').innerHTML, /width: NaN/);
    assert.match(nodes.get('#referee-summary').innerHTML, /Próxima jornada<\/span><strong>-/);
});

test('Score capture is offered only for unscored pending assignments', () => {
    const {context: c, game} = setup();
    assert.match(c.refereeGameCard(game(1, 'scheduled', 1)), /referee-score-form/);
    assert.match(c.refereeGameCard(game(1, 'scheduled', 1)), /Solo un administrador/);
    for (const g of [game(2, 'postponed', 1), game(3, 'completed', 1, [21, 7]),
        game(4, 'completed', 1), game(5, 'scheduled', 1, [7, null])]) {
        assert.doesNotMatch(c.refereeGameCard(g), /referee-score-form/);
    }
});


function confirmationSetup() {
    const s = setup();
    const row = {dataset: {gameId: '81', scheduledTime: '12:00'},
        querySelector: () => ({value: '2'}),
        querySelectorAll: () => [{value: '11', dataset: {position: 'referee'}}]};
    s.nodes.get('#schedule-review-body').querySelectorAll = () => [row];
    s.nodes.get('#referee-schedule-form').querySelectorAll = () => [];
    const button = s.nodes.get('#confirm-schedule');
    button.textContent = 'Confirmar asignaciones';
    s.context.loadRefereeGames = async () => {};
    return {...s, button, confirm: button.listeners.click,
        progress: s.nodes.get('#official-schedule-save-progress'),
        message: s.nodes.get('#official-schedule-confirm-message')};
}

test('Official confirmation exposes pending activity, prevents double submission and completes after success', async () => {
    const s = confirmationSetup();
    let release, calls = 0, submitted;
    s.context.confirmRefereeSchedule = assignments => {
        calls++; submitted = assignments;
        return new Promise(resolve => {release = resolve;});
    };
    const pending = s.confirm();
    assert.equal(s.button.disabled, true);
    assert.equal(s.button.attributes['aria-busy'], 'true');
    assert.match(s.button.textContent, /Guardando asignaciones/);
    assert.equal(s.progress.hidden, false);
    assert.equal(s.progress.attributes['aria-valuenow'], undefined);
    assert.match(s.message.textContent, /Guardando asignaciones de 1/);
    await s.confirm();
    assert.equal(calls, 1);
    assert.equal(submitted[0].game_id, 81);
    assert.equal(submitted[0].officials[0].user_id, 11);
    release({ok: true, json: async () => ({updated: 1})});
    await pending;
    assert.equal(s.progress.attributes['aria-valuenow'], '100');
    assert.match(s.message.textContent, /1 partido.*actualizado/);
    assert.equal(s.button.textContent, 'Confirmar asignaciones');
    assert.equal(s.button.attributes['aria-busy'], undefined);
    assert.equal(s.button.disabled, true);
});

test('Official confirmation shows server errors beside the button and retains review for retry', async () => {
    const s = confirmationSetup();
    s.context.confirmRefereeSchedule = async () => ({ok: false, json: async () => ({detail: [{msg: 'Oficial no disponible'}]})});
    await s.confirm();
    assert.equal(s.message.textContent, 'Oficial no disponible');
    assert.equal(s.progress.hidden, true);
    assert.equal(s.button.disabled, false);
    s.context.confirmRefereeSchedule = async () => ({ok: true, json: async () => ({updated: 1})});
    await s.confirm();
    assert.match(s.message.textContent, /actualizado/);
});

test('Official confirmation handles failed connections and restores its controls', async () => {
    const s = confirmationSetup();
    s.context.confirmRefereeSchedule = async () => {throw new Error('Network unavailable');};
    await s.confirm();
    assert.match(s.message.textContent, /No se pudo confirmar el guardado/);
    assert.equal(s.progress.hidden, true);
    assert.equal(s.button.disabled, false);
    assert.equal(s.button.attributes['aria-busy'], undefined);
});

test('A failed agenda refresh never reports a confirmed assignment save as failed', async () => {
    const s = confirmationSetup();
    s.context.confirmRefereeSchedule = async () => ({ok: true, json: async () => ({updated: 1})});
    s.context.loadRefereeGames = async () => {throw new Error('Refresh failed');};
    await s.confirm();
    assert.match(s.message.textContent, /Asignaciones guardadas/);
    assert.equal(s.progress.attributes['aria-valuenow'], '100');
    assert.equal(s.button.disabled, true);
});

test('Selected import week reaches analysis and changing it invalidates the previous review', async () => {
    const {context:c,nodes} = setup();
    let week = '4', release;
    c.FormData = class {get(key) {return key === 'file' ? 'original.xlsx' : week;}};
    const form = nodes.get('#referee-schedule-form');
    c.analyzeRefereeSchedule = (file, selected) => {
        assert.equal(file,'original.xlsx');assert.equal(selected,'4');
        return new Promise(resolve=>{release=resolve;});
    };
    const pending = form.listeners.submit({preventDefault(){}});
    week='3';form.listeners.change();
    release({ok:true,json:async()=>({selected_week:4,proposals:[]})});await pending;
    assert.equal(nodes.get('#confirm-schedule').disabled,true);
    assert.doesNotMatch(nodes.get('#schedule-review-scope').textContent,/Solo jornada 4/);
    c.analyzeRefereeSchedule = async (file,selected) => {
        assert.equal(selected,'3');return {ok:true,json:async()=>({selected_week:3,proposals:[]})};
    };
    await form.listeners.submit({preventDefault(){}});
    assert.match(nodes.get('#schedule-review-scope').textContent,/Solo jornada 3/);
});
