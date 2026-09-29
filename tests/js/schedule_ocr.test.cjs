const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const context = vm.createContext({window: {}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static/schedule_ocr_cells.js'), 'utf8'), context);

test('OCR preserves real schedule breaks and irregular start times', () => {
    for (const times of [[660,720,780,900,960], [665,730,790], [660]]) {
        assert.equal(JSON.stringify(context.regularScheduleTimes(times)), JSON.stringify(times));
    }
});

test('Unreadable times cannot become invented midnight games', () => {
    for (const times of [[], [null], [660,null,780], [660,1440]]) {
        assert.throws(() => context.regularScheduleTimes(times));
    }
});
