// League home: the next week to play, the latest results with the week's
// featured score, and the standings and number-one players of a division.

const homeHero = document.querySelector("#home-hero");
const homeNext = document.querySelector("#home-next");
const homeNextTitle = document.querySelector("#home-next-title");
const homeNextLink = document.querySelector("#home-next-link");
const homeResults = document.querySelector("#home-results");
const homeResultsTitle = document.querySelector("#home-results-title");
const homeDivisionForm = document.querySelector("#home-division-form");
const homeBranch = document.querySelector("#home-branch");
const homeBranchField = document.querySelector("#home-branch-field");
const homeCategory = document.querySelector("#home-category");
const homeStandings = document.querySelector("#home-standings");
const homeLeaders = document.querySelector("#home-leaders");

const HOME_NEXT_LIMIT = 6;
const HOME_RESULTS_LIMIT = 6;
const HOME_LEADER_METRICS = [
    ["points", "Máquina de Puntos", "Puntos"],
    ["receptions", "Manos de Acero", "Recepciones"],
    ["tackles", "El Muro", "Tacleadas"],
    ["interceptions", "Cazador Aéreo", "Intercepciones"],
    ["sacks", "Cazador de QBs", "Capturas"],
];

const homeName = (name) => (typeof displayName === "function" ? displayName(name) : name);
const homeInitials = (name) => (typeof nameInitials === "function" ? nameInitials(name) : String(name || "?").slice(0, 2));
const homeSkeleton = (shape, count, label) => (typeof skeletonMarkup === "function" ? skeletonMarkup(shape, count, label) : `<p>${label}…</p>`);
const homeEmpty = (options) => (typeof emptyStateMarkup === "function"
    ? emptyStateMarkup(options)
    : `<div class="empty-state"><h3>${escapeHtml(options.title)}</h3><p>${escapeHtml(options.text || "")}</p></div>`);

function homeDaysUntil(isoDate) {
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    return Math.round((new Date(`${isoDate}T12:00:00`) - today) / 86400000);
}

function homeLongDate(isoDate) {
    const label = new Date(`${isoDate}T12:00:00`).toLocaleDateString("es-MX", {weekday: "long", day: "numeric", month: "long"});
    return label.charAt(0).toUpperCase() + label.slice(1);
}

function homeMostCommon(values) {
    const counts = new Map();
    values.filter(Boolean).forEach((value) => counts.set(value, (counts.get(value) || 0) + 1));
    return [...counts].sort((first, second) => second[1] - first[1])[0]?.[0] || null;
}

function homeDivision(team) {
    if (!team?.category) return "";
    return `${divisionBranchLabel(homeName(team.branch || ""), team.category)} · ${team.category.toUpperCase()}`;
}

function homeGameOrder(first, second) {
    return String(first.start_time || "99").localeCompare(String(second.start_time || "99"))
        || (first.field_number || 99) - (second.field_number || 99)
        || first.id - second.id;
}

function homeTeamLogo(team) {
    return team.logo_url
        ? `<img src="${escapeHtml(team.logo_url)}" alt="" loading="lazy" decoding="async">`
        : escapeHtml(homeInitials(team.name));
}

// One compact scoreboard card per game.
function homeGameCard(game) {
    const done = game.status === "completed" && Number.isInteger(game.home_score) && Number.isInteger(game.away_score);
    const side = (team, score, other) => `
        <span class="home-game-team${done && score > other ? " is-winner" : ""}">
            <span class="home-game-logo" aria-hidden="true">${homeTeamLogo(team)}</span>
            <span class="home-game-name">${escapeHtml(homeName(team.name))}</span>
            ${done ? `<strong class="home-game-score">${score}</strong>` : ""}
        </span>`;
    const meta = [
        done ? "Final" : game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar",
        game.field_number ? `Campo ${game.field_number}` : "",
    ].filter(Boolean).join(" · ");
    const label = game.bracket_label || homeDivision(game.home_team);
    const pending = game.bracket_pending;
    return `
        <a class="home-game" href="/games/${game.id}" data-status="${escapeHtml(game.status)}">
            <span class="home-game-meta"><span>${escapeHtml(meta)}</span><span>${escapeHtml(label)}</span></span>
            ${pending
                ? `<span class="home-game-pending">${escapeHtml(game.bracket_label || "Final")} · Por definir</span>`
                : `${side(game.home_team, game.home_score, game.away_score)}${side(game.away_team, game.away_score, game.home_score)}`}
            ${game.status === "postponed" ? '<span class="home-game-flag">Pospuesto</span>' : ""}
        </a>`;
}

