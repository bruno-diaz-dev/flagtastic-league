// Games page controller: scheduling, score capture, and game list rendering.

const gameForm = document.querySelector("#game-form");
const gameFormMessage = document.querySelector("#game-form-message");
const gamesContainer = document.querySelector("#games");

const homeTeamSelect = document.querySelector("[name='home_team_id']");
const awayTeamSelect = document.querySelector("[name='away_team_id']");
const gameFilterWeek = document.querySelector("#game-filter-week");
const gameFilterBranch = document.querySelector("#game-filter-branch");
const gameFilterCategory = document.querySelector("#game-filter-category");
const gameFilterField = document.querySelector("#game-filter-field");
const gamesCount = document.querySelector("#games-count");
const refereeAssignmentForm = document.querySelector("#referee-assignment-form");
const refereeAssignmentMessage = document.querySelector("#referee-assignment-message");
const assignedReferees = document.querySelector("#assigned-referees");
const scheduleImportForm = document.querySelector("#game-schedule-import-form");
const scheduleImportMessage = document.querySelector("#game-schedule-import-message");
const scheduleReview = document.querySelector("#game-schedule-review");
const scheduleReviewHead = document.querySelector("#game-schedule-review-head");
const scheduleReviewBody = document.querySelector("#game-schedule-review-body");
const confirmScheduleButton = document.querySelector("#confirm-game-schedule");
const deleteGamesWeekButton = document.querySelector("#delete-games-week");
const toggleGamesWeekStatusButton = document.querySelector("#toggle-games-week-status");
const weekActionMessage = document.querySelector("#week-action-message");

let gamesState = [];
let scheduleImportState = null;
const officialPositionLabels = {
    referee: "Referee",
    down_judge: "Down Judge",
    field_judge: "Field Judge",
    side_judge: "Side Judge",
    statistician: "Estadístico"
};


function gameLabel(game) {
    return `J${game.week}: ${game.home_team.name} vs ${game.away_team.name}`;
}

