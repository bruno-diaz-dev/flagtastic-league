// One game view; the API omits private sections the current role cannot read.

const gameDetailPage = document.querySelector(".game-detail-page");
const gameId = gameDetailPage.dataset.gameId;
const detailMessage = document.querySelector("#game-detail-message");
const officialSlots = document.querySelector("#game-official-slots");
const officialRefresh = document.querySelector("#game-official-refresh");
const officialMessage = document.querySelector("#game-official-message");
let assignedOfficials = [];
let officialSaving = false;
let officialLoading = false;
let officialNeedsRefresh = false;
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
            ${escapeHtml(official.display_name || official.name)}
        </span>
    `).join("") : "Sin oficiales asignados.";
}

async function loadOfficialOptions() {
    if (officialSaving || officialLoading) return;
    officialLoading = true;
    officialMessage.textContent = "Cargando planilla…";
    syncOfficialControls();
    try {
        const usersResponse = await getAdminUsers();
        // Referees can read the crew, but only administrators can edit it.
        if ([401, 403].includes(usersResponse.status)) {
            officialSlots.innerHTML = "";
            officialMessage.textContent = "";
            return;
        }
        if (!usersResponse.ok) throw new Error("users");
        const crewResponse = await getGameReferees(gameId);
        if (!crewResponse.ok) throw new Error("crew");
        const [users, crew] = await Promise.all([usersResponse.json(), crewResponse.json()]);
        const candidates = users.filter(user =>
            (user.roles || [user.role]).includes("referee") && user.status === "active"
        );
        crew.forEach(official => {
            if (!candidates.some(user => user.id === official.id)) candidates.push({...official, unavailable: true});
        });
        candidates.sort((a, b) => (a.display_name || a.name).localeCompare(b.display_name || b.name, "es"));
        assignedOfficials = crew;
        renderOfficials(crew);
        officialSlots.innerHTML = Object.entries(positionLabels).map(([position, label]) => {
            const selected = crew.find(official => official.position === position)?.id;
            return `<form class="schedule-board-official-slot" data-official-position="${position}">
                <label>${label}<select name="official_id" aria-label="${label} del partido">
                    <option value="">Sin asignar</option>${candidates.map(user => `<option value="${user.id}" ${user.id === selected ? "selected" : ""} ${user.unavailable && user.id !== selected ? "disabled" : ""}>${escapeHtml(user.display_name || user.name)}${user.unavailable ? " (no activo)" : ""}</option>`).join("")}
                </select></label>
                <button type="submit">Guardar ${label}</button>
                <p class="form-message" role="status"></p>
            </form>`;
        }).join("");
        officialNeedsRefresh = false;
        officialMessage.textContent = "Para retirar a alguien, selecciona Sin asignar y guarda ese puesto.";
    } catch (error) {
        officialNeedsRefresh = true;
        officialMessage.textContent = "No se pudo cargar la planilla. Pulsa Actualizar lista para reintentar.";
    } finally {
        officialLoading = false;
        syncOfficialControls();
    }
}

function syncOfficialControls() {
    officialSlots.querySelectorAll("select, button").forEach(control => {
        control.disabled = officialSaving || officialLoading || officialNeedsRefresh;
    });
    officialRefresh.disabled = officialSaving || officialLoading;
}

async function loadGameDetail() {
    const response = await getGameDetails(gameId);
    if (!response.ok) {
        detailMessage.textContent = "No se pudo cargar el partido.";
        return;
    }
    const detail = await response.json();
    const game = detail.game;
    document.querySelector("#game-detail-title").innerHTML = `
        <a class="team-roster-link" href="/teams/${game.home_team.id}/roster">${escapeHtml(game.home_team.name)}</a>
        <span class="matchup-versus">vs</span>
        <a class="team-roster-link" href="/teams/${game.away_team.id}/roster">${escapeHtml(game.away_team.name)}</a>
    `;
    document.querySelector("#game-detail-meta").textContent = ` ${game.is_friendly ? "Amistoso · " : ""}Jornada ${game.week} · ${game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar"} · ${game.field_number ? `Campo ${game.field_number}` : "Campo por asignar"}`;
    document.querySelector("#game-score").innerHTML = `
        ${game.is_friendly ? '<span class="game-friendly-badge">Amistoso · No cuenta para la temporada</span>' : ""}
        <div class="game-detail-score">
            <a class="team-roster-link" href="/teams/${game.home_team.id}/roster">${escapeHtml(game.home_team.name)}</a>
            <strong>${game.home_score ?? "-"} · ${game.away_score ?? "-"}</strong>
            <a class="team-roster-link" href="/teams/${game.away_team.id}/roster">${escapeHtml(game.away_team.name)}</a>
        </div>`;

    if (Object.hasOwn(detail, "my_statistics")) {
        document.querySelector("#my-game-statistics").classList.remove("hidden");
        document.querySelector("#my-game-stats-grid").innerHTML = statsGrid(detail.my_statistics);
    }
    if (detail.team_statistics) {
        document.querySelector("#team-game-statistics").classList.remove("hidden");
        document.querySelector("#team-game-stats-body").innerHTML = detail.team_statistics.map((row) => `
            <tr><td><a class="player-profile-link" href="/players/${row.player_id}?team_id=${row.team_id}">${escapeHtml(row.player_aka || row.player_name)}</a></td><td>${row.jersey_number}</td><td>${row.points}</td><td>${row.receptions}</td><td>${row.interceptions}</td><td>${row.sacks}</td><td>${row.tackles}</td><td>${row.passes_completed}</td><td>${row.passes_attempted}</td><td>${row.completion_percentage ?? "-"}</td></tr>
        `).join("") || `<tr><td colspan="10">Sin estadísticas registradas.</td></tr>`;
    }
    if (detail.officials) {
        document.querySelector("#game-officials").classList.remove("hidden");
        assignedOfficials = detail.officials;
        renderOfficials(detail.officials);
        await loadOfficialOptions();
    }
}

