const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
    const nodes = new Map();
    function node() {
        return {value: '', innerHTML: '', textContent: '', open: false, disabled: false,
            classList: {toggle() {}}, addEventListener() {}, focus() {this.focused = true;},
            querySelector(selector) {return document.querySelector(selector);}};
    }
    const document = {querySelector(selector) {
        if (!nodes.has(selector)) nodes.set(selector, node());
        return nodes.get(selector);
    }};
    const c = vm.createContext({document, getTeams: () => new Promise(() => {}),
        escapeHtml: value => String(value).replaceAll('<', '&lt;').replaceAll('>', '&gt;'),
        divisionBranchLabel: branch => branch,
        isUnifiedYouthCategory: category => ['u8', 'u10', 'u12'].includes(category)});
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/teams.js'), 'utf8'), c);
    c.fixtures = [{id: 1, name: 'Águilas', branch: 'varonil', category: 'libre', status: 'active'},
        {id: 2, name: 'Aguilas Juvenil', branch: 'femenil', category: 'u14', status: 'pending'},
        {id: 3, name: 'Lobos', branch: 'mixto', category: 'u12', status: 'active'}];
    vm.runInContext('teamsState = fixtures;', c);
    return {c, nodes, filter() {return Array.from(c.getFilteredTeams(), team => team.id);}};
}

test('Name search ignores accents and intersects division filters', () => {
    const s = setup();
    s.nodes.get('#team-filter-search').value = '  aguilas  ';
    assert.deepEqual(s.filter(), [1, 2]);
    s.nodes.get('#team-filter-category').value = 'u14';
    assert.deepEqual(s.filter(), [2]);
    s.nodes.get('#team-filter-branch').value = 'varonil';
    assert.deepEqual(s.filter(), []);
    s.c.renderFilteredTeams();
    assert.equal(s.nodes.get('#teams-count').textContent, '0 de 3 equipos');
    assert.match(s.nodes.get('#teams').innerHTML, /Sin coincidencias/);
});

test('Closing registration preserves inputs and returns focus to its opener', () => {
    const {c, nodes} = setup();
    nodes.get('#team-registration').open = true;
    nodes.get('#team-category').value = 'u14';
    c.closeTeamRegistration();
    assert.equal(nodes.get('#team-registration').open, false);
    assert.equal(nodes.get('#team-category').value, 'u14');
    assert.equal(nodes.get('summary').focused, true);
});

test('Youth category ignores branch filter and team names remain escaped', () => {
    const s = setup();
    s.nodes.get('#team-filter-category').value = 'u12';
    s.nodes.get('#team-filter-branch').value = 'femenil';
    assert.deepEqual(s.filter(), [3]);
    s.c.fixtures[2].name = '<script>bad</script>';
    s.c.renderFilteredTeams();
    assert.match(s.nodes.get('#teams').innerHTML, /&lt;script&gt;/);
    assert.doesNotMatch(s.nodes.get('#teams').innerHTML, /<script>/);
});
