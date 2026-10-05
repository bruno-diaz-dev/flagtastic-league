const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const {test} = require("node:test");
const path = require("node:path");
const code = fs.readFileSync(path.join(__dirname, "../../static/analytics.js"), "utf8");

function run(hostname) {
    const scripts = [];
    const context = vm.createContext({
        URL,
        window: {location: {hostname, origin: "https://" + hostname}},
        document: {
            querySelector: () => scripts.length ? scripts[0] : null,
            createElement: () => ({}),
            head: {appendChild: script => scripts.push(script)},
        },
    });
    vm.runInContext(code, context);
    return {context, scripts};
}

test("preview and local development never load visitor tracking", () => {
    for (const host of ["localhost", "127.0.0.1", "flagtastic-league.vercel.app", "flagtastic.online.example.test"]) {
        const {context, scripts} = run(host);
        assert.equal(scripts.length, 0);
        assert.equal(context.window.va, undefined);
    }
});

test("production loads the first-party script once with the filter queued first", () => {
    for (const host of ["flagtastic.online", "www.flagtastic.online"]) {
        const {context, scripts} = run(host);
        assert.equal(scripts.length, 1);
        assert.equal(scripts[0].src, "/_vercel/insights/script.js");
        assert.equal(scripts[0].defer, true);
        assert.equal(context.window.vaq[0][0], "beforeSend");
        vm.runInContext(code, context);
        assert.equal(scripts.length, 1);
    }
});

test("page views remove URL query and fragments and reject other events", () => {
    const {context} = run("flagtastic.online");
    const filter = context.window.vaq[0][1];
    const event = {type: "pageview", url: "https://flagtastic.online/games/53?email=private%40example.test#token"};
    assert.equal(filter(event).url, "https://flagtastic.online/games/53");
    assert.equal(event.url.includes("?email="), true);
    assert.equal(filter({type: "event", url: event.url, payload: {name: "private"}}), null);
});
