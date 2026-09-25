// Private referee schedule. The API enforces referee-only access.

const refereeGames = document.querySelector("#referee-games");
const refereeGamesMessage = document.querySelector("#referee-games-message");
const scheduleForm = document.querySelector("#referee-schedule-form");
const scheduleMessage = document.querySelector("#schedule-import-message");
const scheduleReview = document.querySelector("#schedule-review");
const scheduleReviewBody = document.querySelector("#schedule-review-body");
const scheduleRawText = document.querySelector("#schedule-raw-text");
const confirmScheduleButton = document.querySelector("#confirm-schedule");

let availableReferees = [];
const officialPositions = [
    ["referee", "Referee", true],
    ["down_judge", "Down Judge", true],
    ["field_judge", "Field Judge", false],
    ["side_judge", "Side Judge", false],
    ["statistician", "Estadístico", false]
];


async function loadRefereeGames() {
    const response = await getMyRefereeGames();
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 403) return window.location.assign("/teams");
    if (!response.ok) {
        refereeGamesMessage.textContent = "No se pudieron cargar tus partidos.";
        return;
    }
    const games = await response.json();
    refereeGames.innerHTML = games.length ? games.map((game) => `
        <article class="game-card">
            <div>
                <h3>${escapeHtml(game.home_team.name)} vs ${escapeHtml(game.away_team.name)}</h3>
                <p>${escapeHtml(officialPositions.find(([value]) => value === game.official_position)?.[1] || game.official_position)} · Jornada ${game.week} · ${game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar"} · ${escapeHtml(game.home_team.branch)} / ${escapeHtml(game.home_team.category)} · ${game.field_number ? `Campo ${game.field_number}` : "Campo por asignar"}</p>
            </div>
            <strong>${game.home_score === null ? "Pendiente" : `${game.home_score} - ${game.away_score}`}</strong>
        </article>
    `).join("") : `
        <div class="empty-state">
            <h3>Sin partidos asignados</h3>
            <p>Tus próximas asignaciones aparecerán aquí.</p>
        </div>`;
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
loadRefereeGames().catch(() => {
    refereeGamesMessage.textContent = "No se pudo conectar con el servidor.";
});
