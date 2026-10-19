// Games page controller: scheduling, score capture, and game list rendering.

const gameForm = document.querySelector("#game-form");
const gameFormMessage = document.querySelector("#game-form-message");
const gamesContainer = document.querySelector("#games");

const homeTeamSelect = document.querySelector("[name='home_team_id']");
const awayTeamSelect = document.querySelector("[name='away_team_id']");
const manualGameBranch = document.querySelector("#manual-game-branch");
const manualGameCategory = document.querySelector("#manual-game-category");
const manualGameBranchField = document.querySelector("#manual-game-branch-field");
const manualGameYouthBranch = document.querySelector("#manual-game-youth-branch");
const manualHomeTeamSearch = document.querySelector("#manual-home-team-search");
const manualAwayTeamSearch = document.querySelector("#manual-away-team-search");
const gameFilterStatus = document.querySelector("#game-filter-status");
const gameFilterWeek = document.querySelector("#game-filter-week");
const gameFilterTeam = document.querySelector("#game-filter-team");
const gameFilterBranch = document.querySelector("#game-filter-branch");
const gameFilterCategory = document.querySelector("#game-filter-category");
const gameFilterBranchField = document.querySelector("#game-filter-branch-field");
const gameFilterYouthBranch = document.querySelector("#game-filter-youth-branch");
const gameFilterField = document.querySelector("#game-filter-field");
const gamesCount = document.querySelector("#games-count");
const gameScheduleUpdateMessage = document.querySelector("#game-schedule-update-message");
const refereeAssignmentForm = document.querySelector("#referee-assignment-form");
const refereeAssignmentMessage = document.querySelector("#referee-assignment-message");
const assignedReferees = document.querySelector("#assigned-referees");
const scheduleImportForm = document.querySelector("#game-schedule-import-form");
const scheduleImportMessage = document.querySelector("#game-schedule-import-message");
const scheduleReview = document.querySelector("#game-schedule-review");
const scheduleReviewHead = document.querySelector("#game-schedule-review-head");
const scheduleReviewBody = document.querySelector("#game-schedule-review-body");
const confirmScheduleButton = document.querySelector("#confirm-game-schedule");
const scheduleConfirmMessage = document.querySelector("#game-schedule-confirm-message");
const scheduleSaveProgress = document.querySelector("#game-schedule-save-progress");
const deleteGamesWeekButton = document.querySelector("#delete-games-week");
const toggleGamesWeekStatusButton = document.querySelector("#toggle-games-week-status");
const weekActionMessage = document.querySelector("#week-action-message");

let gamesState = [];
let gameTeamsState = [];
let scheduleImportState = null;
const officialPositionLabels = {
    referee: "Referee",
    down_judge: "Down Judge",
    field_judge: "Field Judge",
    side_judge: "Side Judge",
    statistician: "Estadístico"
};


function gameLabel(game) {
    return `${game.is_friendly ? "Amistoso · " : ""}J${game.week}: ${game.home_team.name} vs ${game.away_team.name}`;
}

function gameTime(game) {
    return game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar";
}

function normalizeSearchText(value) {
    return String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase("es-MX")
        .trim();
}

function compareGames(first, second) {
    return (
        first.week - second.week
        || gameTime(first).localeCompare(gameTime(second), "es-MX")
        || (first.field_number || 99) - (second.field_number || 99)
        || first.home_team.name.localeCompare(second.home_team.name, "es-MX")
    );
}

function gameTeamRow(team, side, score) {
    const logo = team.logo_url
        ? `<img class="team-logo game-team-logo" src="${team.logo_url}" alt="" loading="lazy" decoding="async">`
        : `<span class="game-team-logo game-team-logo-placeholder" aria-hidden="true">${escapeHtml(team.name.slice(0, 1))}</span>`;

    return `
        <div class="game-team-row">
            <span class="game-team-side">${side}</span>
            ${logo}
            <a class="game-team-name team-roster-link" href="/teams/${team.id}/roster">
                ${escapeHtml(team.name)}
            </a>
            <span class="game-team-score" aria-label="Puntos: ${score ?? "sin marcador"}">${score ?? "-"}</span>
        </div>
    `;
}


async function renderAssignedReferees() {
    const gameId = refereeAssignmentForm.elements.game_id.value;
    if (!gameId) {
        assignedReferees.innerHTML = "";
        return;
    }
    const response = await getGameReferees(gameId);
    if (!response.ok) return;
    const referees = await response.json();
    assignedReferees.innerHTML = referees.length
        ? referees.map((referee) => `
            <span class="assigned-referee">
                <strong>${officialPositionLabels[referee.position]}</strong> ·
                ${escapeHtml(referee.display_name)}
                <button type="button" data-remove-referee="${referee.id}" aria-label="Quitar a ${escapeHtml(referee.display_name)}">×</button>
            </span>`).join("")
        : "Sin árbitros asignados.";
}


async function loadRefereeAssignmentOptions() {
    const response = await getAdminUsers();
    if (!response.ok) return;
    const users = await response.json();
    const referees = users.filter((user) => (user.roles || [user.role]).includes("referee"));
    refereeAssignmentForm.elements.referee_id.innerHTML = referees.map((user) =>
        `<option value="${user.id}">${escapeHtml(user.display_name || user.name)}</option>`
    ).join("");
}


function compareTeams(first, second) {
    return (
        first.branch.localeCompare(second.branch, "es-MX")
        || first.category.localeCompare(second.category, "es-MX", {numeric: true})
        || first.name.localeCompare(second.name, "es-MX")
    );
}

