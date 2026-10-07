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
