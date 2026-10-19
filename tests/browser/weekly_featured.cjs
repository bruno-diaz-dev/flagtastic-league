const {chromium} = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

(async () => {
    const browser = await chromium.launch({headless:true, args:['--no-sandbox']});
    const page = await browser.newPage({viewport:{width:1546, height:1000}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const team = (id, name, branch='varonil', category='libre') => ({id, name, branch, category});
    const home = team(1, 'Local'), away = team(2, 'Visitante');
    const game = (id, week, home_score, away_score, extra={}) => ({id, week, home_score, away_score,
        field_number:1, start_time:'12:00', home_team:home, away_team:away, status:'completed', ...extra});
    const games = [game(1, 1, 40, 27), game(2, 1, 20, 6), game(3, 2, 30, 20),
        game(4, 2, 120, 110, {is_friendly:true}), game(5, 3, null, null, {status:'scheduled'}),
        game(6, 2, 18, 6, {home_team:team(3, 'Femenil', 'femenil'), away_team:team(4, 'Femenil rival', 'femenil')})];
    const pageTemplate = fs.readFileSync('templates/games.html', 'utf8');
    const content = pageTemplate.split('{% block content %}')[1].split('{% endblock %}')[0]
        .replace(/{% for field_number in range\(1, 9\) %}[\s\S]*?{% endfor %}/g,
            Array.from({length:8}, (_, i) => `<option value="${i+1}">Campo ${i+1}</option>`).join(''));
    const scripts = pageTemplate.split('{% block scripts %}')[1].split('{% endblock %}')[0];
    const html = fs.readFileSync('templates/base.html', 'utf8')
        .replace('{% block content %}{% endblock %}', content)
        .replace('{% block scripts %}{% endblock %}', scripts);
    await page.route('https://featured.test/**', async route => {
        const path = new URL(route.request().url()).pathname;
        if (path.startsWith('/static/')) {
            const type = path.endsWith('.css') ? 'text/css' : path.endsWith('.jpeg') ? 'image/jpeg' : 'application/javascript';
            return route.fulfill({contentType:type, body:fs.readFileSync('.'+path)});
        }
        const json = body => route.fulfill({contentType:'application/json', body:JSON.stringify(body)});
        if (path === '/api/games') return json(games);
        if (path === '/api/teams') return json([home, away]);
        if (path === '/api/auth/me') return route.fulfill({status:401, contentType:'application/json', body:'{}'});
        if (path.startsWith('/api/')) return json([]);
        return route.fulfill({contentType:'text/html', body:html});
    });
    await page.goto('https://featured.test/games');
    const cards = page.locator('.featured-score-card');
    await page.locator('#games .game-card').first().waitFor();
    assert.equal(await page.locator('#weekly-featured').isVisible(), false);
    assert.equal(await cards.count(), 0);
    assert.equal(await page.locator('#games .game-card').count(), 1, 'upcoming list remains intact');
    await page.locator('#game-filter-week').selectOption('2');
    await cards.first().waitFor();
    assert.equal(await cards.count(), 1);
    assert.match(await cards.first().textContent(), /50 puntos combinados/);
    for (const width of [1546, 1024, 820, 600, 390, 320]) {
        await page.setViewportSize({width, height:1000});
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `no page overflow at ${width}`);
        assert.equal(await cards.first().evaluate(node => node.scrollWidth <= node.clientWidth), true, `no card overflow at ${width}`);
    }
    await page.locator('#game-filter-week').selectOption('1');
    assert.equal(await cards.count(), 1);
    assert.match(await cards.first().textContent(), /67 puntos combinados/);
    assert.equal(await cards.first().locator('a').getAttribute('href'), '/games/1');
    await page.locator('#game-filter-week').selectOption('2');
    await page.locator('#game-filter-week').selectOption('');
    assert.equal(await page.locator('#weekly-featured').isVisible(), false);
    assert.equal(await cards.count(), 0);
    await page.locator('#game-filter-week').selectOption('3');
    assert.equal(await page.locator('#weekly-featured').isVisible(), false, 'unplayed week has no final score to highlight');
    await page.locator('#game-filter-week').selectOption('2');
    await page.locator('#game-filter-branch').selectOption('femenil');
    assert.equal(await cards.count(), 1);
    assert.match(await cards.first().textContent(), /24 puntos combinados/);
    await page.locator('#game-filter-category').selectOption('u14');
    assert.equal(await page.locator('#weekly-featured').isVisible(), false);
    await page.locator('#game-filter-category').selectOption('libre');
    assert.equal(await page.locator('#weekly-featured').isVisible(), true);
    await page.locator('#game-filter-field').selectOption('8');
    assert.equal(await page.locator('#weekly-featured').isVisible(), false);
    assert.deepEqual(errors, []);
    await browser.close();
    console.log('Weekly featured scores: per-week selection, filters, detail links and desktop/mobile layout verified.');
})().catch(error => { console.error(error); process.exit(1); });
