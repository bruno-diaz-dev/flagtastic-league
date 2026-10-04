const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
    const nodes = new Map();
    const document = {querySelector(selector) {
        if (!nodes.has(selector)) nodes.set(selector, {innerHTML: '', textContent: '',
            classList: {toggle() {}, add() {}, remove() {}}, addEventListener() {}});
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
    assert.match(html, /Jornadas completadas<\/span><strong>1/);
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
