const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const c = vm.createContext({Date, calendarAgeFromCurp: () => 14});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/player_identity.js'), 'utf8'), c);

test('Explicit birth-date age respects birthday and invalid/future dates', () => {
    assert.equal(c.calendarAgeFromBirthDate('2012-07-28', new Date(2026, 6, 27)), 13);
    assert.equal(c.calendarAgeFromBirthDate('2012-07-28', new Date(2026, 6, 28)), 14);
    assert.equal(c.calendarAgeFromBirthDate('2012-02-31', new Date(2026, 6, 28)), null);
    assert.equal(c.calendarAgeFromBirthDate('2027-07-28', new Date(2026, 6, 28)), null);
});

test('Provisional mode preserves the identifier and requires private birth date', () => {
    const label = {textContent: ''};
    const field = {hidden: true, classList: {toggle(key, value) {field.hidden = value;}}};
    const form = {elements: {identity_type: {value: 'provisional'}, curp: {value: 'TEST120728MBEXLT'}, birth_date: {value: '2012-07-28'}, age: {}}, querySelector: selector => selector === '[data-identity-label]' ? label : field};
    c.updatePlayerIdentityFields(form);
    assert.equal(form.elements.curp.value, 'TEST120728MBEXLT');
    assert.equal(form.elements.curp.maxLength, 17);
    assert.equal(form.elements.birth_date.required, true);
    assert.equal(form.elements.birth_date.disabled, false);
    assert.equal(field.hidden, false);
    form.elements.identity_type.value = 'curp';
    c.updatePlayerIdentityFields(form);
    assert.equal(form.elements.curp.minLength, 18);
    assert.equal(form.elements.curp.maxLength, 18);
    assert.equal(form.elements.birth_date.disabled, true);
    assert.equal(field.hidden, true);
});
