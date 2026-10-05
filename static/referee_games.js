// Private referee schedule. The API enforces referee-only access.

const refereeGames = document.querySelector("#referee-games");
const refereeGamesMessage = document.querySelector("#referee-games-message");
const refereeSummary = document.querySelector("#referee-summary");
const scheduleForm = document.querySelector("#referee-schedule-form");
const scheduleMessage = document.querySelector("#schedule-import-message");
const scheduleReview = document.querySelector("#schedule-review");
const scheduleReviewBody = document.querySelector("#schedule-review-body");
const scheduleRawText = document.querySelector("#schedule-raw-text");
const confirmScheduleButton = document.querySelector("#confirm-schedule");
const dashboardPhotoPanel = document.querySelector("#referee-dashboard-photo-panel");
const dashboardPhotoForm = document.querySelector("#referee-dashboard-photo-form");
const dashboardPhotoMessage = document.querySelector("#referee-dashboard-photo-message");

let availableReferees = [];
const officialPositions = [
    ["referee", "Referee", true],
    ["down_judge", "Down Judge", true],
    ["field_judge", "Field Judge", false],
    ["side_judge", "Side Judge", false],
    ["statistician", "Estadístico", false]
];


function officialPositionLabel(position) {
    return officialPositions.find(([value]) => value === position)?.[1] || position;
}


function refereeMetric(label, value) {
    return `<div class="stat-item"><span>${label}</span><strong>${escapeHtml(String(value))}</strong></div>`;
}


function refereeGameState(game) {
    if (game.status === "postponed") return "postponed";
    if (game.status === "completed" || (game.home_score != null && game.away_score != null)) return "completed";
    return "pending";
}


function renderRefereeSummary(games) {
    const pending = games.filter(game => refereeGameState(game) === "pending");
    const completed = games.filter(game => refereeGameState(game) === "completed");
    const postponed = games.filter(game => refereeGameState(game) === "postponed");
    const nextWeek = pending.length ? Math.min(...pending.map(game => game.week)) : null;
    refereeSummary.innerHTML = [
        refereeMetric("Por arbitrar", pending.length),
        refereeMetric("Pospuestos", postponed.length),
        refereeMetric("Arbitrajes finalizados", completed.length),
        refereeMetric("Próxima jornada", nextWeek === null ? "-" : `J${nextWeek}`)
    ].join("");
}


function refereeGameCard(game) {
    const state = refereeGameState(game);
    const isPending = state === "pending";
    const isPostponed = state === "postponed";
    return `
        <article class="game-card referee-game-card">
            <div class="referee-game-copy">
                <span class="game-state ${isPostponed ? "game-state-postponed" : isPending ? "game-state-pending" : "game-state-complete"}">${isPostponed ? "Pospuesto" : isPending ? "Pendiente" : "Finalizado"}</span>
                <h4>
                    <a class="team-roster-link" href="/teams/${game.home_team.id}/roster">${escapeHtml(game.home_team.name)}</a>
                    <span class="matchup-versus">vs</span>
                    <a class="team-roster-link" href="/teams/${game.away_team.id}/roster">${escapeHtml(game.away_team.name)}</a>
                </h4>
                <p>${escapeHtml(officialPositionLabel(game.official_position))} · Jornada ${game.week} · ${game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar"}</p>
                <p>${escapeHtml(divisionBranchLabel(game.home_team.branch, game.home_team.category))} / ${escapeHtml(game.home_team.category)} · ${game.field_number ? `Campo ${game.field_number}` : "Campo por asignar"}</p>
                <div class="game-crew" aria-label="Planilla arbitral del partido">
                    <strong>Planilla arbitral</strong>
                    <ul>
                        ${(game.officials || []).length ? game.officials.map((official) => `
                            <li>
                                <span>${escapeHtml(officialPositionLabel(official.position))}</span>
                                <b>${escapeHtml(official.display_name)}</b>
                            </li>`).join("") : "<li><span>Sin asignaciones adicionales</span></li>"}
                    </ul>
                </div>
            </div>
            <div class="referee-game-result">
                <strong>${isPostponed ? "Por reprogramar" : isPending ? "Por jugar" : `${game.home_score} - ${game.away_score}`}</strong>
                <a class="secondary-link" href="/games/${game.id}">${isPending ? "Captura en vivo" : "Ver detalle"}</a>
            </div>
            ${isPending && game.home_score == null && game.away_score == null ? `
            <details class="referee-score-panel">
                <summary>Registrar resultado</summary>
                <form class="score-form referee-score-form" data-game-id="${game.id}">
                    <div class="score-fields">
                        <label><span>${escapeHtml(game.home_team.name)}</span><input type="number" name="home_score" min="0" step="1" inputmode="numeric" required aria-label="Puntos de ${escapeHtml(game.home_team.name)}"></label>
                        <span class="score-separator" aria-hidden="true">-</span>
                        <label><span>${escapeHtml(game.away_team.name)}</span><input type="number" name="away_score" min="0" step="1" inputmode="numeric" required aria-label="Puntos de ${escapeHtml(game.away_team.name)}"></label>
                    </div>
                    <p class="score-capture-help">Verifica los puntos antes de guardar. Solo un administrador podrá corregir el resultado.</p>
                    <button type="submit">Guardar resultado final</button>
                    <p class="score-form-message form-message" role="status"></p>
                </form>
            </details>` : ""}
        </article>`;
}


