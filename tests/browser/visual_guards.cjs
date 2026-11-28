// Visual guards for the public pages, rendered by the real FastAPI app.
//
// Start the app first (no database is needed for page shells), then run:
//   VISUAL_BASE_URL=http://127.0.0.1:8000 node tests/browser/visual_guards.cjs
//
// Every /api request is answered with synthetic fixtures that include the
// awkward cases real data produces: very long and all-caps names, teams
// without a logo, players without a photo, three-digit numbers, unresolved
// bracket games. At each width the guard fails on horizontal page overflow,
// text cut off sideways, content escaping its card, overlapping cards,
// broken images, missing league fonts and any script or console error.
// Screenshots are written to visual-guards/ for review.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const BASE = (process.env.VISUAL_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const OUT = 'visual-guards';
const WIDTHS = [320, 390, 768, 1280];
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64');

const LONG_TEAM = 'CLUB DEPORTIVO DIABLOS DEL SOL DE AGUASCALIENTES TINTO';
const teams = [
    {id: 1, name: LONG_TEAM, branch: 'femenil', category: 'u14', status: 'active', logo_url: '/api/teams/1/logo?size=256', coach: null, head_coach: 'MARÍA FERNANDA LÓPEZ DE LA TORRE', manager: 'Ana Ruiz-Esparza'},
    {id: 2, name: 'lobos', branch: 'femenil', category: 'u14', status: 'active', logo_url: null, coach: null, head_coach: null, manager: null},
    {id: 3, name: 'Rancheros Infantil A.C', branch: 'mixto', category: 'u10', status: 'pending', logo_url: '/api/teams/3/logo?size=256', coach: null, head_coach: null, manager: null},
    {id: 4, name: 'Nómadas', branch: 'varonil', category: 'libre', status: 'active', logo_url: null, coach: null, head_coach: null, manager: null},
];
const team = (id) => {
    const t = teams.find((entry) => entry.id === id);
    return {id: t.id, name: t.name, branch: t.branch, category: t.category, logo_url: t.logo_url};
};
const games = [
    {id: 10, home_team: team(1), away_team: team(2), home_score: 36, away_score: 30, week: 6, field_number: 1, start_time: '13:00:00', game_date: '2026-11-21', venue: 'Cd Industrial', status: 'completed', is_friendly: false, bracket_label: null, bracket_pending: false},
    {id: 11, home_team: team(3), away_team: team(4), home_score: null, away_score: null, week: 7, field_number: 2, start_time: '14:00:00', game_date: '2026-11-28', venue: null, status: 'scheduled', is_friendly: true, bracket_label: null, bracket_pending: false},
    {id: 12, home_team: team(1), away_team: team(2), home_score: null, away_score: null, week: 7, field_number: 8, start_time: '21:00:00', game_date: null, venue: null, status: 'scheduled', is_friendly: false, bracket_label: 'Final Golden Fem 14', bracket_pending: false},
    {id: 13, home_team: {id: null, name: 'Final U12 en espera de equipos', branch: null, category: 'u12', logo_url: null}, away_team: {id: null, name: 'Final U12 en espera de equipos', branch: null, category: 'u12', logo_url: null}, home_score: null, away_score: null, week: 7, field_number: 1, start_time: '15:00:00', game_date: null, venue: null, status: 'scheduled', is_friendly: false, bracket_label: 'Final U12', bracket_pending: true},
];
const player = (id, name, jersey, photo, aka = null) => ({id, name, aka, age: 14, jersey_number: jersey, profile_photo_url: photo ? `/media/profiles/${id}.png` : null});
const roster = {
    ...teams[0], can_manage: false, roster_closed: true, roster_closes_at: '2026-10-16T23:59:00-06:00',
    players: [
        player(1, 'ANDRICK SAID MONTELONGO ROSALES DE LA PEÑA', 0, true),
        player(2, 'diego de leon garcia', 7, false),
        player(3, 'Fernanda Solórzano', 999, true, 'LaFernandaSinEspaciosParaVerificarElAncho'),
        player(4, 'Ximena Ruiz-Esparza', 12, false),
    ],
};
const standings = [
    {team_id: 1, team_name: LONG_TEAM, team_logo_url: '/api/teams/1/logo?size=256', games_played: 6, wins: 6, losses: 0, points_for: 214, points_against: 98, point_difference: 116},
    {team_id: 2, team_name: 'lobos', team_logo_url: null, games_played: 6, wins: 1, losses: 5, points_for: 77, points_against: 190, point_difference: -113},
];
const leader = (id, name, value, photo, aka = null) => ({
    player_id: id, team_id: 1, player_name: name, player_aka: aka, team_name: LONG_TEAM, jersey_number: 100 + id,
    profile_photo_url: photo ? `/media/profiles/${id}.png` : null, value, rank: id,
    passes_completed: 316, passes_attempted: 417, passing_points: 30, passes_intercepted: 2,
});
const leaderRows = [
    leader(1, 'MARÍA FERNANDA NOMBRE LARGO APELLIDO COMPLETO', 75.8, true),
    leader(2, 'ana lópez', 70.3, false, 'UnaAliasMuyLargoSinEspaciosParaVerificarElAncho'),
];
const leaderboards = {
    passer_rating: leaderRows, receptions: leaderRows, points: leaderRows, tackles: leaderRows,
    interceptions: leaderRows, sacks: leaderRows, completion_percentage: leaderRows,
    tie_breakers: {passer_rating: 'Índice exacto; después más intentos y más pases completos. Mínimo: 50 intentos acumulados.', points: 'Más puntos; después más recepciones.'},
    passing_qualification: {latest_week: 6, minimum_attempts: 50},
    passer_rating_formula: {points_per_completion_cap: 2.5, interception_rate_cap: 0.1},
};