officialSlots.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (officialSaving || officialLoading || officialNeedsRefresh) return;
    const form = event.target;
    const position = form.dataset.officialPosition;
    if (!Object.hasOwn(positionLabels, position)) return;
    const nextId = Number(form.elements.official_id.value) || null;
    const previous = assignedOfficials.find(official => official.position === position);
    const message = form.querySelector(".form-message");
    if (nextId === (previous?.id || null)) {message.textContent = "Sin cambios."; return;}
    if (nextId && assignedOfficials.some(official => official.position !== position && official.id === nextId)) {
        message.textContent = "Esta persona ya tiene otro puesto en el partido.";
        return;
    }
    officialSaving = true;
    const button = form.querySelector("button");
    const label = button.textContent;
    button.textContent = "Guardando…";
    message.textContent = "Guardando asignación…";
    form.setAttribute("aria-busy", "true");
    syncOfficialControls();
    try {
        const response = nextId
            ? await assignGameReferee(gameId, nextId, position)
            : await removeGameReferee(gameId, previous.id);
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            message.textContent = typeof body.detail === "string" ? body.detail : "No se pudo guardar la asignación.";
            return;
        }
        assignedOfficials = assignedOfficials.filter(official => official.position !== position);
        if (nextId) assignedOfficials.push({id: nextId, position,
            display_name: form.elements.official_id.selectedOptions[0].textContent.replace(/ \(no activo\)$/, "")});
        renderOfficials(assignedOfficials);
        message.textContent = nextId ? "Asignación guardada." : "Puesto sin asignar.";
    } catch (error) {
        officialNeedsRefresh = true;
        message.textContent = "No se pudo confirmar el guardado. Pulsa Actualizar lista para comprobar la asignación.";
    } finally {
        officialSaving = false;
        button.textContent = label;
        form.removeAttribute("aria-busy");
        syncOfficialControls();
    }
});
officialRefresh.addEventListener("click", loadOfficialOptions);

loadGameDetail().catch(() => {
    detailMessage.textContent = "No se pudo conectar con el servidor.";
});
