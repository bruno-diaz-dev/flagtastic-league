// One featured final score per week, calculated from the current calendar filters.
function selectWeeklyFeaturedGames(games) {
    const weeks = new Map();
    const total = game => game.home_score + game.away_score;
    const margin = game => Math.abs(game.home_score - game.away_score);
    for (const game of games) {
        if (game.is_friendly || game.status !== "completed"
            || !Number.isInteger(game.home_score) || !Number.isInteger(game.away_score)
            || game.home_score < 0 || game.away_score < 0) continue;
        const current = weeks.get(game.week);
        if (!current || total(game) > total(current)
            || (total(game) === total(current) && margin(game) < margin(current))
            || (total(game) === total(current) && margin(game) === margin(current) && game.id < current.id)) {
            weeks.set(game.week, game);
        }
    }
    return [...weeks.values()].sort((a, b) => b.week - a.week);
}

function renderWeeklyFeaturedGames(games) {
    const section = document.querySelector("#weekly-featured");
    const list = document.querySelector("#weekly-featured-list");
    if (!section || !list) return;
    const featured = selectWeeklyFeaturedGames(games);
    section.hidden = featured.length === 0;
    list.innerHTML = featured.map(game => {
        const team = (side, score, opponentScore) => `
            <div class="featured-score-team ${score > opponentScore ? "is-winner" : ""}">
                <strong>${escapeHtml(side.name)}</strong>
                <span class="featured-score-number">${score}</span>
            </div>`;
        return `
            <article class="featured-score-card" aria-labelledby="featured-score-title-${game.week}">
                <header class="featured-score-header">
                    <span class="featured-score-kicker"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M13 3c1 5 5 6 5 11a6 6 0 0 1-12 0c0-3 2-5 4-7 0 3 1 4 2 4 2-2 1-5 1-8Z"/></svg>Marcador destacado</span>
                    <span class="featured-score-week" id="featured-score-title-${game.week}">Jornada ${game.week}</span>
                </header>
                <p class="featured-score-division">${escapeHtml(divisionBranchLabel(game.home_team.branch, game.home_team.category))} · ${escapeHtml(game.home_team.category.toUpperCase())}</p>
                <div class="featured-score-match" aria-label="${escapeHtml(game.home_team.name)} ${game.home_score}, ${escapeHtml(game.away_team.name)} ${game.away_score}">
                    ${team(game.home_team, game.home_score, game.away_score)}
                    ${team(game.away_team, game.away_score, game.home_score)}
                </div>
                <footer class="featured-score-footer">
                    <span><strong>${game.home_score + game.away_score}</strong> puntos combinados</span>
                    <a href="/games/${game.id}" aria-label="Ver partido destacado de la jornada ${game.week}">Ver partido <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M7 17 17 7M7 7h10v10"/></svg></a>
                </footer>
            </article>`;
    }).join("");
}
