const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function harness() {
    const nodes = new Map();
    const node = (selector) => {
        if (!nodes.has(selector)) nodes.set(selector, {
            dataset: { userId: '42' }, textContent: '', innerHTML: '',
            classList: { add() {}, remove() {} }, addEventListener() {}
        });
        return nodes.get(selector);
    };
    const context = vm.createContext({
        document: { querySelector: node },
        window: { location: { assign() {} } },
        getPublicRefereeProfile: () => new Promise(() => {}),
        escapeHtml: (value) => value.replace(/[&<>"']/g, (char) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[char]))
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/referee_profile.js'), 'utf8'), context);
    return { node, render: (statistics) => context.renderRefereeProfile({
        display_name: 'Brucie', name: 'Bruno Díaz', aka: 'Brucie', statistics
    }) };
}

test('participation is sorted, proportional, and preserves source statistics', () => {
    const { node, render } = harness();
    const positions = [{ position: 'side_judge', games: 4 }, { position: 'referee', games: 6 }];
    render({ games: 10, completed_games: 8, weeks: 2, positions });
    assert.equal(node('#referee-profile-primary-position').textContent, 'Referee');
    const bars = node('#referee-profile-positions').innerHTML;
    assert.ok(bars.indexOf('Referee') < bars.indexOf('Side Judge'));
    assert.match(bars, /width: 60%/);
    assert.match(bars, /width: 40%/);
    assert.equal(positions[0].position, 'side_judge');
    const stats = node('#referee-profile-stats').innerHTML;
    assert.match(stats, /<strong>8<\/strong><span>Partidos completados/);
    assert.match(stats, /<strong>10<\/strong><span>Partidos registrados/);
});

test('empty and zero-count participation show an empty state without invalid percentages', () => {
    for (const positions of [[], [{ position: 'referee', games: 0 }]]) {
        const { node, render } = harness();
        render({ games: 0, completed_games: 0, weeks: 0, positions });
        assert.equal(node('#referee-profile-primary-position').textContent, 'Sin asignaciones');
        assert.match(node('#referee-profile-positions').innerHTML, /Sin asignaciones registradas/);
        assert.doesNotMatch(node('#referee-profile-positions').innerHTML, /NaN|Infinity/);
    }
});

test('unknown position labels are escaped in the chart', () => {
    const { node, render } = harness();
    render({ games: 1, completed_games: 1, weeks: 1, positions: [{ position: '<img src=x>', games: 1 }] });
    assert.match(node('#referee-profile-positions').innerHTML, /&lt;img src=x&gt;/);
    assert.doesNotMatch(node('#referee-profile-positions').innerHTML, /<img/);
});
