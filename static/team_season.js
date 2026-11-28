// Team season on the roster page: standing and record, the schedule with
// results, and the team's leader in each statistic. roster.js announces the
// loaded team with a "roster:loaded" event.

const teamSeason = document.querySelector("#team-season");
const teamSeasonStats = document.querySelector("#team-season-stats");
const teamSchedule = document.querySelector("#team-schedule");
const teamLeaders = document.querySelector("#team-leaders");

const TEAM_LEADER_DEFINITIONS = [
    ["points", "Máquina de Puntos", "Puntos"],
    ["receptions", "Manos de Acero", "Recepciones"],
    ["tackles", "El Muro", "Tacleadas"],
    ["interceptions", "Cazador Aéreo", "Intercepciones"],
    ["sacks", "Cazador de QBs", "Capturas"],
];
const WEEKDAY_SHORT = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const MONTH_SHORT = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

const seasonName = (name) => (typeof displayName === "function" ? displayName(name) : name);
const seasonInitials = (name) => (typeof nameInitials === "function" ? nameInitials(name) : String(name || "?").slice(0, 2));
const seasonEmpty = (options) => (typeof emptyStateMarkup === "function"
    ? emptyStateMarkup({heading: "h5", ...options})
    : `<div class="empty-state"><h5>${escapeHtml(options.title)}</h5></div>`);

function seasonShortDate(isoDate) {
    if (!isoDate) return "";
    const day = new Date(`${isoDate}T12:00:00`);
    return `${WEEKDAY_SHORT[day.getDay()]} ${day.getDate()} ${MONTH_SHORT[day.getMonth()]}`;
}

function seasonLogo(team) {
    return team?.logo_url
        ? `<img src="${escapeHtml(team.logo_url)}" alt="" loading="lazy" decoding="async">`
        : escapeHtml(seasonInitials(team?.name));
}

// One row per game, from this team's side: opponent, then the result or kickoff.
function seasonGameRow(game, teamId) {
    const isHome = game.home_team.id === teamId;
    const opponent = isHome ? game.away_team : game.home_team;
    const own = isHome ? game.home_score : game.away_score;
    const other = isHome ? game.away_score : game.home_score;
    const done = game.status === "completed" && Number.isInteger(own) && Number.isInteger(other);
    let outcome;
    if (done) {
        const result = own > other ? "win" : own < other ? "loss" : "tie";
        const letter = {win: "G", loss: "P", tie: "E"}[result];
        outcome = `<span class="team-result" data-result="${result}"><b>${letter}</b>${own}-${other}</span>`;
    } else if (game.status === "postponed") {
        outcome = '<span class="team-result" data-result="postponed">Pospuesto</span>';
    } else {
        const time = game.start_time ? game.start_time.slice(0, 5) : "Por asignar";
        outcome = `<span class="team-result" data-result="scheduled">${escapeHtml(time)}${game.field_number ? ` · C${game.field_number}` : ""}</span>`;
    }
    const when = [`J${game.week}`, seasonShortDate(game.game_date)].filter(Boolean).join(" · ");
    const opponentName = game.bracket_pending ? "Por definir" : seasonName(opponent.name);
    return `
        <li>
            <a class="team-game" href="/games/${game.id}">
                <span class="team-game-when">${escapeHtml(when)}${game.bracket_label ? `<small>${escapeHtml(game.bracket_label)}</small>` : ""}</span>
                <span class="team-game-opponent">
                    <span class="team-game-side">${isHome ? "vs" : "@"}</span>
                    <span class="home-game-logo" aria-hidden="true">${seasonLogo(opponent)}</span>
                    <span class="team-game-name">${escapeHtml(opponentName)}</span>
                </span>
                ${outcome}
            </a>
        </li>`;
}

function seasonLeaderCard(leader, [metric, title, statistic]) {
    if (!leader) return "";
    const shown = leader.player_aka || seasonName(leader.player_name);
    const photo = leader.profile_photo_url
        ? `<img src="${escapeHtml(leader.profile_photo_url)}" alt="" loading="lazy" decoding="async">`
        : escapeHtml(seasonInitials(leader.player_name));
    return `
        <a class="home-leader" href="/players/${leader.player_id}?team_id=${leader.team_id}" data-metric="${metric}">
            <span class="home-leader-photo" aria-hidden="true">${photo}</span>
            <span class="home-leader-copy">
                <small>${escapeHtml(title)}</small>
                <strong>${escapeHtml(shown)}</strong>
                <span>#${escapeHtml(leader.jersey_number ?? "—")}</span>
            </span>
            <span class="home-leader-value"><strong>${escapeHtml(leader.value)}</strong><small>${escapeHtml(statistic)}</small></span>
        </a>`;
}