function updateManualGameBranchControl() {
    const unified = isUnifiedYouthCategory(manualGameCategory.value);
    manualGameBranchField.classList.toggle("hidden", unified);
    manualGameYouthBranch.classList.toggle("hidden", !unified);
    if (unified) manualGameBranch.value = "";
}

function updateGameFilterBranchControl() {
    const unified = isUnifiedYouthCategory(gameFilterCategory.value);
    gameFilterBranchField.classList.toggle("hidden", unified);
    gameFilterYouthBranch.classList.toggle("hidden", !unified);
    if (unified) gameFilterBranch.value = "";
}

function renderManualTeamSelect(select, searchInput) {
    const selectedTeamId = select.value;
    const friendly = document.querySelector("#manual-game-type")?.value === "true";
    const search = normalizeSearchText(searchInput.value);
    const category = manualGameCategory.value;
    const unifiedYouthCategory = ["u8", "u10", "u12"].includes(category);
    const teams = gameTeamsState
        .filter((team) => (
            (
                !manualGameBranch.value
                || unifiedYouthCategory
                || team.branch === manualGameBranch.value
            )
            && (!category || team.category === category)
            && (!search || search.split(/\s+/).every((term) => normalizeSearchText(`${team.name} ${team.branch} ${team.category} ${team.branch.slice(0, 1)}${team.category.replace(/^u/, "")}`).includes(term)))
        ))
        .sort(compareTeams);
    const placeholder = teams.length
        ? "Selecciona un equipo"
        : friendly ? "Selecciona un equipo o agrega un invitado" : "No hay equipos con estos filtros";

    select.innerHTML = `
        <option value="">${placeholder}</option>
        ${friendly ? '<option value="guest">Equipo invitado (escribir nombre)</option>' : ""}
        ${teams.map((team) => `
            <option value="${team.id}">
                ${escapeHtml(team.name)} · ${escapeHtml(divisionBranchLabel(team.branch, team.category))} / ${escapeHtml(team.category)}
            </option>
        `).join("")}
    `;
    select.disabled = teams.length === 0 && !friendly;
    if (friendly && search && teams.length === 0) {
        select.value = "guest";
        const side = select === homeTeamSelect ? "home" : "away";
        const guest = gameForm.elements[side + "_guest_name"];
        if (guest && (!guest.value.trim() || guest.value === guest.dataset.searchName)) {
            guest.value = searchInput.value.trim();
            guest.dataset.searchName = guest.value;
        }
    } else if ((friendly && selectedTeamId === "guest") || teams.some((team) => String(team.id) === selectedTeamId)) {
        select.value = selectedTeamId;
    }
}

function renderManualTeamOptions() {
    renderManualTeamSelect(homeTeamSelect, manualHomeTeamSearch);
    renderManualTeamSelect(awayTeamSelect, manualAwayTeamSearch);
    updateGuestFields();
}

function updateGuestFields() {
    for (const side of ["home", "away"]) {
        const select = gameForm.elements[side + "_team_id"];
        const guest = gameForm.elements[side + "_guest_name"];
        if (!guest) continue;
        const active = document.querySelector("#manual-game-type")?.value === "true" && select.value === "guest";
        document.querySelector("#" + side + "-guest-field").classList.toggle("hidden", !active);
        guest.disabled = !active;
        guest.required = active;
    }
}
document.querySelector("#manual-game-type")?.addEventListener("change", renderManualTeamOptions);
homeTeamSelect.addEventListener("change", updateGuestFields);
awayTeamSelect.addEventListener("change", updateGuestFields);

