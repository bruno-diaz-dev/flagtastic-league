const teamForm = document.querySelector("#team-form");
const formMessage = document.querySelector("#form-message");
const teamsContainer = document.querySelector("#teams");

const rosterPanel = document.querySelector("#roster-panel");
const rosterTitle = document.querySelector("#roster-title");
const rosterSubtitle = document.querySelector("#roster-subtitle");
const rosterContainer = document.querySelector("#roster");

let teamState = [];

function renderEmptyTeamsState() {
    teamsContainer.innerHTML = `
        <div class="empty-state">
            <h3>Sin equipos registrados</h3>
            <p>Los equipos registrados aparecerán aquí.</p>
        </div>
    `;
}

function renderTeams(teams) {
    if (teams.length === 0) {
        renderEmptyTeamsState();
        return;
    }

    teamsContainer.innerHTML = teams
        .map((team) => `
            <button class="team-card" type="button" data-team-id="${team.id}">
                <div>
                    <h3>${team.name}</h3>
                    <p>${team.branch} / ${team.category}</p>
                </div>
                <span class="team-status">${team.status}</span>
            </button>
        `)
        .join("");
}

function renderGameTeamOptions(teams) {
    if (homeTeamSelect === null || awayTeamSelect === null) {
        return;
    }


    const options = teams
        .map((team) => {
            return `<option value="${team.id}">${team.name} - ${team.branch} / ${team.category}</option>`;
        })
        .join("");

        homeTeamSelect.innerHTML = options;
        awayTeamSelect.innerHTML = options;
}

function renderRoster(team) {
    rosterPanel.classList.remove("hidden");
    rosterTitle.textContent = `Roster de ${team.name}`;
    rosterSubtitle.textContent = `${team.branch} / ${team.category}`;

    if (team.players.length === 0) {
        rosterContainer.innerHTML = `
            <div class="empty-state">
                <h3>Sin jugadores registrados</h3>
                <p>Este equipo todavía no tiene jugadores registrados.</p>
            </div>
        `;
        return;
    }

    rosterContainer.innerHTML = team.players
        .map((player) => `
            <article class="roster-player">
                <span class="jersey-number">#${player.jersey_number}</span>
                <div>
                    <h3>${player.name}</h3>
                    <p>${player.age} años</p>
                </div>
            </article>
        `)
        .join("");
}

async function loadTeams() {
    teamsContainer.innerHTML = `
        <div class="empty-state">
            <h3>Cargando equipos</h3>
            <p>Espera un momento.</p>
        </div>
    `;

    try {
        const response = await getTeams();

        if (!response.ok) {
            teamsContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No se pudieron cargar los equipos</h3>
                    <p>Intenta recargar la página.</p>
                </div>
            `;
            return;
        }

        const teams = await response.json();
        teamsState = teams;
        renderGameTeamOptions(teamsState);
        renderTeams(teams);
    } catch (error) {
        teamsContainer.innerHTML = `
            <div class="empty-state">
                <h3>No se pudieron cargar los equipos</h3>
                <p>Revisa que el servidor esté encendido.</p>
            </div>
        `;
    }
}

async function loadTeamDetail(teamId) {
    rosterPanel.classList.remove("hidden");
    rosterTitle.textContent = "Cargando roster";
    rosterSubtitle.textContent = "Espera un momento.";
    rosterContainer.innerHTML = "";

    try {
        const response = await getTeamDetail(teamId);

        if (!response.ok) {
            rosterTitle.textContent = "No se pudo cargar el roster";
            rosterSubtitle.textContent = "Intenta seleccionar el equipo otra vez.";
            return;
        }

        const team = await response.json();
        renderRoster(team);
    } catch (error) {
        rosterTitle.textContent = "No se pudo cargar el roster";
        rosterSubtitle.textContent = "Revisa que el servidor esté encendido.";
    }
}

async function registerTeam(event) {
    event.preventDefault();

    const formData = new FormData(teamForm);

    const payload = {
        name: formData.get("name"),
        branch: formData.get("branch"),
        category: formData.get("category")
    };

    formMessage.textContent = "Registrando equipo...";

    try {
        const response = await createTeam(payload)
        if (!response.ok) {
            formMessage.textContent = "No se pudo registrar el equipo.";
            return;
        }

        await response.json();

        teamForm.reset();
        formMessage.textContent = "Equipo registrado correctamente.";

        await loadTeams();
    } catch (error) {
        formMessage.textContent = "No se pudo conectar con el servidor.";
    }
}

teamsContainer.addEventListener("click", (event) => {
    const teamCard = event.target.closest("[data-team-id]");

    if (teamCard === null) {
        return;
    }

    loadTeamDetail(teamCard.dataset.teamId);
});

teamForm.addEventListener("submit", registerTeam);