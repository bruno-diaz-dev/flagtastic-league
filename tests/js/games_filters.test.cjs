const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
    const nodes = new Map();
    function node() {
        return {value: '', innerHTML: '', textContent: '', dataset: {},
            classList: {toggle() {}, add() {}, remove() {}}, addEventListener() {}};
    }
    const document = {querySelector(selector) {
        if (!nodes.has(selector)) nodes.set(selector, node());
        return nodes.get(selector);
    }};
    document.querySelector('#referee-assignment-form').elements = {game_id: node()};
    const pending = () => new Promise(() => {});
    const context = vm.createContext({document, window: {}, getGames: pending,
        getTeams: pending, getAdminUsers: pending,
        escapeHtml: value => String(value).replaceAll('<', '&lt;').replaceAll('>', '&gt;'),
        divisionBranchLabel: branch => branch,
        isUnifiedYouthCategory: c => ['u8', 'u10', 'u12'].includes(c)});
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/games.js'), 'utf8'), context);
    context.result = [];
    vm.runInContext('renderGameCards = renderGames; renderGames = games => { result = games.map(game => game.id); };', context);
    const team = (id, name, branch='varonil', category='libre') => ({id, name, branch, category});
    const game = (id, status, week, scores=[null, null]) => ({id, status, week,
        home_team: team(1, 'Águilas'), away_team: team(2, 'Halcones'),
        home_score: scores[0], away_score: scores[1], field_number: 1});
    context.fixtures = [game(1, 'scheduled', 2), game(2, 'completed', 1, [0, 0]),
        game(3, 'postponed', 1), game(4, 'scheduled', 1, [7, 0]), game(5, 'completed', 2)];
    vm.runInContext('gamesState = fixtures;', context);
    return {nodes, context, ids() {context.renderFilteredGames(); return Array.from(context.result);}};
}

test('Default list and broad division filters show only pending games', () => {
    const s = setup();
    assert.deepEqual(s.ids(), [1]);
    s.nodes.get('#game-filter-branch').value = 'varonil';
    s.nodes.get('#game-filter-category').value = 'libre';
    s.nodes.get('#game-filter-field').value = '1';
    assert.deepEqual(s.ids(), [1]);
});

test('Selecting a jornada restores its completed, postponed and scored games', () => {
    const s = setup();
    s.nodes.get('#game-filter-week').value = '1';
    assert.deepEqual(s.ids(), [2, 3, 4]);
    s.nodes.get('#game-filter-week').value = '';
    assert.deepEqual(s.ids(), [1]);
});

test('Explicit team search includes history and still intersects jornada and field', () => {
    const s = setup();
    s.nodes.get('#game-filter-team').value = 'aguilas';
    assert.deepEqual(s.ids(), [1, 2, 3, 4, 5]);
    s.nodes.get('#game-filter-week').value = '1';
    assert.deepEqual(s.ids(), [2, 3, 4]);
    s.nodes.get('#game-filter-field').value = '2';
    assert.deepEqual(s.ids(), []);
});

test('Whitespace search does not expose hidden games', () => {
    const s = setup();
    s.nodes.get('#game-filter-team').value = '   ';
    assert.deepEqual(s.ids(), [1]);
});

test('Unplayed game score controls support referees while correction stays admin-only', () => {
    const {context: c, nodes} = setup();
    c.renderGameCards([c.fixtures[0]]);
    const pending = nodes.get('#games').innerHTML;
    assert.match(pending, /score-form scorekeeper-only/);
    assert.match(pending, /game-admin-panel scorekeeper-only/);
    assert.match(pending, /danger-button admin-only/);
    c.renderGameCards([c.fixtures[1]]);
    const completed = nodes.get('#games').innerHTML;
    assert.match(completed, /score-form admin-only/);
    assert.doesNotMatch(completed, /scorekeeper-only/);
    c.renderGameCards([c.fixtures[2]]);
    assert.doesNotMatch(nodes.get('#games').innerHTML, /class="score-form/);
});

test('Saving a score immediately removes the game from pending without a cached reload', async () => {
    const s = setup();
    s.context.FormData = class {get(name) {return name === 'home_score' ? '21' : '7';}};
    s.context.updateGamesScore = async () => ({ok: true, json: async () => ({id: 1, home_score: 21, away_score: 7})});
    const button = {disabled: false};
    const message = {textContent: ''};
    const form = {dataset: {gameId: '1'}, querySelector: selector => selector.startsWith('button') ? button : message};
    await s.context.submitGamesScore({preventDefault() {}, target: form});
    assert.deepEqual(s.ids(), []);
    s.nodes.get('#game-filter-week').value = '2';
    assert.ok(s.ids().includes(1));
});
