// Profiles show one category/team at a time; there is no combined total option.
function renderScopedPlayerStatistics(profile, {select, container, context, labels, teamId, onSelect}) {
    const teams = profile.teams;
    const selected = teams.find(team => String(team.team_id) === String(teamId))
        || teams.find(team => team.team_id === profile.selected_team_id) || teams[0];
    select.innerHTML = teams.map(team => `<option value="${team.team_id}">${escapeHtml(`${team.category.toUpperCase()} · ${divisionBranchLabel(team.branch, team.category)} · ${team.team_name}${team.jersey_number == null ? '' : ` · #${team.jersey_number}`}${team.active === false ? ' · Histórico' : ''}`)}</option>`).join("");
    select.disabled = teams.length === 0;
    if (selected) select.value = String(selected.team_id);
    function update() {
        const team = teams.find(candidate => String(candidate.team_id) === select.value);
        const statistics = team ? team.statistics : profile.statistics;
        container.innerHTML = Object.entries(labels).map(([key, label]) => {
            const value = statistics?.[key] ?? "-";
            return `<article class="stat-item"><span>${label}</span><strong>${value}</strong></article>`;
        }).join("");
        context.textContent = team
            ? `${team.category.toUpperCase()} · ${divisionBranchLabel(team.branch, team.category)} · ${team.team_name}. Solo estadísticas de este equipo; las jornadas se cuentan una vez por semana.`
            : "Sin equipo registrado. No hay estadísticas de temporada.";
        if (team && onSelect) onSelect(team.team_id);
    }
    select.onchange = update;
    update();
}
