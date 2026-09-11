const gameForm = document.querySelector("#game-form");
const gameFormMessage = document.querySelector("#game-form-message");
const homeTeamSelect = document.querySelector("[name='home_team_id']");
const awayTeamSelect = document.querySelector("[name='away_team_id']");

const navLinks = document.querySelectorAll("[data-view]");
const views = document.querySelectorAll(".view");

const gamesContainer = document.querySelector("#games");

const standingsForm = document.querySelector("#standings-form");
const standingsFormMessage = document.querySelector("#standings-form-message");
const standingsContainer = document.querySelector("#standings");

function showView(viewName) {
    views.forEach((view) => {
        view.classList.toggle("active-view", view.id === `${viewName}-view`);
    });

    navLinks.forEach((link) => {
        link.classList.toggle("active", link.dataset.view === viewName);
    });

    if (viewName === "games") {
        loadGames();
    }
}


function renderGames(games) {
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
                        <h3>${game.home_team.name} vs ${game.away_team.name}</h3>
                        <p>${game.home_team.name} local / ${game.away_team.name} visitante</p>
                    </div>
                   
                    ${
                        hasScore
                        ? `<strong>${score}</strong>`
                        : `
                            <form class="score-form" data-game-id="${game.id}">
                                <label>
                                    ${game.home_team.name}
                                    <input
                                        type="number"
                                        name="home_score"
                                        min="0"
                                        required
                                    >
                                </label>

                                <label>
                                    ${game.away_team.name}
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

        const games = await response.json();
        renderGames(games);
    } catch (error) {
        gamesContainer.innerHTML = `
            <div class="empty-state">
                <h3>No se pudieron cargar los partidos</h3>
                <p>Revisa que el servidor esté encendido.</p>
            </div>
        `;
    }
}

navLinks.forEach((link) => {
    link.addEventListener("click", () => {
        showView(link.dataset.view);
    });
});

async function registerGame(event) {
    event.preventDefault();

    const formData = new FormData(gameForm);

    const payload = {
        home_team_id: Number(formData.get("home_team_id")),
        away_team_id: Number(formData.get("away_team_id"))
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

async function loadStandings(event) {
    event.preventDefault();

    const formData = new FormData(standingsForm);
    const branch = formData.get("branch");
    const category = formData.get("category");

    standingsFormMessage.textContent = "Consultando tabla...";

    try {
        const response = await getStandings(branch, category);

        if (!response.ok) {
            standingsFormMessage.textContent = "No se pudo consultar la tabla.";
            return;
        }

        const standings = await response.json();

        standingsFormMessage.textContent = "";
        renderStandings(standings);
    } catch (error) {
        standingsFormMessage.textContent = "No se pudo conectar con el servidor.";
    }
}

function renderStandings(standings) {
    if (standings.length === 0) {
        standingsContainer.innerHTML = `
            <div class="empty-state">
                <h3>Sin resultados</h3>
                <p>No hay partidos con marcador para esta rama y categoría.</p>
            </div>
        `;
        return;
    }

    standingsContainer.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Equipo</th>
                    <th>G</th>
                    <th>P</th>
                    <th>PF</th>
                    <th>PC</th>
                    <th>Dif</th>
                </tr>
            </thead>
            <tbody>
                ${standings
                    .map((team) => `
                        <tr>
                            <td>${team.team_name}</td>
                            <td>${team.wins}</td>
                            <td>${team.losses}</td>
                            <td>${team.points_for}</td>
                            <td>${team.points_against}</td>
                            <td>${team.point_difference}</td>
                        </tr>
                    `)
                    .join("")}
            </tbody>
        </table>
    `;
}

if (standingsForm !== null) {
    standingsForm.addEventListener("submit", loadStandings);
}

gamesContainer.addEventListener("submit", (event) => {
    if (!event.target.classList.contains("score-form")) {
        return;
    }

    submitGamesScore(event);
});


if (gameForm !== null) {
    gameForm.addEventListener("submit", registerGame);
}

loadTeams();