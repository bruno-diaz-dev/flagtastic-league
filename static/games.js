// Games page controller: scheduling, score capture, and game list rendering.

const gameForm = document.querySelector("#game-form");
const gameFormMessage = document.querySelector("#game-form-message");
const gamesContainer = document.querySelector("#games");

const homeTeamSelect = document.querySelector("[name='home_team_id']");
const awayTeamSelect = document.querySelector("[name='away_team_id']");
const gameFilterWeek = document.querySelector("#game-filter-week");
const gameFilterBranch = document.querySelector("#game-filter-branch");
const gameFilterCategory = document.querySelector("#game-filter-category");
const gamesCount = document.querySelector("#games-count");

let gamesState = [];


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
            const score = hasScore
                ? `${game.home_score} - ${game.away_score}`
                : "Pendiente";

            return `
                <article class="game-card">
                    <div>
                        <h3>${escapeHtml(game.home_team.name)} vs ${escapeHtml(game.away_team.name)}</h3>
                        <p>Jornada ${game.week} · ${escapeHtml(game.home_team.branch)} / ${escapeHtml(game.home_team.category)}</p>
                    </div>
                   
                    ${
                        hasScore
                        ? `<strong>${score}</strong>`
                        : `
                            <form class="score-form admin-only" data-game-id="${game.id}">
                                <label>
                                    ${escapeHtml(game.home_team.name)}
                                    <input
                                        type="number"
                                        name="home_score"
                                        min="0"
                                        required
                                    >
                                </label>

                                <label>
                                    ${escapeHtml(game.away_team.name)}
                                    <input
                                        type="number"
                                        name="away_score"
                                        min="0"
                                        required
                                    >
                                </label>

                                <button type="submit">Guardar marcador</button>
                            </form>
                        `
                    }
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
        return matchesWeek && matchesBranch && matchesCategory;
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
        populateWeekFilter(gamesState);
        renderFilteredGames();
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
        week: Number(formData.get("week"))
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


if (gameForm !== null) {
    gameForm.addEventListener("submit", registerGame);
}

[gameFilterWeek, gameFilterBranch, gameFilterCategory].forEach((filter) => {
    filter.addEventListener("change", renderFilteredGames);
});


loadGamesTeams();
loadGames();
