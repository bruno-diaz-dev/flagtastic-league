// Private representative dashboard; the API scopes every team by session user.
const representativeTeams = document.querySelector("#representative-teams");

function metric(label, value) {
    return `<div class="stat-item"><span>${label}</span><strong>${value ?? "-"}</strong></div>`;
}

function renderRepresentativeTeam(team) {
    const standing = team.standing;
    const staff = [team.head_coach, team.coach, team.manager].filter(Boolean);
    return `
        <section class="representative-team-panel">
            <header class="representative-team-header">
                ${team.logo_url ? `<img class="team-logo" src="${team.logo_url}" alt="Logo de ${escapeHtml(team.name)}">` : ""}
                <div><h3>${escapeHtml(team.name)}</h3><p>${escapeHtml(team.branch)} / ${escapeHtml(team.category)}</p></div>
                <a class="secondary-link" href="/teams/${team.id}/roster">Ver roster</a>
            </header>
            <p class="muted-text">${staff.length ? `Cuerpo técnico: ${staff.map(escapeHtml).join(" · ")}` : "Cuerpo técnico pendiente"}</p>
            <div class="stat-grid">
                ${metric("Posición", standing.position ? `${standing.position}/${standing.division_team_count}` : "-")}
                ${metric("Récord", `${standing.wins}-${standing.losses}`)}
                ${metric("PF / PC", `${standing.points_for} / ${standing.points_against}`)}
                ${metric("Jugadores", team.roster_count)}
                ${metric("Puntos", team.statistics.points)}
                ${metric("Recepciones", team.statistics.receptions)}
                ${metric("Tacleadas", team.statistics.tackles)}
                ${metric("% pases", team.statistics.completion_percentage)}
            </div>
            <div class="table-scroll"><table class="standings-data-table"><thead><tr>
                <th>Jugador</th><th>#</th><th>PTS</th><th>REC</th><th>INT</th><th>CAP</th><th>TAC</th><th>PC</th><th>PL</th><th>%</th>
            </tr></thead><tbody>${team.players.map((player) => `<tr>
                <td><a href="/players/${player.player_id}">${escapeHtml(player.player_aka || player.player_name)}</a></td>
                <td>${player.jersey_number}</td><td>${player.points}</td><td>${player.receptions}</td><td>${player.interceptions}</td>
                <td>${player.sacks}</td><td>${player.tackles}</td><td>${player.passes_completed}</td><td>${player.passes_attempted}</td>
                <td>${player.completion_percentage ?? "-"}</td>
            </tr>`).join("") || `<tr><td colspan="10">Sin jugadores registrados.</td></tr>`}</tbody></table></div>
        </section>`;
}

async function loadRepresentativeDashboard() {
    const response = await getMyRepresentativeDashboard();
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 403) {
        representativeTeams.innerHTML = `<div class="empty-state"><h3>Acceso restringido</h3><p>Necesitas el rol de representante.</p></div>`;
        return;
    }
    if (!response.ok) throw new Error("Dashboard request failed");
    const dashboard = await response.json();
    representativeTeams.innerHTML = dashboard.teams.length
        ? dashboard.teams.map(renderRepresentativeTeam).join("")
        : `<div class="empty-state"><h3>Sin equipos asignados</h3><p>Los equipos que registres aparecerán aquí.</p></div>`;
}

loadRepresentativeDashboard().catch(() => {
    representativeTeams.innerHTML = `<div class="empty-state"><h3>No se pudo cargar el dashboard</h3><p>Intenta recargar la página.</p></div>`;
});
