const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

test("roster preserves the versioned thumbnail URL across repeated renders", () => {
    const nodes = new Map();
    const context = vm.createContext({
        document: {querySelector(selector) {
            if (!nodes.has(selector)) nodes.set(selector, {
                dataset: {teamId: "105"}, addEventListener() {},
                classList: {add() {}, remove() {}},
                elements: {head_coach: {}, coach: {}, manager: {}}
            });
            return nodes.get(selector);
        }},
        divisionBranchLabel: branch => branch
    });
    const source = fs.readFileSync("static/roster.js", "utf8");
    vm.runInContext(source.slice(0, source.indexOf("async function loadRoster")), context);
    const team = {
        name: "Cobras Reales", branch: "mixto", category: "libre", players: [],
        logo_url: "/api/teams/105/logo?v=content-hash&size=256"
    };
    context.renderRoster(team);
    assert.equal(nodes.get("#roster-team-logo").src, team.logo_url);
    context.renderRoster(team);
    assert.equal(nodes.get("#roster-team-logo").src, team.logo_url);
});

test("roster permission and closure message follow server state", async () => {
    const nodes = new Map();
    const toggles = new Map();
    let team = {
        name: "Test", branch: "mixto", category: "u8", players: [],
        can_manage: true, roster_closed: false,
    };
    const context = vm.createContext({
        document: {
            body: {classList: {toggle: (name, value) => toggles.set(name, value)}},
            querySelector(selector) {
                if (!nodes.has(selector)) nodes.set(selector, {
                    dataset: {teamId: "1"}, addEventListener() {},
                    classList: {add() {}, remove() {}},
                    elements: {head_coach: {}, coach: {}, manager: {}},
                });
                return nodes.get(selector);
            },
        },
        divisionBranchLabel: branch => branch,
        getTeamDetail: async () => ({ok: true, json: async () => team}),
    });
    const source = fs.readFileSync("static/roster.js", "utf8");
    vm.runInContext(source.slice(0, source.indexOf('playerForm.addEventListener("submit"')), context);
    await context.loadRoster();
    assert.equal(toggles.get("can-manage-team"), true);
    assert.match(nodes.get("#roster-deadline-message").textContent, /16 de octubre de 2026, 00:00/);
    team = {...team, can_manage: false, roster_closed: true};
    await context.loadRoster();
    assert.equal(toggles.get("can-manage-team"), false);
    assert.match(nodes.get("#roster-deadline-message").textContent, /Roster cerrado/);
    team = {...team, can_manage: true};
    await context.loadRoster();
    assert.equal(toggles.get("can-manage-team"), true);
});