function renderHomeHero(nextWeek, weekGames, latestWeek) {
    if (!homeHero) return;
    if (nextWeek == null) {
        setPageHero({tags: latestWeek ? [{label: `Jornada ${latestWeek} finalizada`, tone: "gold"}] : []});
        return;
    }
    const date = homeMostCommon(weekGames.map((game) => game.game_date));
    const venue = homeMostCommon(weekGames.map((game) => game.venue));
    const days = date ? homeDaysUntil(date) : null;
    const when = days === 0 ? "Hoy" : days === 1 ? "Mañana" : days > 1 ? `En ${days} días` : "Por jugar";
    const finals = weekGames.some((game) => game.bracket_label);
    const fields = new Set(weekGames.map((game) => game.field_number).filter(Boolean)).size;
    const divisions = new Set(weekGames.map((game) => homeDivision(game.home_team)).filter(Boolean)).size;
    setPageHero({
        tags: [
            {label: when, tone: days === 0 ? "live" : "gold"},
            ...(finals ? [{label: "Día de finales", tone: "gold"}] : []),
        ],
        stats: [[weekGames.length, "Partidos"], [fields, "Campos"], [divisions, "Divisiones"]],
    });
    document.querySelector("#home-hero-title").textContent = `Jornada ${nextWeek}`;
    document.querySelector("#home-hero-subtitle").textContent = `${date ? homeLongDate(date) : "Fecha por confirmar"} · ${venue || "Sede por confirmar"}`;
    homeHero.dataset.week = String(nextWeek);
}

function renderHomeNext(nextWeek, weekGames) {
    if (nextWeek == null) {
        homeNextTitle.textContent = "Próxima jornada";
        homeNext.innerHTML = homeEmpty({
            icon: "calendar",
            title: "El calendario está en pausa",
            text: "La próxima jornada aparecerá aquí en cuanto se programe. Mientras, repasa cómo va la tabla.",
            action: {label: "Ver la tabla", href: "/standings"},
        });
        return;
    }
    const pending = weekGames.filter((game) => game.status === "scheduled").sort(homeGameOrder);
    homeNextTitle.textContent = `Jornada ${nextWeek} · por jugar`;
    homeNext.innerHTML = pending.slice(0, HOME_NEXT_LIMIT).map(homeGameCard).join("");
    homeNextLink.textContent = pending.length > HOME_NEXT_LIMIT ? `Ver los ${pending.length} partidos` : "Ver calendario";
}

function renderHomeResults(latestWeek, games) {
    if (latestWeek == null) {
        homeResults.innerHTML = homeEmpty({
            icon: "trophy",
            title: "Todavía no hay marcadores",
            text: "Los resultados aparecerán aquí al terminar los primeros partidos de la temporada.",
            action: {label: "Ver calendario", href: "/games"},
        });
        return;
    }
    const played = games.filter((game) => game.week === latestWeek && game.status === "completed");
    const featured = typeof selectWeeklyFeaturedGames === "function" ? selectWeeklyFeaturedGames(played)[0] : null;
    const others = played.filter((game) => game !== featured)
        .sort((first, second) => homeGameOrder(second, first))
        .slice(0, HOME_RESULTS_LIMIT);
    homeResultsTitle.textContent = `Jornada ${latestWeek} · resultados`;
    const spotlight = featured ? `
        <a class="home-featured" href="/games/${featured.id}">
            <span class="home-featured-kicker">Marcador destacado · ${featured.home_score + featured.away_score} puntos</span>
            <span class="home-featured-division">${escapeHtml(homeDivision(featured.home_team))}</span>
            <span class="home-featured-match">
                ${[[featured.home_team, featured.home_score, featured.away_score], [featured.away_team, featured.away_score, featured.home_score]].map(([team, score, other]) => `
                    <span class="home-featured-team${score > other ? " is-winner" : ""}">
                        <span class="home-game-logo" aria-hidden="true">${homeTeamLogo(team)}</span>
                        <span class="home-featured-name">${escapeHtml(homeName(team.name))}</span>
                        <strong>${score}</strong>
                    </span>`).join("")}
            </span>
            <span class="home-featured-cta">Ver partido</span>
        </a>` : "";
    homeResults.innerHTML = `${spotlight}<div class="home-game-grid">${others.map(homeGameCard).join("")}</div>`;
}

async function loadHomeGames() {
    homeNext.innerHTML = homeSkeleton("games", 3, "Cargando la jornada");
    homeResults.innerHTML = homeSkeleton("games", 3, "Cargando resultados");
    try {
        const response = await getGames();
        if (!response.ok) throw new Error("Request failed");
        const games = (await response.json()).filter((game) => !game.is_friendly);
        // The phone top bar names the page "Inicio" while the band names the week.
        const pageLabel = document.querySelector("#current-page-label");
        if (pageLabel) pageLabel.textContent = "Inicio";
        const pendingWeeks = games.filter((game) => game.status === "scheduled").map((game) => game.week);
        const nextWeek = pendingWeeks.length ? Math.min(...pendingWeeks) : null;
        const playedWeeks = games.filter((game) => game.status === "completed").map((game) => game.week);
        const latestWeek = playedWeeks.length ? Math.max(...playedWeeks) : null;
        const weekGames = nextWeek == null ? [] : games.filter((game) => game.week === nextWeek);
        renderHomeHero(nextWeek, weekGames, latestWeek);
        renderHomeNext(nextWeek, weekGames);
        renderHomeResults(latestWeek, games);
    } catch (error) {
        const failure = homeEmpty({
            icon: "alert",
            title: "No pudimos traer los partidos",
            text: "Revisa tu conexión e inténtalo de nuevo.",
            action: {label: "Reintentar", id: "home-games-retry"},
        });
        homeNext.innerHTML = failure;
        homeResults.innerHTML = "";
        document.querySelector("#home-games-retry")?.addEventListener("click", loadHomeGames);
    }
}

