// One game view; the API omits private sections the current role cannot read.

const gameDetailPage = document.querySelector(".game-detail-page");
const gameId = gameDetailPage.dataset.gameId;
const detailMessage = document.querySelector("#game-detail-message");
const officialForm = document.querySelector("#game-official-form");
const officialMessage = document.querySelector("#game-official-message");
const labels = {
    points: "Puntos", receptions: "Recepciones", interceptions: "Intercepciones",
    sacks: "Capturas", tackles: "Tacleadas", passes_completed: "Pases completos",
    passes_attempted: "Pases lanzados", completion_percentage: "% completos"
};
const positionLabels = {
    referee: "Referee", down_judge: "Down Judge", field_judge: "Field Judge",
    side_judge: "Side Judge", statistician: "Estadístico"
};

function statsGrid(stats) {
    if (!stats) return `<div class="empty-state"><p>Sin estadísticas registradas para este partido.</p></div>`;
    return Object.entries(labels).map(([key, label]) =>
        `<article class="stat-item"><span>${label}</span><strong>${stats[key] ?? "-"}</strong></article>`
    ).join("");
}

function renderOfficials(officials) {
    const list = document.querySelector("#game-officials-list");
    list.innerHTML = officials.length ? officials.map((official) => `
        <span class="assigned-referee">
            <strong>${positionLabels[official.position]}</strong> ·
            ${escapeHtml(official.display_name)}
            <button class="admin-only" type="button" data-remove-official="${official.id}" aria-label="Quitar a ${escapeHtml(official.display_name)}">×</button>
        </span>
    `).join("") : "Sin oficiales asignados.";
}

async function loadOfficialOptions() {
    const response = await getAdminUsers();
    if (!response.ok) return;
    const users = await response.json();
    const officials = users.filter((user) =>
        (user.roles || [user.role]).includes("referee") && user.status === "active"
    );
    officialForm.elements.user_id.innerHTML = officials.map((user) =>
        `<option value="${user.id}">${escapeHtml(user.display_name || user.name)}</option>`
    ).join("");
}

async function loadGameDetail() {
    const response = await getGameDetails(gameId);
    if (!response.ok) {
        detailMessage.textContent = "No se pudo cargar el partido.";
        return;
    }
    const detail = await response.json();
    const game = detail.game;
    document.querySelector("#game-detail-title").textContent = `${game.home_team.name} vs ${game.away_team.name}`;
    document.querySelector("#game-detail-meta").textContent = `Jornada ${game.week} · ${game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar"} · ${game.field_number ? `Campo ${game.field_number}` : "Campo por asignar"}`;
    document.querySelector("#game-score").innerHTML = `<div class="game-detail-score"><span>${escapeHtml(game.home_team.name)}</span><strong>${game.home_score ?? "-"} · ${game.away_score ?? "-"}</strong><span>${escapeHtml(game.away_team.name)}</span></div>`;

    if (Object.hasOwn(detail, "my_statistics")) {
        document.querySelector("#my-game-statistics").classList.remove("hidden");
        document.querySelector("#my-game-stats-grid").innerHTML = statsGrid(detail.my_statistics);
    }
    if (detail.team_statistics) {
        document.querySelector("#team-game-statistics").classList.remove("hidden");
        document.querySelector("#team-game-stats-body").innerHTML = detail.team_statistics.map((row) => `
            <tr><td>${escapeHtml(row.player_aka || row.player_name)}</td><td>${row.jersey_number}</td><td>${row.points}</td><td>${row.receptions}</td><td>${row.interceptions}</td><td>${row.sacks}</td><td>${row.tackles}</td><td>${row.passes_completed}</td><td>${row.passes_attempted}</td><td>${row.completion_percentage ?? "-"}</td></tr>
        `).join("") || `<tr><td colspan="10">Sin estadísticas registradas.</td></tr>`;
    }
    if (detail.officials) {
        document.querySelector("#game-officials").classList.remove("hidden");
        renderOfficials(detail.officials);
        await loadOfficialOptions();
    }
}

officialForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    officialMessage.textContent = "Guardando cambio...";
    const response = await assignGameReferee(
        gameId,
        officialForm.elements.user_id.value,
        officialForm.elements.position.value
    );
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        officialMessage.textContent = error.detail || "No se pudo guardar la asignación.";
        return;
    }
    officialMessage.textContent = "Asignación actualizada.";
    const officialsResponse = await getGameReferees(gameId);
    if (officialsResponse.ok) renderOfficials(await officialsResponse.json());
});

document.querySelector("#game-officials-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-remove-official]");
    if (!button) return;
    const response = await removeGameReferee(gameId, button.dataset.removeOfficial);
    if (!response.ok) {
        officialMessage.textContent = "No se pudo retirar al oficial.";
        return;
    }
    officialMessage.textContent = "Oficial retirado del partido.";
    const officialsResponse = await getGameReferees(gameId);
    if (officialsResponse.ok) renderOfficials(await officialsResponse.json());
});

loadGameDetail().catch(() => {
    detailMessage.textContent = "No se pudo conectar con el servidor.";
});
