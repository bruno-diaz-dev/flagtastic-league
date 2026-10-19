const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../static/weekly_featured.js'), 'utf8');
const context = vm.createContext({});
vm.runInContext(source, context);
const game = (id, week, home, away, extra = {}) => ({id, week, home_score: home, away_score: away, status: 'completed', ...extra});
const ids = games => Array.from(context.selectWeeklyFeaturedGames(games), g => g.id);

test('Each week gets its own highest combined final score, newest week first', () => {
    const games = [game(1, 1, 40, 27), game(2, 1, 12, 6), game(3, 2, 30, 20), game(4, 3, 0, 6)];
    const original = JSON.stringify(games);
    assert.deepEqual(ids(games), [4, 3, 1]);
    assert.equal(JSON.stringify(games), original);
});

test('Friendlies, postponed games, incomplete scores and invalid values cannot be featured', () => {
    assert.deepEqual(ids([
        game(1, 1, 200, 100, {is_friendly: true}),
        game(2, 1, 120, 90, {status: 'postponed'}),
        game(3, 1, null, 90), game(4, 1, '40', '30'),
        game(5, 1, -1, 100), game(6, 1, 40, 30, {status: 'scheduled'}),
        game(7, 1, 12, 0)
    ]), [7]);
    assert.deepEqual(ids([]), []);
});

test('Equal point totals prefer a closer game, then stable game ID regardless of response order', () => {
    const games = [game(3, 1, 70, 0), game(2, 1, 40, 30), game(1, 1, 30, 40)];
    assert.deepEqual(ids(games), [1]);
    assert.deepEqual(ids(games.reverse()), [1]);
});

test('Rendering hides empty weeks and escapes team names', () => {
    const section = {hidden: false}, list = {innerHTML: ''};
    context.document = {querySelector: selector => selector === '#weekly-featured' ? section : list};
    context.escapeHtml = text => String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
    context.divisionBranchLabel = branch => branch;
    context.renderWeeklyFeaturedGames([]);
    assert.equal(section.hidden, true);
    context.renderWeeklyFeaturedGames([game(1, 1, 20, 6, {
        home_team: {name: '<script>unsafe</script>', branch: 'mixto', category: 'u12'},
        away_team: {name: 'Away', branch: 'mixto', category: 'u12'}
    })]);
    assert.equal(section.hidden, false);
    assert.match(list.innerHTML, /26<\/strong> puntos combinados/);
    assert.doesNotMatch(list.innerHTML, /<script>/);
    assert.match(list.innerHTML, /href="\/games\/1"/);
});