refereeGames.addEventListener("submit", async (event) => {
    if (!event.target.classList.contains("referee-score-form")) return;
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const message = form.querySelector(".score-form-message");
    if (button.disabled) return;
    const values = new FormData(form);
    button.disabled = true;
    message.textContent = "Guardando resultado...";
    try {
        const response = await updateGamesScore(form.dataset.gameId, {
            home_score: Number(values.get("home_score")),
            away_score: Number(values.get("away_score"))
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            message.textContent = body.detail || "No se pudo registrar el resultado.";
            button.disabled = false;
            return;
        }
        refereeGamesMessage.textContent = "Resultado registrado. El partido está ahora en tu historial.";
        await loadRefereeGames();
    } catch (error) {
        message.textContent = "No se pudo conectar. Comprueba el estado del partido antes de reintentar.";
        button.disabled = false;
    }
});


function refereeGameSection(title, description, games) {
    return `
        <section class="referee-game-section">
            <header class="dashboard-section-heading">
                <div><h3>${title}</h3><p>${description}</p></div>
                <strong>${games.length}</strong>
            </header>
            <div class="games-list">
                ${games.length
                    ? games.map(refereeGameCard).join("")
                    : `<div class="empty-state"><h4>Sin partidos</h4><p>No hay asignaciones en esta sección.</p></div>`}
            </div>
        </section>`;
}


function renderRefereeHistory(games) {
    const weeks = [...new Set(games.map(game => game.week))].sort((a, b) => b - a);
    const positions = officialPositions.map(([position, label]) => ({
        label, count: games.filter(game => game.official_position === position).length
    }));
    const maximum = Math.max(1, ...positions.map(position => position.count));
    return `
        <section class="referee-history-panel" aria-labelledby="referee-history-title">
            <header class="dashboard-section-heading">
                <div>
                    <p class="eyebrow">Historial de arbitrajes</p>
                    <h3 id="referee-history-title">Mi experiencia arbitral</h3>
                    <p>Solo partidos finalizados. Tus asignaciones pendientes aparecen arriba.</p>
                </div>
            </header>
            <div class="referee-history-metrics">
                ${refereeMetric("Partidos arbitrados", games.length)}
                ${refereeMetric("Jornadas arbitradas", weeks.length)}
            </div>
            ${games.length ? `
                <h4>Participación por puesto</h4>
                <ul class="referee-position-bars">
                    ${positions.filter(position => position.count > 0).map(position => `
                        <li>
                            <div><span>${position.label}</span><strong>${position.count} ${position.count === 1 ? "partido" : "partidos"}</strong></div>
                            <div class="referee-position-track" aria-hidden="true"><span style="width: ${position.count / maximum * 100}%"></span></div>
                        </li>`).join("")}
                </ul>
                <h4>Consultar partidos por jornada</h4>
                <div class="referee-history-weeks">
                    ${weeks.map(week => {
                        const weekGames = games.filter(game => game.week === week);
                        return `
                            <details class="referee-history-week">
                                <summary>Jornada ${week} · ${weekGames.length} ${weekGames.length === 1 ? "arbitraje" : "arbitrajes"}</summary>
                                <ul class="referee-history-list">
                                    ${weekGames.map(game => `
                                        <li>
                                            <div>
                                                <a class="team-roster-link" href="/teams/${game.home_team.id}/roster">${escapeHtml(game.home_team.name)}</a>
                                                <span class="matchup-versus">vs</span>
                                                <a class="team-roster-link" href="/teams/${game.away_team.id}/roster">${escapeHtml(game.away_team.name)}</a>
                                                <p>${escapeHtml(officialPositionLabel(game.official_position))} · ${game.start_time ? game.start_time.slice(0, 5) : "Hora sin registrar"} · ${game.field_number ? `Campo ${game.field_number}` : "Campo sin registrar"}</p>
                                            </div>
                                            <div class="referee-history-result">
                                                <strong>${game.home_score != null && game.away_score != null ? `${game.home_score} - ${game.away_score}` : "Finalizado"}</strong>
                                                <a class="secondary-link" href="/games/${game.id}">Ver detalle</a>
                                            </div>
                                        </li>`).join("")}
                                </ul>
                            </details>`;
                    }).join("")}
                </div>` : `<p class="form-hint">Tu experiencia aparecerá cuando finalicen los partidos que tienes asignados.</p>`}
        </section>`;
}


async function loadRefereeGames() {
    const response = await getMyRefereeGames();
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 403) return window.location.assign("/teams");
    if (!response.ok) {
        refereeGamesMessage.textContent = "No se pudieron cargar tus partidos.";
        return;
    }
    const games = await response.json();
    const pendingGames = games.filter(game => refereeGameState(game) === "pending")
        .sort((a, b) => a.week - b.week || (a.start_time || "99:99").localeCompare(b.start_time || "99:99"));
    const completedGames = games.filter(game => refereeGameState(game) === "completed");
    const postponedGames = games.filter(game => refereeGameState(game) === "postponed");
    renderRefereeSummary(games);
    refereeGames.innerHTML = refereeGameSection(
        "Próximas asignaciones",
        "Estos son tus partidos por arbitrar. Revisa horario, campo y puesto.",
        pendingGames
    ) + (postponedGames.length ? `
        <details class="referee-postponed-panel">
            <summary>Asignaciones pospuestas · ${postponedGames.length}</summary>
            ${refereeGameSection("Por reprogramar", "Espera la confirmación de un nuevo horario.", postponedGames)}
        </details>` : "") + renderRefereeHistory(completedGames);
}