function renderSeasonStats(team, standings, games) {
    const index = standings.findIndex((row) => row.team_id === team.id);
    const row = standings[index];
    const results = games
        .filter((game) => game.status === "completed" && Number.isInteger(game.home_score) && Number.isInteger(game.away_score))
        .sort((first, second) => second.week - first.week || second.id - first.id)
        .slice(0, 5)
        .reverse()
        .map((game) => {
            const own = game.home_team.id === team.id ? game.home_score : game.away_score;
            const other = game.home_team.id === team.id ? game.away_score : game.home_score;
            return own > other ? "G" : own < other ? "P" : "E";
        });
    const items = [];
    if (row) {
        items.push([`#${index + 1}`, `de ${standings.length} en la tabla`]);
        items.push([`${row.wins}-${row.losses}`, "Récord"]);
        items.push([row.points_for, "Puntos a favor"]);
        items.push([row.points_against, "Puntos en contra"]);
        items.push([`${row.point_difference > 0 ? "+" : ""}${row.point_difference}`, "Diferencia"]);
    }
    teamSeasonStats.innerHTML = items.map(([value, label]) => `<li><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></li>`).join("")
        + (results.length
            ? `<li class="team-streak"><span class="team-streak-chips">${results.map((result) => `<b data-result="${result}">${result}</b>`).join("")}</span><span>Últimos ${results.length}</span></li>`
            : "");
    teamSeasonStats.hidden = items.length === 0 && results.length === 0;
}

async function loadTeamSeason(team) {
    if (!teamSeason || !team?.id) return;
    teamSeason.hidden = false;
    if (typeof skeletonMarkup === "function") {
        teamSchedule.innerHTML = `<li>${skeletonMarkup("table", 4, "Cargando calendario")}</li>`;
        teamLeaders.innerHTML = skeletonMarkup("cards", 2, "Cargando líderes");
    }
    const category = team.category;
    const branch = isUnifiedYouthCategory(category) ? "mixto" : team.branch;
    const [gamesResult, standingsResult, leadersResult] = await Promise.allSettled([
        getGames().then((response) => (response.ok ? response.json() : Promise.reject(new Error("games")))),
        getStandings(branch, category).then((response) => (response.ok ? response.json() : [])),
        fetch(`/api/teams/${team.id}/leaders`).then((response) => (response.ok ? response.json() : {})),
    ]);
    const games = gamesResult.status === "fulfilled"
        ? gamesResult.value.filter((game) => game.home_team.id === team.id || game.away_team.id === team.id)
            .sort((first, second) => first.week - second.week || String(first.start_time).localeCompare(String(second.start_time)))
        : [];
    const standings = standingsResult.status === "fulfilled" ? standingsResult.value : [];
    renderSeasonStats(team, standings, games);

    teamSchedule.innerHTML = games.length
        ? games.map((game) => seasonGameRow(game, team.id)).join("")
        : `<li>${seasonEmpty({
            icon: "calendar",
            title: gamesResult.status === "fulfilled" ? "Sin partidos programados" : "No pudimos cargar el calendario",
            text: gamesResult.status === "fulfilled" ? "Sus partidos aparecerán aquí en cuanto se publique el calendario." : "Inténtalo de nuevo en un momento.",
        })}</li>`;

    const leaders = leadersResult.status === "fulfilled" ? leadersResult.value : {};
    const cards = TEAM_LEADER_DEFINITIONS.map((definition) => seasonLeaderCard(leaders[definition[0]]?.[0], definition)).join("");
    teamLeaders.innerHTML = cards || seasonEmpty({
        icon: "chart",
        title: "Sin estadísticas todavía",
        text: "Los líderes del equipo aparecerán cuando se publiquen sus cédulas.",
    });
}

document.addEventListener("roster:loaded", (event) => loadTeamSeason(event.detail));
