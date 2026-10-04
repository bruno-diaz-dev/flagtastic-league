const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup({width = 390, pathname = '/teams/42/roster', blockedStorage = false} = {}) {
    const handlers = {};
    const classes = new Set(['sidebar-collapsed']);
    const node = (text = '') => ({textContent: text, attributes: {}, focused: false,
        setAttribute(key, value) {this.attributes[key] = value;},
        getAttribute(key) {return this.attributes[key];},
        classList: {add() {}, remove() {}}, addEventListener() {},
        focus() {this.focused = true; document.activeElement = this;},
        getClientRects() {return [{}];}});
    const toggle = node();
    const label = node();
    const links = ['/teams', '/games', '/referees', '/referee/games'].map(href => {
        const link = node(); link.attributes.href = href;
        link.querySelector = () => node(href.slice(1)); return link;
    });
    const document = {title: '', activeElement: null,
        body: {classList: {contains: c => classes.has(c), toggle(c, value) {value ? classes.add(c) : classes.delete(c);}}},
        querySelector: selector => selector === '#sidebar-toggle' ? toggle : selector === '#current-page-label' ? label : selector === '.content h2' ? node('Equipos') : null,
        querySelectorAll: selector => selector.startsWith('.sidebar') ? [toggle, ...links] : links,
        addEventListener: (name, handler) => {handlers[name] = handler;}};
    const c = vm.createContext({document, window: {innerWidth: width, location: {pathname}, addEventListener() {}},
        localStorage: {getItem() {if (blockedStorage) throw Error('blocked'); return null;}, setItem() {if (blockedStorage) throw Error('blocked');}}});
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/layout.js'), 'utf8'), c);
    return {c, classes, links, toggle, label, document, handlers};
}

test('Nested pages select their parent navigation and name the current screen', () => {
    const s = setup();
    assert.equal(s.links[0].attributes['aria-current'], 'page');
    assert.equal(s.links[1].attributes['aria-current'], undefined);
    assert.equal(s.links[0].attributes['aria-label'], 'teams');
    assert.equal(s.document.title, 'Equipos | FlagTastic');
    assert.equal(s.label.textContent, 'Equipos');
    assert.equal(setup({pathname: '/referee/games'}).links[3].attributes['aria-current'], 'page');
});

test('Responsive navigation works when browser storage is blocked', () => {
    assert.ok(setup({blockedStorage: true}).classes.has('sidebar-collapsed'));
    assert.ok(!setup({width: 1280, blockedStorage: true}).classes.has('sidebar-collapsed'));
});

test('Mobile drawer cycles focus and restores focus when closed', () => {
    const s = setup();
    s.c.setSidebarCollapsed(false);
    s.document.activeElement = s.links.at(-1);
    let prevented = false;
    s.handlers.keydown({key: 'Tab', shiftKey: false, preventDefault() {prevented = true;}});
    assert.equal(prevented, true);
    assert.equal(s.document.activeElement, s.toggle);
    s.handlers.keydown({key: 'Tab', shiftKey: true, preventDefault() {}});
    assert.equal(s.document.activeElement, s.links.at(-1));
    s.handlers.keydown({key: 'Escape'});
    assert.ok(s.classes.has('sidebar-collapsed'));
    assert.equal(s.document.activeElement, s.toggle);
});

test('Native validation opens all containing disclosures before field focus', () => {
    const s = setup();
    const outer = {open: false, parentElement: {closest: () => null}};
    const inner = {open: false, parentElement: {closest: () => outer}};
    s.handlers.invalid({target: {closest: () => inner}});
    assert.equal(inner.open, true);
    assert.equal(outer.open, true);
});