function officialSelects(selectedOfficials) {
    const selectedByPosition = new Map(
        selectedOfficials.map((official) => [official.position, official.user_id])
    );
    return officialPositions.map(([position, label, required]) => `
        <label class="schedule-official-slot">
            ${label}${required ? " *" : ""}
            <select data-position="${position}" ${required ? "required" : ""}>
                <option value="">Sin asignar</option>
                ${availableReferees.map((referee) => `
                    <option value="${referee.id}" ${selectedByPosition.get(position) === referee.id ? "selected" : ""}>
                        ${escapeHtml(referee.display_name || referee.name)}
                    </option>`).join("")}
            </select>
        </label>
    `).join("");
}


function renderScheduleReview(result) {
    scheduleRawText.textContent = result.raw_text || "";
    scheduleReviewBody.innerHTML = result.proposals.map((proposal) => `
        <tr data-game-id="${proposal.game_id}" data-scheduled-time="${proposal.scheduled_time || ""}">
            <td>
                <strong>${escapeHtml(proposal.game_label)}</strong>
                <small>${escapeHtml(proposal.source_text)}</small>
            </td>
            <td>
                <select name="field_number">
                    ${Array.from({length: 8}, (_, index) => index + 1).map((number) =>
                        `<option value="${number}" ${number === proposal.field_number ? "selected" : ""}>Campo ${number}</option>`
                    ).join("")}
                </select>
            </td>
            <td><div class="schedule-referees">${officialSelects(proposal.officials || [])}</div></td>
        </tr>
    `).join("");
    scheduleReview.classList.remove("hidden");
    confirmScheduleButton.disabled = result.proposals.length === 0;
    const warnings = result.warnings || [];
    const warningCopy = warnings.length
        ? ` ${warnings.length} advertencia(s): ${warnings.join(" ")}`
        : "";
    scheduleMessage.textContent = result.proposals.length
        ? `${result.proposals.length} partido(s) reconocido(s). Revisa antes de confirmar.${warningCopy}`
        : `Se leyó el archivo, pero ningún partido coincidió. Revisa el contenido reconocido.${warningCopy}`;
}