function renderGames(games) {
    gamesCount.textContent = `${games.length} partido${games.length === 1 ? "" : "s"}`;

    if (games.length === 0) {
        gamesContainer.innerHTML = `
            <div class="empty-state">
                <h3>Sin partidos con estos filtros</h3>
                <p>Selecciona Estado: Pospuestos para encontrar y restablecer un partido, o elige una jornada para ver su historial.</p>
            </div>
        `;
        return;
    }

    const groups = new Map();
    [...games].sort(compareGames).forEach((game) => {
        const key = `${game.week}|${gameTime(game)}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(game);
    });

    gamesContainer.innerHTML = [...groups.values()]
        .map((groupGames) => {
            const firstGame = groupGames[0];
            return `
                <section class="game-time-group" aria-labelledby="game-group-${firstGame.week}-${firstGame.id}">
                    <header class="game-time-heading">
                        <h3 id="game-group-${firstGame.week}-${firstGame.id}">Jornada ${firstGame.week}</h3>
                        <time>${gameTime(firstGame)}</time>
                    </header>
                    <div class="game-time-grid">
                        ${groupGames.map((game) => {
            const hasScore = game.status === "completed" || game.home_score != null || game.away_score != null;
            const isPostponed = game.status === "postponed";
            const status = hasScore
                ? `<span class="game-status game-status-completed">Finalizado</span>`
                : isPostponed
                    ? `<span class="game-status game-status-postponed">Pospuesto</span>`
                    : `<span class="game-status game-status-scheduled">Programado</span>`;
            const scoreEditor = !isPostponed
                ? `
                        <form class="score-form ${hasScore ? "admin-only" : "scorekeeper-only"}" data-game-id="${game.id}">
                            <div class="score-fields">
                                <label>
                                    <span>Local</span>
                                    <input type="number" name="home_score" min="0" inputmode="numeric" value="${game.home_score ?? ""}" aria-label="Puntos de ${escapeHtml(game.home_team.name)}" required>
                                </label>
                                <span class="score-separator" aria-hidden="true">-</span>
                                <label>
                                    <span>Visitante</span>
                                    <input type="number" name="away_score" min="0" inputmode="numeric" value="${game.away_score ?? ""}" aria-label="Puntos de ${escapeHtml(game.away_team.name)}" required>
                                </label>
                            </div>
                            ${!hasScore ? '<p class="score-capture-help">Verifica los puntos antes de guardar. Solo un administrador podrá corregir el resultado.</p>' : ""}
                            <button type="submit">${hasScore ? "Actualizar marcador" : "Guardar resultado final"}</button>
                            <p class="score-form-message form-message" role="status"></p>
                        </form>`
                : "";

            return `
                <article class="game-card ${game.is_friendly ? "game-card-friendly" : ""}">
                    <header class="game-card-header">
                        <span class="game-field">${game.field_number ? `Campo ${game.field_number}` : "Campo por asignar"}</span>
                        ${status}
                        ${game.is_friendly ? '<span class="game-friendly-badge">Amistoso</span>' : ""}
                    </header>
                    <div class="game-teams">
                        ${gameTeamRow(game.home_team, "Local", game.home_score)}
                        ${gameTeamRow(game.away_team, "Visitante", game.away_score)}
                    </div>
                    <footer class="game-card-footer">
                        <span>${escapeHtml(divisionBranchLabel(game.home_team.branch, game.home_team.category))} · ${escapeHtml(game.home_team.category)}</span>
                        <a class="secondary-link game-details-link" href="/games/${game.id}">Ver partido / En vivo</a>
                    </footer>
                    <details class="game-admin-panel ${!hasScore && !isPostponed ? "scorekeeper-only" : "admin-only"}">
                        <summary>${!hasScore && !isPostponed ? "Resultado y horario" : "Administrar partido"}</summary>
                        <div class="game-admin-controls">
                            ${scoreEditor}
                            ${!hasScore ? `
                            <form class="game-time-form admin-only" data-game-id="${game.id}">
                                <label>Horario del partido
                                    <input type="time" name="start_time" value="${escapeHtml(game.start_time?.slice(0, 5) || "")}" aria-label="Nuevo horario del partido ${game.id}" required>
                                </label>
                                <label>Campo<select name="field_number" aria-label="Nuevo campo del partido ${game.id}">${Array.from({length: 8}, (_, i) => `<option value="${i + 1}" ${i + 1 === game.field_number ? "selected" : ""}>Campo ${i + 1}</option>`).join("")}</select></label>
                                <button type="submit">Guardar horario y campo</button>
                                <p class="game-time-message form-message" role="status"></p>
                            </form>
                            ` : ""}
                            ${!hasScore ? `
                            <button
                                class="secondary-button admin-only game-status-button"
                                type="button"
                                data-game-status="${game.id}"
                                data-next-status="${isPostponed ? "scheduled" : "postponed"}"
                            >${isPostponed ? "Restablecer partido" : "Posponer"}</button>
                            <p class="game-status-message form-message" role="status"></p>
                        ` : ""}
                            <button class="danger-button admin-only" type="button" data-delete-game="${game.id}">
                            Eliminar
                            </button>
                        </div>
                    </details>
                </article>
            `;
                        }).join("")}
                    </div>
                </section>
            `;
        })
        .join("");
}

function populateWeekFilter(games) {
    const selectedWeek = gameFilterWeek.value;
    const weeks = [...new Set(games.map((game) => game.week))]
        .sort((first, second) => first - second);

    gameFilterWeek.innerHTML = `
        <option value="">Próximos partidos</option>
        ${weeks.map((week) => `<option value="${week}">Jornada ${week}</option>`).join("")}
    `;
    gameFilterWeek.value = selectedWeek;
}

function renderFilteredGames() {
    const selectedWeek = gameFilterWeek.value;
    deleteGamesWeekButton.disabled = selectedWeek === "";
    toggleGamesWeekStatusButton.disabled = selectedWeek === "";
    const selectedWeekGames = gamesState.filter(
        (game) => String(game.week) === selectedWeek && game.status !== "completed"
    );
    const selectedWeekIsPostponed = (
        selectedWeekGames.length > 0
        && selectedWeekGames.every((game) => game.status === "postponed")
    );
    toggleGamesWeekStatusButton.dataset.nextStatus = (
        selectedWeekIsPostponed ? "scheduled" : "postponed"
    );
    toggleGamesWeekStatusButton.textContent = (
        selectedWeekIsPostponed ? "Restaurar jornada" : "Posponer jornada"
    );
    const featuredCandidates = [];
    const filteredGames = gamesState.filter((game) => {
        const teamSearch = normalizeSearchText(gameFilterTeam.value);
        const matchesTeam = (
            teamSearch === ""
            || normalizeSearchText(game.home_team.name).includes(teamSearch)
            || normalizeSearchText(game.away_team.name).includes(teamSearch)
        );
        const matchesWeek = (
            gameFilterWeek.value === ""
            || String(game.week) === gameFilterWeek.value
        );
        const matchesBranch = (
            isUnifiedYouthCategory(gameFilterCategory.value)
            || gameFilterBranch.value === ""
            || game.home_team.branch === gameFilterBranch.value
        );
        const matchesCategory = (
            gameFilterCategory.value === ""
            || game.home_team.category === gameFilterCategory.value
        );
        const matchesField = (
            gameFilterField.value === ""
            || String(game.field_number) === gameFilterField.value
        );
        const hasScore = game.home_score != null && game.away_score != null;
        const matchesStatus = gameFilterStatus.value
            ? gameFilterStatus.value === "all" || game.status === gameFilterStatus.value
            : (
            selectedWeek !== ""
            || normalizeSearchText(gameFilterTeam.value) !== ""
            || (game.status !== "completed" && game.status !== "postponed" && !hasScore)
        );
        const matchesContext = matchesTeam && matchesWeek && matchesBranch && matchesCategory && matchesField;
        if (matchesContext) featuredCandidates.push(game);
        return matchesStatus && matchesContext;
    });

    if (typeof renderWeeklyFeaturedGames === "function") renderWeeklyFeaturedGames(featuredCandidates);
    renderGames(filteredGames);
    if (typeof renderScheduleBoard === "function") renderScheduleBoard();
}

async function loadGamesTeams() {
    try {
        const response = await getTeams();

        if (!response.ok) {
            gameFormMessage.textContent = "No se pudieron cargar los equipos";
            return;
        }

        gameTeamsState = await response.json();
        renderManualTeamOptions();
    } catch (error) {
        gameFormMessage.textContent = "No se pudo conectar al servidor";
    }
}

async function loadGames() {
    gamesContainer.innerHTML = `
        <div class="empty-state">
            <h3>Cargando partidos</h3>
            <p>Espera un momento.</p>
        </div>
    `;

    try {
        const response = await getGames();

        if (!response.ok) {
            gamesContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No se pudieron cargar los partidos</h3>
                    <p>Intenta recargar la página.</p>
                </div>
            `;
            return;
        }

        gamesState = await response.json();
        refereeAssignmentForm.elements.game_id.innerHTML = gamesState.map((game) =>
            `<option value="${game.id}">${escapeHtml(gameLabel(game))}</option>`
        ).join("");
        populateWeekFilter(gamesState);
        renderFilteredGames();
        await renderAssignedReferees();
    } catch (error) {
        gamesContainer.innerHTML = `
            <div class="empty-state">
                <h3>No se pudieron cargar los partidos</h3>
                <p>Revisa que el servidor esté encendido.</p>
            </div>
        `;
    }
}