function gameTime(game) {
    return game.start_time ? game.start_time.slice(0, 5) : "Hora por asignar";
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


function renderGameTeamOption(teams){
    const options = teams
        .map((team) => {
            return `<option value="${team.id}">${team.name} - ${team.branch} / ${team.category}</option>`;
        })
        .join("");

        homeTeamSelect.innerHTML = options;
        awayTeamSelect.innerHTML = options;
    
}

function renderGames(games) {
    gamesCount.textContent = `${games.length} partido${games.length === 1 ? "" : "s"}`;

    if (games.length === 0) {
        gamesContainer.innerHTML = `
            <div class="empty-state">
                <h3>Sin partidos registrados</h3>
                <p>Los partidos registrados aparecerán aquí.</p>
            </div>
        `;
        return;
    }

    gamesContainer.innerHTML = games
        .map((game) => {
            const hasScore = game.home_score !== null && game.away_score !== null;
            const isPostponed = game.status === "postponed";
            const gameState = hasScore
                ? `<strong class="game-score">${game.home_score} - ${game.away_score}</strong>`
                : isPostponed
                    ? `<span class="game-status game-status-postponed">Pospuesto</span>`
                    : `
                        <form class="score-form admin-only" data-game-id="${game.id}">
                            <div class="score-fields">
                                <label>
                                    <span>Local</span>
                                    <input type="number" name="home_score" min="0" inputmode="numeric" aria-label="Puntos de ${escapeHtml(game.home_team.name)}" required>
                                </label>
                                <span class="score-separator" aria-hidden="true">-</span>
                                <label>
                                    <span>Visitante</span>
                                    <input type="number" name="away_score" min="0" inputmode="numeric" aria-label="Puntos de ${escapeHtml(game.away_team.name)}" required>
                                </label>
                            </div>
                            <button type="submit">Guardar</button>
                        </form>`;

            return `
                <article class="game-card">
                    <div class="game-card-summary">
                        <h3 class="game-matchup">
                            ${game.home_team.logo_url ? `<img class="team-logo team-logo-small" src="${game.home_team.logo_url}" alt="" loading="lazy" decoding="async">` : ""}
                            <span>${escapeHtml(game.home_team.name)}</span>
                            <span class="matchup-versus">vs</span>
                            ${game.away_team.logo_url ? `<img class="team-logo team-logo-small" src="${game.away_team.logo_url}" alt="" loading="lazy" decoding="async">` : ""}
                            <span>${escapeHtml(game.away_team.name)}</span>
                        </h3>
                        <p>Jornada ${game.week} · ${gameTime(game)} · ${escapeHtml(game.home_team.branch)} / ${escapeHtml(game.home_team.category)} · ${game.field_number ? `Campo ${game.field_number}` : "Campo por asignar"}</p>
                    </div>
                   
                    ${gameState}
                    <div class="game-card-actions">
                        <a class="secondary-link game-details-link" href="/games/${game.id}">Ver detalles</a>
                        ${!hasScore ? `
                            <button
                                class="secondary-button admin-only game-status-button"
                                type="button"
                                data-game-status="${game.id}"
                                data-next-status="${isPostponed ? "scheduled" : "postponed"}"
                            >${isPostponed ? "Restaurar" : "Posponer"}</button>
                        ` : ""}
                        <button class="danger-button admin-only" type="button" data-delete-game="${game.id}">
                            Eliminar
                        </button>
                    </div>
                </article>
            `;
        })
        .join("");
}

function populateWeekFilter(games) {
    const selectedWeek = gameFilterWeek.value;
    const weeks = [...new Set(games.map((game) => game.week))]
        .sort((first, second) => first - second);

    gameFilterWeek.innerHTML = `
        <option value="">Todas las jornadas</option>
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
    const filteredGames = gamesState.filter((game) => {
        const matchesWeek = (
            gameFilterWeek.value === ""
            || String(game.week) === gameFilterWeek.value
        );
        const matchesBranch = (
            gameFilterBranch.value === ""
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
        return matchesWeek && matchesBranch && matchesCategory && matchesField;
    });

    renderGames(filteredGames);
}

async function loadGamesTeams() {
    try {
        const response = await getTeams();

        if (!response.ok) {
            gameFormMessage.textContent = "No se pudieron cargar los equipos";
            return;
        }

        const teams = await response.json();
        renderGameTeamOption(teams);
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
        home_team_id: Number(formData.get("home_team_id")),
        away_team_id: Number(formData.get("away_team_id")),
        week: Number(formData.get("week")),
        field_number: Number(formData.get("field_number")),
        start_time: formData.get("start_time") || null
    };

    gameFormMessage.textContent = "Registrando partido...";

    try {
        const response = await createGame(payload);

        if (response.status === 409) {
            gameFormMessage.textContent ="Un equipo no puede jugar contra si mismo.";
            return;
        }

        if (response.status === 404) {
            gameFormMessage.textContent = "No se encontro a alguno de los equipos.";
            return;
        }

        if (!response.ok) {
            gameFormMessage.textContent = "No se pudo registrar el partido.";
            return;
        }

        gameForm.reset();
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

    const payload = {
        home_score: Number(formData.get("home_score")),
        away_score: Number(formData.get("away_score"))
    };

    try {
        const response = await updateGamesScore(gameId, payload);

        if (!response.ok) {
            return;
        }

        await loadGames();
    } catch (error) {
        return;
    }
}

gamesContainer.addEventListener("submit", (event) => {
    // Score forms are rendered dynamically, so one delegated listener handles all.
    if (event.target.classList.contains("score-form")) {
        submitGamesScore(event);
    }
});

gamesContainer.addEventListener("click", async (event) => {
    const statusButton = event.target.closest("[data-game-status]");
    if (statusButton) {
        statusButton.disabled = true;
        const response = await updateGameStatus(
            statusButton.dataset.gameStatus,
            statusButton.dataset.nextStatus
        );
        if (response.ok) await loadGames();
        else statusButton.disabled = false;
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

[gameFilterWeek, gameFilterBranch, gameFilterCategory, gameFilterField].forEach((filter) => {
    filter.addEventListener("change", renderFilteredGames);
});

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
    if (!window.Tesseract) {
        throw new Error("El lector OCR del navegador no está disponible.");
    }

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

function renderGameScheduleReview(result) {
    scheduleImportState = result;
    scheduleReview.classList.remove("hidden");
    scheduleReviewHead.innerHTML = `
<tr><th>Importar</th><th>Jornada</th><th>Campo</th><th>Hora</th><th>Local</th><th>Visitante</th><th>Rama / Categoría</th><th>Estado</th></tr>`;
    scheduleReviewBody.innerHTML = result.proposals.map((proposal, index) => `
        <tr class="${proposal.ready ? "" : "schedule-row-warning"}">
            <td><input type="checkbox" data-schedule-row="${index}" ${proposal.ready ? "checked" : "disabled"}></td>
            <td>${proposal.week}</td>
            <td>${proposal.field_number}</td>
            <td><input type="time" data-schedule-time="${index}" aria-label="Hora del partido ${index + 1}" value="${escapeHtml(proposal.start_time || "")}" required></td>
            <td>${escapeHtml(proposal.home_match || proposal.home_team)}</td>
            <td>${escapeHtml(proposal.away_match || proposal.away_team)}</td>
            <td>${escapeHtml([proposal.home_match_branch || proposal.away_match_branch, proposal.home_match_category || proposal.away_match_category].filter(Boolean).join(" / "))}</td>
            <td>${proposal.ready ? (proposal.start_time ? "Listo" : "Completa la hora") : `Sin coincidencia (${escapeHtml(proposal.source_row)})`}</td>
        </tr>`).join("");
    confirmScheduleButton.disabled = result.matched === 0;
    scheduleImportMessage.textContent = (
        `${result.matched} partido(s) listos y ${result.unmatched} fila(s) por corregir.`
    );
}


scheduleImportForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const scheduleFields = new FormData(scheduleImportForm);
    const file = scheduleFields.get("file");
    const weekOverride = scheduleFields.get("week_override");
    scheduleReview.classList.add("hidden");
    scheduleImportState = null;
    scheduleImportMessage.textContent = "Analizando archivo...";

    try {
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
    if (!scheduleImportState) return;
    confirmScheduleButton.disabled = true;
    const selected = [...scheduleReviewBody.querySelectorAll("[data-schedule-row]:checked")]
        .map((checkbox) => {
            const index = Number(checkbox.dataset.scheduleRow);
            return {...scheduleImportState.proposals[index], start_time: scheduleReviewBody.querySelector(`[data-schedule-time="${index}"]`).value};
        })
        .map((proposal) => ({
            home_team_id: proposal.home_team_id,
            away_team_id: proposal.away_team_id,
            week: proposal.week,
            field_number: proposal.field_number,
            start_time: proposal.start_time
        }));
    if (!selected.length) {
        scheduleImportMessage.textContent = "Selecciona al menos un partido listo.";
        confirmScheduleButton.disabled = false;
        return;
    }
    if (selected.some((game) => !game.start_time)) {
        scheduleImportMessage.textContent = "Completa la hora de cada partido seleccionado antes de confirmar.";
        confirmScheduleButton.disabled = false;
        return;
    }
    try {
        const response = await confirmGameSchedule(selected);
        const body = await response.json();
        scheduleImportMessage.textContent = response.ok
            ? `${body.created} partido(s) creados; ${body.updated || 0} corregido(s); ${body.skipped} sin cambios.`
            : (body.detail || "No se pudo guardar el rol.");
        if (response.ok) {
            scheduleImportState = null;
            scheduleReview.classList.add("hidden");
            await loadGames();
        }
    } catch (error) {
        scheduleImportMessage.textContent = "No se pudo guardar el rol. Reintenta la confirmacion.";
    } finally {
        confirmScheduleButton.disabled = !scheduleImportState;
    }
});
