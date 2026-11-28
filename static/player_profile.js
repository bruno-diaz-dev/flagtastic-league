// Read-only season profile shared by roster, leaderboard and admin links.

const publicProfilePage = document.querySelector("#public-player-profile");
const publicPlayerId = publicProfilePage.dataset.playerId;
const publicStats = document.querySelector("#public-player-stats");
const publicTeams = document.querySelector("#public-player-teams");
const publicMessage = document.querySelector("#public-player-message");

document.querySelector("#public-profile-back").addEventListener("click", () => {
    if (window.history.length > 1) window.history.back();
    else window.location.assign("/teams");
});

const publicStatisticLabels = {
    points: "Puntos",
    receptions: "Recepciones",
    tackles: "Tacleadas",
    interceptions: "Intercepciones",
    sacks: "Capturas",
    passes_completed: "Pases completos",
    passes_attempted: "Pases lanzados",
    completion_percentage: "% de pases completos",
    weeks: "Jornadas con estadísticas"
};

const WEEKLY_COLUMNS = [
    ["points", "PTS", "Puntos"],
    ["receptions", "REC", "Recepciones"],
    ["tackles", "TAC", "Tacleadas"],
    ["interceptions", "INT", "Intercepciones"],
    ["sacks", "CAP", "Capturas"],
];

// The card shows the jersey and team of the membership on screen.
function renderPlayerCardTeam(team) {
    const jersey = document.querySelector("#player-card-jersey");
    const teamLine = document.querySelector("#player-card-team");
    if (!team) {
        jersey.hidden = true;
        teamLine.textContent = "";
        return;
    }
    jersey.hidden = team.jersey_number == null;
    jersey.textContent = team.jersey_number == null ? "" : `#${team.jersey_number}`;
    const division = `${displayName(divisionBranchLabel(team.branch, team.category))} · ${displayName(team.category)}`;
    const standing = team.standing_position ? ` · ${team.standing_position}° de ${team.division_team_count}` : "";
    teamLine.textContent = `${displayName(team.team_name)} · ${division}${standing}`;
}

// Week by week for the same membership, each row with a bar for its points.
function renderWeekly(team) {
    const container = document.querySelector("#public-player-weekly");
    const weeks = team?.weekly || [];
    if (!weeks.length) {
        container.innerHTML = typeof emptyStateMarkup === "function"
            ? emptyStateMarkup({icon: "chart", heading: "h4", title: "Sin jornadas registradas", text: "Sus números aparecerán aquí cuando se publique la cédula de cada jornada."})
            : `<div class="empty-state"><h4>Sin jornadas registradas</h4></div>`;
        return;
    }
    const best = Math.max(1, ...weeks.map((week) => week.points));
    container.innerHTML = `
        <div class="player-weekly-row player-weekly-head" aria-hidden="true">
            <span>Jornada</span>${WEEKLY_COLUMNS.map(([, short]) => `<span>${short}</span>`).join("")}<span>Pases</span>
        </div>
        ${weeks.map((week) => `
        <div class="player-weekly-row" style="--share:${Math.round((week.points / best) * 100)}%">
            <span class="player-weekly-week">J${week.week}</span>
            ${WEEKLY_COLUMNS.map(([key, short, label]) => `<span class="player-weekly-cell${key === "points" ? " is-points" : ""}" data-label="${short}" aria-label="${label}: ${week[key]}">${week[key]}</span>`).join("")}
            <span class="player-weekly-cell" data-label="Pases" aria-label="Pases completos de lanzados: ${week.passes_completed} de ${week.passes_attempted}">${week.passes_completed}/${week.passes_attempted}</span>
        </div>`).join("")}`;
}


function profileInitials(name) {
    return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}


function renderPublicProfile(profile) {
    const shownName = profile.player.aka || displayName(profile.player.name);
    document.querySelector("#public-player-name").textContent = shownName;
    document.querySelector("#public-player-identity").textContent = profile.player.aka
        ? `${profile.player.name} · ${profile.player.age} años`
        : `${profile.player.age} años`;

    const photo = document.querySelector("#public-player-photo");
    const placeholder = document.querySelector("#public-player-photo-placeholder");
    if (profile.player.profile_photo_url) {
        photo.src = profile.player.profile_photo_url;
        photo.alt = `Foto de ${shownName}`;
        photo.classList.remove("hidden");
        placeholder.classList.add("hidden");
    } else {
        placeholder.textContent = profileInitials(profile.player.name);
    }

    renderScopedPlayerStatistics(profile, {
        select: document.querySelector("#public-player-stats-team"), container: publicStats,
        context: document.querySelector("#public-player-stats-context"), labels: publicStatisticLabels,
        teamId: new URLSearchParams(window.location.search).get("team_id"),
        onSelect: teamId => {
            const url = new URL(window.location.href);
            url.searchParams.set("team_id", teamId);
            window.history.replaceState(null, "", url);
            const team = profile.teams.find((candidate) => String(candidate.team_id) === String(teamId));
            renderPlayerCardTeam(team);
            renderWeekly(team);
        }
    });

    if (!profile.teams.length) {
        renderPlayerCardTeam(null);
        renderWeekly(null);
    }

    publicTeams.innerHTML = profile.teams.length
        ? profile.teams.map((team) => `
            <article class="team-card">
                <div><h4><a class="team-roster-link" href="/teams/${team.team_id}/roster">${escapeHtml(displayName(team.team_name))}</a></h4>
                <p>${escapeHtml(displayName(divisionBranchLabel(team.branch, team.category)))} · ${escapeHtml(displayName(team.category))} · #${team.jersey_number}</p></div>
                <strong>${team.standing_position || "-"} / ${team.division_team_count}</strong>
            </article>`).join("")
        : `<div class="empty-state"><h4>Sin equipo registrado</h4><p>Este jugador todavía no aparece en un roster.</p></div>`;
}


async function loadPublicProfile() {
    const response = await getPublicPlayerProfile(publicPlayerId, new URLSearchParams(window.location.search).get("team_id"));
    if (response.status === 404) {
        publicMessage.textContent = "Jugador no encontrado.";
        return;
    }
    if (!response.ok) throw new Error("Player profile request failed");
    renderPublicProfile(await response.json());
}


loadPublicProfile().catch(() => {
    publicMessage.textContent = "No se pudo cargar el perfil del jugador.";
});