async function registerGame(event) {
    event.preventDefault();

    const formData = new FormData(gameForm);

    const payload = {
        home_team_id: formData.get("home_team_id") === "guest" ? null : Number(formData.get("home_team_id")),
        away_team_id: formData.get("away_team_id") === "guest" ? null : Number(formData.get("away_team_id")),
        is_friendly: formData.get("is_friendly") === "true",
        home_guest_name: formData.get("home_guest_name") || null,
        away_guest_name: formData.get("away_guest_name") || null,
        branch: isUnifiedYouthCategory(manualGameCategory.value) ? "mixto" : (manualGameBranch.value || null),
        category: manualGameCategory.value || null,
        week: Number(formData.get("week")),
        field_number: Number(formData.get("field_number")),
        start_time: formData.get("start_time") || null
    };

    gameFormMessage.textContent = "Registrando partido...";

    try {
        const response = await createGame(payload);

        if (response.status === 409) {
            const body = await response.json();
            gameFormMessage.textContent = body.detail || "Revisa los participantes del partido.";
            return;
        }

        if (response.status === 404) {
            gameFormMessage.textContent = "No se encontro a alguno de los equipos.";
            return;
        }

        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            gameFormMessage.textContent = typeof body.detail === "string" ? body.detail : "Revisa los equipos, rama y categoría del partido.";
            return;
        }

        gameForm.reset();
        renderManualTeamOptions();
        gameFormMessage.textContent = "Partido registrado correctamente.";

        await loadGames();
    } catch (error) {
        gameFormMessage.textContent = "No se pudo conectar con el servidor.";
    }
}

async function submitGamesScore(event) {
    event.preventDefault();

    const scoreForm = event.target;
    const gameId = scoreForm.dataset.gameId;
    const formData = new FormData(scoreForm);
    const submitButton = scoreForm.querySelector('button[type="submit"]');
    const message = scoreForm.querySelector(".score-form-message");
    if (submitButton.disabled) return;

    const payload = {
        home_score: Number(formData.get("home_score")),
        away_score: Number(formData.get("away_score"))
    };

    submitButton.disabled = true;
    message.textContent = "Guardando marcador...";

    try {
        const response = await updateGamesScore(gameId, payload);
        const body = await response.json().catch(() => ({}));

        if (!response.ok) {
            message.textContent = body.detail || "No se pudo actualizar el marcador.";
            submitButton.disabled = false;
            return;
        }

        // Reflect the confirmed result immediately instead of reloading the
        // public schedule, which may still be cached briefly at the edge.
        gamesState = gamesState.map((game) => game.id === Number(gameId)
            ? {...game, home_score: body.home_score, away_score: body.away_score, status: "completed"}
            : game);
        renderFilteredGames();
    } catch (error) {
        message.textContent = "No se pudo actualizar el marcador.";
        submitButton.disabled = false;
    }
}

