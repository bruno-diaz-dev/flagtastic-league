const assert = require("node:assert/strict");
const {test} = require("node:test");
const {displayName, nameInitials} = require("../../static/display.js");

test("names read the same however they were typed", () => {
    for (const typed of ["DIABLOS DEL SOL", "Diablos del sol", "diablos  del   sol "]) {
        assert.equal(displayName(typed), "Diablos del Sol");
    }
    assert.equal(displayName("ANDRICK SAID MONTELONGO ROSALES DE LA PEÑA"), "Andrick Said Montelongo Rosales de la Peña");
    assert.equal(displayName("de la torre"), "De la Torre");
});

test("categories, initialisms and compound surnames keep their shape", () => {
    assert.equal(displayName("u14"), "U14");
    assert.equal(displayName("Rancheros Infantil A.C"), "Rancheros Infantil A.C");
    assert.equal(displayName("ximena ruiz-esparza"), "Ximena Ruiz-Esparza");
    assert.equal(displayName("KITTY’S"), "Kitty’s");
    assert.equal(displayName("ÁNGEL ÑANDÚ"), "Ángel Ñandú");
});

test("short acronyms survive unless the whole name was typed in capitals", () => {
    assert.equal(displayName("ECA"), "ECA");
    assert.equal(displayName("Black Mamba FC"), "Black Mamba FC");
    assert.equal(displayName("DIABLOS DEL SOL"), "Diablos del Sol");
    assert.equal(displayName("RANCHERAS FLAG"), "Rancheras Flag");
});

test("empty values stay empty and initials skip joining words", () => {
    assert.equal(displayName(null), "");
    assert.equal(displayName("   "), "");
    assert.equal(nameInitials("Diablos del Sol"), "DS");
    assert.equal(nameInitials("lobos"), "L");
    assert.equal(nameInitials("Ángel"), "Á");
    assert.equal(nameInitials(""), "?");
});
