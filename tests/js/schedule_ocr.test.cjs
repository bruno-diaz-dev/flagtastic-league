const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const context = vm.createContext({window: {}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/schedule_ocr_cells.js'), 'utf8'), context);

test('Time OCR accepts separators but never truncates a malformed reading', () => {
    assert.equal(context.scheduleTimeMinutes(' 21:00\n'), 1260);
    assert.equal(context.scheduleTimeMinutes('11.00'), 660);
    assert.equal(context.scheduleTimeMinutes('2100'), 1260);
    assert.equal(context.scheduleTimeMinutes('12100'), null);
});

test('OCR preserves real schedule breaks and irregular start times', () => {
    for (const times of [[660,720,780,900,960], [665,730,790], [660]]) {
        assert.equal(JSON.stringify(context.regularScheduleTimes(times)), JSON.stringify(times));
    }
});

test('Hourly schedule corrects OCR minute noise and a duplicated hour', () => {
    const recognized = [660,720,789,840,900,840,1029,1080,1140,1200,1260];
    const expected = [660,720,780,840,900,960,1020,1080,1140,1200,1260];
    assert.equal(
        JSON.stringify(context.regularScheduleTimes(recognized)),
        JSON.stringify(expected)
    );
});

test('Unreadable times stay empty for administrator correction', () => {
    assert.equal(JSON.stringify(context.regularScheduleTimes([660,null,780,1440])), '[660,null,780,null]');
    assert.equal(context.scheduleTimeText(null), null);
});

test('Grid detection keeps a lightly colored boundary and the full schedule', () => {
    const ratios = new Array(531).fill(0);
    ratios[26] = 1;
    for (const y of [77, 118, 159, 200, 241, 283, 324, 365, 406, 448, 489, 530]) {
        ratios[y] = y === 241 ? 0.486 : 0.68;
    }
    assert.equal(
        JSON.stringify(context.scheduleGridLineCenters(ratios, 531)),
        JSON.stringify([77, 118, 159, 200, 241, 283, 324, 365, 406, 448, 489, 530])
    );
});