function fixture(pathname) {
    if (pathname === '/api/auth/session') return {user: null};
    if (pathname === '/api/teams') return teams;
    if (pathname === '/api/games') return games;
    if (pathname === '/api/teams/1') return roster;
    if (pathname === '/api/standings') return standings;
    if (pathname === '/api/statistics/leaderboards') return leaderboards;
    return undefined;
}

const PAGES = [
    {name: 'teams', path: '/teams', ready: '.team-card'},
    {name: 'games', path: '/games', ready: '.game-card'},
    {name: 'standings', path: '/standings', ready: '.standings-team', prepare: async (page) => {
        await page.selectOption('#standings-branch', 'femenil').catch(() => {});
        await page.selectOption('#standings-category', 'u14').catch(() => {});
        await page.locator('form button[type=submit]').first().click();
    }},
    {name: 'statistics', path: '/statistics', ready: '.leaderboard-panel'},
    {name: 'roster', path: '/teams/1/roster', ready: '.roster-player'},
    {name: 'login', path: '/login', ready: '#login-form'},
];

// Runs in the page: returns a list of human-readable layout problems.
function inspectLayout() {
    const problems = [];
    const describe = (el) => `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${[...el.classList].map((c) => '.' + c).join('')} "${(el.textContent || '').trim().slice(0, 40)}"`;
    const visible = (el) => {
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
    };
    const root = document.documentElement;
    if (root.scrollWidth > root.clientWidth + 1) problems.push(`page scrolls sideways by ${root.scrollWidth - root.clientWidth}px`);

    // Text cut off sideways (ellipsis and line clamps are deliberate).
    for (const el of document.querySelectorAll('main h1, main h2, main h3, main h4, main p, main a, main strong, main span, main td, main th, main button, main label, main small')) {
        if (!visible(el) || el.closest('.hidden, [hidden], .table-scroll, .standings-table, .sr-only')) continue;
        const style = getComputedStyle(el);
        const clips = ['hidden', 'clip'].includes(style.overflowX);
        if (clips && style.textOverflow !== 'ellipsis' && !style.webkitLineClamp?.match(/\d/) && el.scrollWidth > el.clientWidth + 1) {
            problems.push(`text cut off: ${describe(el)}`);
        }
        const rect = el.getBoundingClientRect();
        if (rect.left < -1 || rect.right > root.clientWidth + 1) problems.push(`outside the screen: ${describe(el)}`);
    }

    // Content must stay inside its card, and cards must not overlap.
    const cards = [...document.querySelectorAll('.team-card, .game-card, .roster-player, .leaderboard-panel, .auth-panel')].filter(visible);
    for (const card of cards) {
        const box = card.getBoundingClientRect();
        for (const child of card.querySelectorAll('*')) {
            if (!visible(child) || child.closest('.hidden, [hidden], .sr-only')) continue;
            const r = child.getBoundingClientRect();
            if (r.left < box.left - 1 || r.right > box.right + 1) {
                problems.push(`escapes its card: ${describe(child)} in ${describe(card)}`);
                break;
            }
        }
    }
    for (let i = 0; i < cards.length; i += 1) {
        for (let j = i + 1; j < cards.length; j += 1) {
            if (cards[i].parentElement !== cards[j].parentElement) continue;
            const a = cards[i].getBoundingClientRect();
            const b = cards[j].getBoundingClientRect();
            const overlap = Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
            if (overlap) problems.push(`cards overlap: ${describe(cards[i])} and ${describe(cards[j])}`);
        }
    }

    for (const img of document.querySelectorAll('main img')) {
        if (visible(img) && img.complete && img.naturalWidth === 0) problems.push(`broken image: ${img.getAttribute('src')}`);
    }
    return problems;
}