async function loadAvailableReferees() {
    const response = await getAdminUsers();
    if (!response.ok) return;
    const users = await response.json();
    availableReferees = users.filter((user) =>
        (user.roles || [user.role]).includes("referee") && user.status === "active"
    );
}


async function requestMissingRefereePhoto() {
    const response = await getMyRefereeProfile();
    if (!response.ok) return;
    const profile = await response.json();
    dashboardPhotoPanel.classList.toggle("hidden", Boolean(profile.profile_photo_url));
}


dashboardPhotoForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = new FormData(dashboardPhotoForm).get("file");
    dashboardPhotoMessage.textContent = "Guardando foto...";
    const response = await uploadMyRefereePhoto(file);
    dashboardPhotoMessage.textContent = response.ok
        ? "Foto arbitral actualizada correctamente."
        : ((await response.json()).detail || "No se pudo guardar la foto.");
    if (response.ok) dashboardPhotoPanel.classList.add("hidden");
});


scheduleForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = new FormData(scheduleForm).get("file");
    scheduleMessage.textContent = "Analizando archivo...";
    scheduleReview.classList.add("hidden");
    const response = await analyzeRefereeSchedule(file);
    const body = await response.json();
    if (!response.ok) {
        scheduleMessage.textContent = body.detail || "No se pudo analizar el archivo.";
        return;
    }
    renderScheduleReview(body);
});


confirmScheduleButton?.addEventListener("click", async () => {
    const assignments = [...scheduleReviewBody.querySelectorAll("tr")].map((row) => ({
        game_id: Number(row.dataset.gameId),
        field_number: Number(row.querySelector("[name='field_number']").value),
        scheduled_time: row.dataset.scheduledTime || null,
        officials: [...row.querySelectorAll("[data-position]")]
            .filter((select) => select.value)
            .map((select) => ({
                user_id: Number(select.value),
                position: select.dataset.position
            }))
    }));
    const response = await confirmRefereeSchedule(assignments);
    const body = await response.json();
    scheduleMessage.textContent = response.ok
        ? `${body.updated} partido(s) actualizado(s).`
        : (body.detail || "No se pudieron guardar las asignaciones.");
    if (response.ok) {
        scheduleReview.classList.add("hidden");
        await loadRefereeGames();
    }
});


loadAvailableReferees();
requestMissingRefereePhoto();
loadRefereeGames().catch(() => {
    refereeSummary.innerHTML = "";
    refereeGamesMessage.textContent = "No se pudo conectar con el servidor.";
});