async function submitGameSchedule(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const message = form.querySelector(".game-time-message");
    if (button.disabled) return;
    const showMessage = text => {
        message.textContent = text;
        if (gameScheduleUpdateMessage) gameScheduleUpdateMessage.textContent = text;
    };
    const startTime = new FormData(form).get("start_time");
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Guardando horario…";
    showMessage("Guardando horario…");
    try {
        const response = await updateGameSchedule(form.dataset.gameId, startTime, Number(new FormData(form).get("field_number")));
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = Array.isArray(body.detail)
                ? body.detail.map(error => error.msg).join(". ") : body.detail;
            showMessage(detail || "No se pudo cambiar el horario.");
            return;
        }
        gamesState = gamesState.map(game => game.id === Number(body.id)
            ? {...game, start_time: body.start_time, field_number: body.field_number} : game);
        renderFilteredGames();
        showMessage("Horario y campo actualizados. Se conservan las asignaciones de oficiales.");
        const savedForm = gamesContainer.querySelector(`.game-time-form[data-game-id="${body.id}"]`);
        if (savedForm) {
            savedForm.closest("details").open = true;
            savedForm.querySelector(".game-time-message").textContent = "Horario y campo actualizados. Se conservan las asignaciones de oficiales.";
            savedForm.scrollIntoView({block: "nearest"});
        }
    } catch (error) {
        showMessage("No se pudo confirmar el cambio de horario. Revisa el partido antes de reintentar.");
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
}

gamesContainer.addEventListener("submit", (event) => {
    // Score forms are rendered dynamically, so one delegated listener handles all.
    if (event.target.classList.contains("game-time-form")) {
        submitGameSchedule(event);
    } else if (event.target.classList.contains("score-form")) {
        submitGamesScore(event);
    }
});

async function submitGameStatus(button) {
    if (button.disabled) return;
    const originalLabel = button.textContent;
    const message = button.parentElement.querySelector(".game-status-message");
    const showMessage = text => {
        message.textContent = text;
        gameScheduleUpdateMessage.textContent = text;
    };
    button.disabled = true;
    button.textContent = "Guardando…";
    showMessage("Guardando estado del partido…");
    try {
        const response = await updateGameStatus(button.dataset.gameStatus, button.dataset.nextStatus);
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = Array.isArray(body.detail)
                ? body.detail.map(error => error.msg).join(". ") : body.detail;
            showMessage(detail || "No se pudo cambiar el estado del partido.");
            return;
        }
        gamesState = gamesState.map(game => game.id === Number(body.id)
            ? {...game, status: body.status} : game);
        renderFilteredGames();
        showMessage(body.status === "scheduled"
            ? "Partido restablecido. Ya está programado y conserva su horario, campo y oficiales."
            : "Partido pospuesto. Puedes encontrarlo en Estado: Pospuestos para restablecerlo.");
    } catch (error) {
        showMessage("No se pudo confirmar el cambio. Revisa el estado del partido antes de reintentar.");
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
}

gamesContainer.addEventListener("click", async (event) => {
    const statusButton = event.target.closest("[data-game-status]");
    if (statusButton) {
        await submitGameStatus(statusButton);
        return;
    }

    const deleteButton = event.target.closest("[data-delete-game]");
    if (!deleteButton) return;
    if (!window.confirm("¿Eliminar este partido? Esta acción no se puede deshacer.")) return;
    deleteButton.disabled = true;
    const response = await deleteGame(deleteButton.dataset.deleteGame);
    if (response.ok) await loadGames();
    else deleteButton.disabled = false;
});


if (gameForm !== null) {
    gameForm.addEventListener("submit", registerGame);
}

manualGameBranch.addEventListener("change", renderManualTeamOptions);
manualGameCategory.addEventListener("change", () => {
    updateManualGameBranchControl();
    renderManualTeamOptions();
});
manualHomeTeamSearch.addEventListener("input", () => {
    renderManualTeamSelect(homeTeamSelect, manualHomeTeamSearch);
    updateGuestFields();
});
manualAwayTeamSearch.addEventListener("input", () => {
    renderManualTeamSelect(awayTeamSelect, manualAwayTeamSearch);
    updateGuestFields();
});

[gameFilterWeek, gameFilterBranch, gameFilterField, gameFilterStatus].forEach((filter) => {
    filter.addEventListener("change", renderFilteredGames);
});
gameFilterCategory.addEventListener("change", () => {
    updateGameFilterBranchControl();
    renderFilteredGames();
});
gameFilterTeam.addEventListener("input", renderFilteredGames);

updateManualGameBranchControl();
updateGameFilterBranchControl();

deleteGamesWeekButton.addEventListener("click", async () => {
    const week = gameFilterWeek.value;
    if (!week) return;
    const confirmation = window.prompt(
        `Esta acción eliminará todos los partidos de la jornada ${week}. Escribe ELIMINAR JORNADA ${week} para continuar.`
    );
    if (confirmation !== `ELIMINAR JORNADA ${week}`) {
        weekActionMessage.textContent = "No se eliminó ningún partido.";
        return;
    }
    deleteGamesWeekButton.disabled = true;
    weekActionMessage.textContent = "Eliminando jornada...";
    const response = await deleteGamesByWeek(week);
    if (!response.ok) {
        weekActionMessage.textContent = "No se pudo eliminar la jornada.";
        deleteGamesWeekButton.disabled = false;
        return;
    }
    const result = await response.json();
    weekActionMessage.textContent = `Se eliminaron ${result.deleted} partidos de la jornada ${week}.`;
    gameFilterWeek.value = "";
    await loadGames();
});

