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
    vm.runInContext(fs.readFileSync("static/roster.js", "utf8"), context);
    const team = {
        name: "Cobras Reales", branch: "mixto", category: "libre", players: [],
        logo_url: "/api/teams/105/logo?v=content-hash&size=256"
    };
    context.renderRoster(team);
    assert.equal(nodes.get("#roster-team-logo").src, team.logo_url);
    context.renderRoster(team);
    assert.equal(nodes.get("#roster-team-logo").src, team.logo_url);
});