(async () => {
    fs.mkdirSync(OUT, {recursive: true});
    const browser = await chromium.launch({headless: true, args: ['--no-sandbox']});
    const failures = [];
    for (const width of WIDTHS) {
        const context = await browser.newContext({viewport: {width, height: 900}, isMobile: width < 768, hasTouch: width < 768});
        const unexpected = [];
        await context.route('**/*', async (route) => {
            const url = new URL(route.request().url());
            if (url.origin !== new URL(BASE).origin) return route.abort();
            if (url.pathname.startsWith('/media/') || /^\/api\/teams\/\d+\/logo$/.test(url.pathname)) {
                return route.fulfill({contentType: 'image/png', body: PNG});
            }
            if (url.pathname.startsWith('/api/')) {
                const body = fixture(url.pathname);
                if (body === undefined) {
                    unexpected.push(`${route.request().method()} ${url.pathname}`);
                    return route.fulfill({status: 404, contentType: 'application/json', body: '{"detail":"fixture missing"}'});
                }
                return route.fulfill({contentType: 'application/json', body: JSON.stringify(body)});
            }
            return route.continue();
        });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', (error) => errors.push(`script error: ${error.message}`));
        page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });

        for (const target of PAGES) {
            errors.length = 0;
            unexpected.length = 0;
            await page.goto(BASE + target.path, {waitUntil: 'load'});
            if (target.prepare) await target.prepare(page);
            await page.locator(target.ready).first().waitFor({timeout: 10000});
            await page.evaluate(() => document.fonts.ready);
            await page.waitForTimeout(250);
            const fonts = await page.evaluate(() => {
                const loaded = (family) => [...document.fonts].some((face) => face.family.replace(/"/g, '') === family && face.status === 'loaded');
                return {display: loaded('Barlow Condensed'), body: loaded('Inter')};
            });
            const problems = await page.evaluate(inspectLayout);
            if (!fonts.display || !fonts.body) problems.push(`league fonts not loaded: ${JSON.stringify(fonts)}`);
            problems.push(...errors, ...unexpected.map((request) => `request without fixture: ${request}`));
            await page.screenshot({path: path.join(OUT, `${target.name}-${width}.png`), fullPage: true});
            for (const problem of new Set(problems)) failures.push(`${target.path} at ${width}px: ${problem}`);
        }

        // Page-specific expectations.
        await page.goto(BASE + '/login', {waitUntil: 'load'});
        assert.equal(await page.locator('a[href="/forgot-password"]').count(), 1, 'login links to password recovery');
        await page.goto(BASE + '/teams', {waitUntil: 'load'});
        await page.locator('.team-card').first().waitFor();
        const titles = (await page.locator('.team-card h3').allTextContents()).map((title) => title.trim());
        assert.ok(titles.includes('Club Deportivo Diablos del Sol de Aguascalientes Tinto'), `team names use display casing: ${titles}`);
        assert.ok(titles.includes('Lobos') && titles.includes('Rancheros Infantil A.C'), `display casing keeps initialisms: ${titles}`);
        const initials = (await page.locator('.team-card .team-logo-placeholder').allTextContents()).map((text) => text.trim());
        assert.ok(initials.includes('L') && initials.includes('N'), `teams without a logo show initials: ${initials}`);
        await context.close();
    }
    await browser.close();
    if (failures.length) {
        console.error(`Visual guards found ${failures.length} problem(s):\n- ${failures.join('\n- ')}`);
        process.exit(1);
    }
    console.log(`Visual guards passed: ${PAGES.length} pages at ${WIDTHS.join(', ')} px. Screenshots in ${OUT}/.`);
})().catch((error) => { console.error(error); process.exit(1); });