toggleGamesWeekStatusButton.addEventListener("click", async () => {
    const week = gameFilterWeek.value;
    const status = toggleGamesWeekStatusButton.dataset.nextStatus;
    if (!week || !status) return;
    const action = status === "postponed" ? "posponer" : "restaurar";
    if (!window.confirm(`¿Deseas ${action} los partidos pendientes de la jornada ${week}?`)) return;

    toggleGamesWeekStatusButton.disabled = true;
    weekActionMessage.textContent = "Actualizando jornada...";
    const response = await updateGamesStatusByWeek(week, status);
    const body = await response.json();
    if (!response.ok) {
        weekActionMessage.textContent = body.detail || "No se pudo actualizar la jornada.";
        toggleGamesWeekStatusButton.disabled = false;
        return;
    }
    weekActionMessage.textContent = `Se actualizaron ${body.updated} partidos de la jornada ${week}.`;
    await loadGames();
});


loadGamesTeams();
loadGames();
loadRefereeAssignmentOptions();

refereeAssignmentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(refereeAssignmentForm);
    const response = await assignGameReferee(
        fields.get("game_id"),
        fields.get("referee_id"),
        fields.get("position")
    );
    const body = response.status === 204 ? null : await response.json();
    refereeAssignmentMessage.textContent = response.ok
        ? "Oficial asignado correctamente."
        : (body.detail || "No se pudo asignar el árbitro.");
    if (response.ok) await renderAssignedReferees();
});

refereeAssignmentForm.elements.game_id.addEventListener("change", renderAssignedReferees);

assignedReferees.addEventListener("click", async (event) => {
    const refereeId = event.target.dataset.removeReferee;
    if (!refereeId) return;
    const gameId = refereeAssignmentForm.elements.game_id.value;
    const response = await removeGameReferee(gameId, refereeId);
    if (response.ok) await renderAssignedReferees();
});


function parseTesseractTsv(tsv) {
    return String(tsv || "")
        .split("\n")
        .slice(1)
        .map((line) => line.split("\t"))
        .filter((columns) => columns.length >= 12 && columns[0] === "5")
        .map((columns) => ({
            text: columns.slice(11).join("\t").trim(),
            left: Number(columns[6]),
            top: Number(columns[7]),
            width: Number(columns[8]),
            height: Number(columns[9])
        }))
        .filter((word) => word.text);
}


async function getImageDimensions(file) {
    if ("createImageBitmap" in window) {
        const bitmap = await createImageBitmap(file);
        try {
            return {width: bitmap.width, height: bitmap.height};
        } finally {
            bitmap.close();
        }
    }

    return new Promise((resolve, reject) => {
        const url = URL.createObjectURL(file);
        const image = new Image();
        image.onload = () => {
            resolve({width: image.naturalWidth, height: image.naturalHeight});
            URL.revokeObjectURL(url);
        };
        image.onerror = () => {
            URL.revokeObjectURL(url);
            reject(new Error("No se pudo leer la imagen."));
        };
        image.src = url;
    });
}


async function buildScheduleTimeCrop(file, dimensions) {
    const sourceWidth = Math.max(1, Math.round(dimensions.width * 0.028));
    const scale = 5;
    const canvas = document.createElement("canvas");
    canvas.width = sourceWidth * scale;
    canvas.height = dimensions.height * scale;
    const context = canvas.getContext("2d", {willReadFrequently: true});
    context.imageSmoothingEnabled = false;

    const url = URL.createObjectURL(file);
    try {
        const image = await new Promise((resolve, reject) => {
            const element = new Image();
            element.onload = () => resolve(element);
            element.onerror = () => reject(new Error("No se pudo preparar la columna de horarios."));
            element.src = url;
        });

        context.drawImage(
            image,
            0, 0, sourceWidth, dimensions.height,
            0, 0, canvas.width, canvas.height
        );
    } finally {
        URL.revokeObjectURL(url);
    }

    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = imageData.data;
    for (let index = 0; index < pixels.length; index += 4) {
        const gray = Math.round(
            pixels[index] * 0.299
            + pixels[index + 1] * 0.587
            + pixels[index + 2] * 0.114
        );
        const value = gray > 175 ? 255 : 0;
        pixels[index] = value;
        pixels[index + 1] = value;
        pixels[index + 2] = value;
    }
    context.putImageData(imageData, 0, 0);

    return {canvas, scale};
}


function mapTimeCropWords(tsv, scale) {
    return parseTesseractTsv(tsv).map((word) => ({
        ...word,
        left: Math.round(word.left / scale),
        top: Math.round(word.top / scale),
        width: Math.max(1, Math.round(word.width / scale)),
        height: Math.max(1, Math.round(word.height / scale))
    }));
}


async function analyzeScheduleImageInBrowser(file, weekOverride) {
    await loadScheduleOcr();

    const dimensions = await getImageDimensions(file);
    let worker = null;
    try {
        worker = await window.Tesseract.createWorker("spa", 1, {
            logger: (progress) => {
                if (progress.status !== "recognizing text") return;
                const percent = Math.round((progress.progress || 0) * 100);
                scheduleImportMessage.textContent = `Leyendo imagen... ${percent}%`;
            }
        });

        const result = await worker.recognize(file, {}, {tsv: true});
        const words = parseTesseractTsv(result.data.tsv);
        if (!words.length) {
            throw new Error("No se reconoció texto en la imagen.");
        }

        scheduleImportMessage.textContent = "Leyendo horarios...";
        const timeCrop = await buildScheduleTimeCrop(file, dimensions);
        await worker.setParameters({
            tessedit_char_whitelist: "0123456789:",
            tessedit_pageseg_mode: "6"
        });
        const timeResult = await worker.recognize(
            timeCrop.canvas,
            {},
            {tsv: true}
        );
        const timeWords = mapTimeCropWords(timeResult.data.tsv, timeCrop.scale);

        scheduleImportMessage.textContent = "Relacionando equipos reconocidos...";
        return analyzeGameScheduleOcr({
            image_width: dimensions.width,
            image_height: dimensions.height,
            recognized_text: result.data.text || "",
            week_override: Number(weekOverride),
            words: [...words, ...timeWords]
        });
    } finally {
        if (worker) await worker.terminate();
    }
}

