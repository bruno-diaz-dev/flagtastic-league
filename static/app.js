const teamForm = document.querySelector("#team-form");
const formMessage = document.querySelector("#form-message");
const teamsContainer = document.querySelector("#teams");

function renderEmptyState() {
    teamsContainer.innerHTML = `
        <div class="empty-state">
            <h3>Sin equipos registrados</h3>
            <p>Los equipos registrados aparecerán aquí.</p>
        </div>
    `;
}

function renderTeams(teams) {
    if (teams.length === 0) {
        renderEmptyState();
        return;
    }

    teamsContainer.innerHTML = teams
        .map((team) => `
            <article class="team-card">
                <div>
                    <h3>${team.name}</h3>
                    <p>${team.branch} / ${team.category}</p>
                </div>
                <span class="team-status">${team.status}</span>
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
        const response = await fetch("/api/teams");

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
        const response = await fetch("/api/teams", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

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

teamForm.addEventListener("submit", registerTeam);

loadTeams();