function homeLeaderCard(leader, [metric, title, statistic]) {
    if (!leader) return "";
    const shown = leader.player_aka || homeName(leader.player_name);
    const photo = leader.profile_photo_url
        ? `<img src="${escapeHtml(leader.profile_photo_url)}" alt="" loading="lazy" decoding="async">`
        : escapeHtml(homeInitials(leader.player_name));
    return `
        <a class="home-leader" href="/players/${leader.player_id}?team_id=${leader.team_id}" data-metric="${metric}">
            <span class="home-leader-photo" aria-hidden="true">${photo}</span>
            <span class="home-leader-copy">
                <small>${escapeHtml(title)}</small>
                <strong>${escapeHtml(shown)}</strong>
                <span>#${escapeHtml(leader.jersey_number ?? "—")} · ${escapeHtml(homeName(leader.team_name))}</span>
            </span>
            <span class="home-leader-value"><strong>${escapeHtml(leader.value)}</strong><small>${escapeHtml(statistic)}</small></span>
        </a>`;
}

function homeStandingsTable(standings) {
    if (!standings.length) {
        return homeEmpty({
            icon: "trophy",
            heading: "h5",
            title: "Sin marcadores todavía",
            text: "La tabla se arma con los partidos jugados de esta división.",
            action: {label: "Ver calendario", href: "/games"},
        });
    }
    return `<ol class="home-standings">${standings.slice(0, 5).map((team, index) => `
        <li>
            <span class="home-standings-rank">${index + 1}</span>
            <span class="home-game-logo" aria-hidden="true">${team.team_logo_url ? `<img src="${escapeHtml(team.team_logo_url)}" alt="" loading="lazy" decoding="async">` : escapeHtml(homeInitials(team.team_name))}</span>
            <a href="/teams/${team.team_id}/roster">${escapeHtml(homeName(team.team_name))}</a>
            <span class="home-standings-record">${team.wins}-${team.losses}</span>
            <span class="home-standings-diff">${team.point_difference > 0 ? "+" : ""}${team.point_difference}</span>
        </li>`).join("")}</ol>`;
}

let homeDivisionRequest = 0;

async function loadHomeDivision() {
    const request = ++homeDivisionRequest;
    const category = homeCategory.value;
    const unified = isUnifiedYouthCategory(category);
    homeBranchField.classList.toggle("hidden", unified);
    const branch = unified ? "mixto" : homeBranch.value;
    homeStandings.innerHTML = homeSkeleton("table", 5, "Cargando la tabla");
    homeLeaders.innerHTML = homeSkeleton("cards", 3, "Cargando líderes");
    try {
        const [standingsResponse, leadersResponse] = await Promise.all([
            getStandings(branch, category),
            getLeaderboards(branch, category),
        ]);
        if (!standingsResponse.ok || !leadersResponse.ok) throw new Error("Request failed");
        const [standings, leaderboards] = await Promise.all([standingsResponse.json(), leadersResponse.json()]);
        if (request !== homeDivisionRequest) return;
        homeStandings.innerHTML = homeStandingsTable(standings);
        const cards = HOME_LEADER_METRICS.map((definition) => homeLeaderCard(leaderboards[definition[0]]?.[0], definition)).join("");
        homeLeaders.innerHTML = cards || homeEmpty({
            icon: "chart",
            heading: "h5",
            title: "Sin estadísticas cargadas",
            text: "Los líderes de la división aparecerán cuando se publiquen las cédulas.",
            action: {label: "Ver estadísticas", href: "/statistics"},
        });
    } catch (error) {
        if (request !== homeDivisionRequest) return;
        homeStandings.innerHTML = homeEmpty({icon: "alert", heading: "h5", title: "No pudimos cargar la tabla", text: "Inténtalo de nuevo en un momento."});
        homeLeaders.innerHTML = "";
    }
}

if (homeNext && homeResults) {
    loadHomeGames();
}
if (homeDivisionForm) {
    homeDivisionForm.addEventListener("submit", (event) => event.preventDefault());
    homeBranch.addEventListener("change", loadHomeDivision);
    homeCategory.addEventListener("change", loadHomeDivision);
    loadHomeDivision();
}
