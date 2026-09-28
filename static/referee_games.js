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


function renderRefereeSummary(games) {
    const pendingGames = games.filter((game) => game.home_score === null);
    const completedGames = games.length - pendingGames.length;
    const nextWeek = pendingGames.length
        ? Math.min(...pendingGames.map((game) => game.week))
        : null;
    const positionCounts = games.reduce((counts, game) => {
        counts[game.official_position] = (counts[game.official_position] || 0) + 1;
        return counts;
    }, {});
    const mostFrequentPosition = Object.entries(positionCounts)
        .sort((left, right) => right[1] - left[1])[0]?.[0];

    refereeSummary.innerHTML = [
        refereeMetric("Asignaciones", games.length),
        refereeMetric("Pendientes", pendingGames.length),
        refereeMetric("Finalizadas", completedGames),
        refereeMetric("Siguiente jornada", nextWeek ? `J${nextWeek}` : "-"),
        refereeMetric("Rol más frecuente", mostFrequentPosition ? officialPositionLabel(mostFrequentPosition) : "-")
    ].join("");
}


function refereeGameCard(game) {
    const isPending = game.home_score === null;
    return `
        <article class="game-card referee-game-card">
            <div class="referee-game-copy">
                <span class="game-state ${isPending ? "game-state-pending" : "game-state-complete"}">${isPending ? "Pendiente" : "Finalizado"}</span>
                <h4>${escapeHtml(game.home_team.name)} vs ${escapeHtml(game.away_team.name)}</h4>
                <p>${escapeHtml(officialPositionLabel(game.official_position))} · Jornada ${game.week} · ${game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar"}</p>
                <p>${escapeHtml(game.home_team.branch)} / ${escapeHtml(game.home_team.category)} · ${game.field_number ? `Campo ${game.field_number}` : "Campo por asignar"}</p>
            </div>
            <div class="referee-game-result">
                <strong>${isPending ? "Por jugar" : `${game.home_score} - ${game.away_score}`}</strong>
                <a class="secondary-link" href="/games/${game.id}">Ver detalle</a>
            </div>
        </article>`;
}


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


async function loadRefereeGames() {
    const response = await getMyRefereeGames();
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 403) return window.location.assign("/teams");
    if (!response.ok) {
        refereeGamesMessage.textContent = "No se pudieron cargar tus partidos.";
        return;
    }
    const games = await response.json();
    const pendingGames = games.filter((game) => game.home_score === null);
    const completedGames = games.filter((game) => game.home_score !== null);
    renderRefereeSummary(games);
    refereeGames.innerHTML = games.length
        ? refereeGameSection(
            "Asignaciones pendientes",
            "Partidos que todavía no tienen marcador final.",
            pendingGames
        ) + refereeGameSection(
            "Historial de arbitrajes",
            "Partidos finalizados en los que participaste.",
            completedGames
        )
        : `<div class="empty-state"><h3>Sin partidos asignados</h3><p>Tus próximas asignaciones aparecerán aquí.</p></div>`;
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
    scheduleRawText.textContent = result.raw_text;
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
    scheduleMessage.textContent = result.proposals.length
        ? `${result.proposals.length} partido(s) reconocido(s). Revisa antes de confirmar.`
        : "Se leyó la imagen, pero ningún partido coincidió. Revisa el texto reconocido.";
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
    scheduleMessage.textContent = "Analizando imagen...";
    scheduleReview.classList.add("hidden");
    const response = await analyzeRefereeSchedule(file);
    const body = await response.json();
    if (!response.ok) {
        scheduleMessage.textContent = body.detail || "No se pudo analizar la imagen.";
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