function scheduleDivisionOptions(values, selected) {
    return `<option value="">Seleccionar</option>` + values.map(value => `<option value="${value}" ${value === selected ? "selected" : ""}>${value.toUpperCase()}</option>`).join("");
}
function scheduleTeamControl(proposal, side, index) {
    const selectedId = proposal[`${side}_team_id`];
    const source = proposal[`${side}_team`];
    const name = proposal[`${side}_match`] || source;
    const teams = [...gameTeamsState].sort(compareTeams);
    const options = teams.map(team => `<option value="${team.id}" ${team.id === selectedId ? "selected" : ""}>${escapeHtml(team.name)} · ${escapeHtml(team.branch)} · ${escapeHtml(team.category.toUpperCase())}</option>`).join("");
    const label = side === "home" ? "local" : "visitante";
    return `<small class="schedule-source-name">Archivo: ${escapeHtml(source)}</small>
        <select data-schedule-${side}-id="${index}" aria-label="Seleccionar equipo ${label} ${index + 1}"><option value="">Seleccionar equipo / invitado</option>${options}</select>
        <input data-schedule-${side}="${index}" aria-label="Nombre invitado ${label} ${index + 1}" maxlength="120" value="${escapeHtml(name)}" ${selectedId ? 'hidden' : ''}>`;
}
function refreshScheduleRow(index) {
    const field = name => scheduleReviewBody.querySelector(`[data-schedule-${name}="${index}"]`);
    const home = gameTeamsState.find(team => String(team.id) === field("home-id").value);
    const away = gameTeamsState.find(team => String(team.id) === field("away-id").value);
    field("home").hidden = Boolean(home);
    field("away").hidden = Boolean(away);
    const friendly = field("friendly").checked;
    const sameTeam = home && away && home.id === away.id;
    const compatible = home && away && home.category === away.category
        && (isUnifiedYouthCategory(home.category) || home.branch === away.branch);
    const valid = !sameTeam && (friendly || compatible);
    const choice = field("row");
    choice.disabled = !valid;
    choice.checked = Boolean(valid);
    const status = choice.closest("tr").lastElementChild;
    status.textContent = sameTeam ? "Selecciona dos equipos distintos" : valid ? "Listo" : home && away ? "Divisiones distintas: revisa el rol" : "Selecciona el equipo registrado o marca Amistoso si es invitado";
    choice.closest("tr").classList.toggle("schedule-row-warning", !valid);
    if (compatible && !friendly) {
        field("branch").value = home.branch;
        field("category").value = home.category;
    }
}
function setScheduleSaveProgress(state) {
    if (!scheduleSaveProgress) return;
    scheduleSaveProgress.hidden = state === "idle";
    scheduleSaveProgress.classList.toggle("is-complete", state === "complete");
    if (state === "complete") scheduleSaveProgress.setAttribute("aria-valuenow", "100");
    else scheduleSaveProgress.removeAttribute("aria-valuenow");
}
function setScheduleConfirmMessage(message) {
    scheduleImportMessage.textContent = message;
    if (scheduleConfirmMessage) scheduleConfirmMessage.textContent = message;
}
function renderGameScheduleReview(result) {
    setScheduleSaveProgress("idle");
    if (scheduleConfirmMessage) scheduleConfirmMessage.textContent = "";
    scheduleImportState = result;
    scheduleReview.classList.remove("hidden");
    scheduleReviewHead.innerHTML = `<tr><th>Importar</th><th>Amistoso</th><th>Jornada</th><th>Campo</th><th>Hora</th><th>Local</th><th>Visitante</th><th>Rama / Categoría</th><th>Estado</th></tr>`;
    scheduleReviewBody.innerHTML = result.proposals.map((proposal, index) => `
        <tr class="${proposal.ready ? "" : "schedule-row-warning"}">
            <td><input type="checkbox" data-schedule-row="${index}" ${proposal.ready ? "checked" : "disabled"} aria-label="Importar partido ${index + 1}"></td>
            <td><input type="checkbox" data-schedule-friendly="${index}" aria-label="Amistoso ${index + 1}"></td>
            <td>${proposal.week}</td><td>${proposal.field_number}</td>
            <td><input type="time" data-schedule-time="${index}" aria-label="Hora del partido ${index + 1}" value="${escapeHtml(proposal.start_time || "")}" required></td>
            <td>${scheduleTeamControl(proposal, "home", index)}</td>
            <td>${scheduleTeamControl(proposal, "away", index)}</td>
            <td><div class="schedule-division-fields"><select data-schedule-branch="${index}" aria-label="Rama ${index + 1}">${scheduleDivisionOptions(["varonil","femenil","mixto"],proposal.suggested_branch || proposal.home_match_branch || proposal.away_match_branch)}</select>
            <select data-schedule-category="${index}" aria-label="Categoría ${index + 1}">${scheduleDivisionOptions(["u6","u7","u8","u10","u12","u14","u16","u18","libre"],proposal.suggested_category || proposal.home_match_category || proposal.away_match_category)}</select></div></td>
            <td>${proposal.ready ? "Listo" : "Selecciona el equipo registrado o marca Amistoso si es invitado"}</td>
        </tr>`).join("");
    result.proposals.forEach((_, index) => refreshScheduleRow(index));
    confirmScheduleButton.disabled = result.proposals.length === 0;
    scheduleImportMessage.textContent = `${result.matched} partido(s) listos y ${result.unmatched} fila(s) por revisar. Selecciona los equipos pendientes en cada fila. Usa Amistoso únicamente si el partido corresponde a invitados o divisiones distintas.`;
}
scheduleReviewBody.addEventListener("change", event => {
    const index = event.target.dataset.scheduleFriendly
        ?? event.target.dataset.scheduleHomeId ?? event.target.dataset.scheduleAwayId;
    if (index !== undefined) refreshScheduleRow(index);
});


scheduleImportForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const scheduleFields = new FormData(scheduleImportForm);
    const file = scheduleFields.get("file");
    const weekOverride = scheduleFields.get("week_override");
    scheduleReview.classList.add("hidden");
    scheduleImportState = null;
    scheduleImportMessage.textContent = "Analizando archivo...";
    setScheduleSaveProgress("idle");
    if (scheduleConfirmMessage) scheduleConfirmMessage.textContent = "";

    try {
        await loadGamesTeams();
        const isImage = file instanceof File && file.type.startsWith("image/");
        const response = isImage
            ? await window.analyzeScheduleImageCells(
                file,
                weekOverride,
                (message) => { scheduleImportMessage.textContent = message; }
            )
            : await analyzeGameSchedule(file);
        const body = await response.json();
        if (!response.ok) {
            scheduleImportMessage.textContent = body.detail || "No se pudo analizar el rol.";
            return;
        }
        renderGameScheduleReview(body);
    } catch (error) {
        scheduleImportMessage.textContent = error.message || "No se pudo analizar el rol.";
    }
});


confirmScheduleButton?.addEventListener("click", async () => {
    if (!scheduleImportState || confirmScheduleButton.disabled) return;
    confirmScheduleButton.disabled = true;
    const selected = [...scheduleReviewBody.querySelectorAll("[data-schedule-row]:checked")].map(checkbox => {
        const index = Number(checkbox.dataset.scheduleRow);
        const proposal = scheduleImportState.proposals[index];
        const field = name => scheduleReviewBody.querySelector(`[data-schedule-${name}="${index}"]`);
        const homeName = field("home").value.trim(), awayName = field("away").value.trim();
        const homeId = Number(field("home-id").value) || null;
        const awayId = Number(field("away-id").value) || null;
        return {home_team_id: homeId, away_team_id: awayId,
            home_guest_name: homeId ? null : homeName, away_guest_name: awayId ? null : awayName,
            is_friendly: field("friendly").checked,
            branch: field("branch").value || null, category: field("category").value || null,
            week: proposal.week, field_number: proposal.field_number, start_time: field("time").value};
    });
    if (selected.some(game => (!game.home_team_id || !game.away_team_id) && !game.is_friendly)) {
        setScheduleConfirmMessage("Selecciona los equipos registrados o marca Amistoso si corresponde a invitados.");
        confirmScheduleButton.disabled = false;
        return;
    }
    if (selected.some(game => (!game.home_team_id && !game.home_guest_name) || (!game.away_team_id && !game.away_guest_name))) {
        setScheduleConfirmMessage("Escribe el nombre de cada invitado.");
        confirmScheduleButton.disabled = false;
        return;
    }
    if (selected.some(game => !game.home_team_id && !game.away_team_id && (!game.branch || !game.category))) {
        setScheduleConfirmMessage("Selecciona rama y categoría para los amistosos con dos invitados.");
        confirmScheduleButton.disabled = false;
        return;
    }
    if (!selected.length) {
        setScheduleConfirmMessage("Selecciona al menos un partido listo.");
        confirmScheduleButton.disabled = false;
        return;
    }
    if (selected.some((game) => !game.start_time)) {
        setScheduleConfirmMessage("Completa la hora de cada partido seleccionado antes de confirmar.");
        confirmScheduleButton.disabled = false;
        return;
    }
    const originalLabel = confirmScheduleButton.textContent;
    confirmScheduleButton.textContent = "Guardando partidos…";
    confirmScheduleButton.setAttribute("aria-busy", "true");
    setScheduleSaveProgress("saving");
    setScheduleConfirmMessage(`Guardando ${selected.length} partido(s)… Espera a que termine la importación.`);
    try {
        const response = await confirmGameSchedule(selected);
        const body = await response.json();
        setScheduleSaveProgress(response.ok ? "complete" : "idle");
        const detail = Array.isArray(body.detail)
            ? body.detail.map(error => error.msg).join(". ") : body.detail;
        setScheduleConfirmMessage(response.ok
            ? `${body.created} partido(s) creados; ${body.updated || 0} corregido(s); ${body.skipped} sin cambios.`
            : (detail || "No se pudo guardar el rol."));
        if (response.ok) {
            scheduleImportState = null;
            scheduleReview.classList.add("hidden");
            await loadGames();
        }
    } catch (error) {
        setScheduleSaveProgress("idle");
        setScheduleConfirmMessage("No se pudo confirmar el resultado del guardado. Reintenta la confirmación para verificarlo; los mismos partidos no se duplicarán.");
    } finally {
        confirmScheduleButton.textContent = originalLabel;
        confirmScheduleButton.removeAttribute("aria-busy");
        confirmScheduleButton.disabled = !scheduleImportState;
    }
});
