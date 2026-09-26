// Teams directory controller: registration, filtering, navigation, and deletion.

const teamForm = document.querySelector("#team-form");
const formMessage = document.querySelector("#form-message");
const teamsContainer = document.querySelector("#teams");

const teamFilterBranch = document.querySelector("#team-filter-branch");
const teamFilterCategory = document.querySelector("#team-filter-category");

let teamsState = [];
let representativesState = [];

const teamStatusLabels = {
    pending: "Pendiente",
    active: "Activo",
    inactive: "Inactivo"
};

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
            <article class="team-card">
                <button class="team-card-main" type="button" data-team-id="${team.id}">
                    ${team.logo_url
                        ? `<img class="team-logo" src="${team.logo_url}" alt="Logo de ${escapeHtml(team.name)}">`
                        : `<span class="team-logo team-logo-placeholder" aria-hidden="true">${escapeHtml(team.name.charAt(0))}</span>`}
                    <div>
                        <h3>${escapeHtml(team.name)}</h3>
                        <p>${escapeHtml(team.branch)} / ${escapeHtml(team.category)}</p>
                    </div>
                    <span class="team-status team-status-${escapeHtml(team.status)}">${escapeHtml(teamStatusLabels[team.status] || team.status)}</span>
                </button>
                <div class="team-admin-actions admin-only">
                    <label>
                        Estado
                        <select data-team-status-id="${team.id}" aria-label="Estado de ${escapeHtml(team.name)}">
                            <option value="pending" ${team.status === "pending" ? "selected" : ""}>Pendiente</option>
                            <option value="active" ${team.status === "active" ? "selected" : ""}>Activo</option>
                            <option value="inactive" ${team.status === "inactive" ? "selected" : ""}>Inactivo</option>
                        </select>
                    </label>
                    <button class="team-status-button" type="button" data-update-team-status="${team.id}">Actualizar</button>
                    <label>
                        Vincular representante
                        <select data-team-representative-id="${team.id}" aria-label="Representante de ${escapeHtml(team.name)}">
                            <option value="">Selecciona una persona</option>
                            ${representativesState.map((user) => `<option value="${user.id}">${escapeHtml(user.display_name || user.name)}</option>`).join("")}
                        </select>
                    </label>
                    <button class="team-status-button" type="button" data-assign-team-representative="${team.id}">Vincular</button>
                    <button
                        class="team-delete-button"
                        type="button"
                        data-delete-team-id="${team.id}"
                        data-team-name="${escapeHtml(team.name)}"
                    >Eliminar</button>
                </div>
            </article>
        `)
        .join("");
}

function getFilteredTeams() {
    // Filters are combined so large divisions remain usable without re-fetching.
    const selectedBranch= teamFilterBranch.value;
    const selectedCategory = teamFilterCategory.value;

    return teamsState.filter((team) => {
        const matchesBranch =
            selectedBranch === "" || team.branch === selectedBranch;

        const matchesCategory =
            selectedCategory === "" || team.category === selectedCategory;

        return matchesBranch && matchesCategory;
    });
}

function renderFilteredTeams() {
    const filteredTeams = getFilteredTeams();
    renderTeams(filteredTeams);
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
        renderFilteredTeams();
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
        category: formData.get("category"),
        head_coach: formData.get("head_coach"),
        coach: formData.get("coach"),
        manager: formData.get("manager")
    };

    formMessage.textContent = "Registrando equipo...";

    try {
        const response = await createTeam(payload)

        if (response.status === 409) {
            formMessage.textContent = "Este equipo ya esta registrado en esta rama y categoria.";
            return;
        }
        if (!response.ok) {
            formMessage.textContent = "No se pudo registrar el equipo.";
            return;
        }

        const createdTeam = await response.json();
        const logoResponse = await uploadTeamLogo(
            createdTeam.id,
            formData.get("logo")
        );
        if (!logoResponse.ok) {
            formMessage.textContent = "El equipo se registró, pero no se pudo guardar el logo.";
            await loadTeams();
            return;
        }

        teamForm.reset();
        formMessage.textContent = "Equipo registrado correctamente.";

        await loadTeams();
    } catch (error) {
        formMessage.textContent = "No se pudo conectar con el servidor.";
    }
}

teamsContainer.addEventListener("click", async (event) => {
    const representativeButton = event.target.closest(
        "[data-assign-team-representative]"
    );

    if (representativeButton !== null) {
        const teamId = representativeButton.dataset.assignTeamRepresentative;
        const representativeSelect = teamsContainer.querySelector(
            `[data-team-representative-id="${teamId}"]`
        );
        if (!representativeSelect.value) {
            formMessage.textContent = "Selecciona un representante.";
            return;
        }
        representativeButton.disabled = true;
        const response = await assignTeamRepresentative(
            teamId,
            representativeSelect.value
        );
        representativeButton.disabled = false;
        formMessage.textContent = response.ok
            ? "Representante vinculado correctamente."
            : "No se pudo vincular al representante.";
        return;
    }

    const statusButton = event.target.closest("[data-update-team-status]");

    if (statusButton !== null) {
        const teamId = statusButton.dataset.updateTeamStatus;
        const statusSelect = teamsContainer.querySelector(
            `[data-team-status-id="${teamId}"]`
        );
        statusButton.disabled = true;
        const response = await updateTeamStatus(teamId, statusSelect.value);
        statusButton.disabled = false;
        if (!response.ok) {
            formMessage.textContent = "No se pudo actualizar el estado del equipo.";
            return;
        }
        formMessage.textContent = "Estado del equipo actualizado.";
        await loadTeams();
        return;
    }

    const deleteButton = event.target.closest("[data-delete-team-id]");

    if (deleteButton !== null) {
        const teamName = deleteButton.dataset.teamName;
        const confirmed = window.confirm(
            `¿Eliminar ${teamName}? También se eliminarán sus partidos, roster y estadísticas.`
        );
        if (!confirmed) {
            return;
        }

        const response = await deleteTeam(deleteButton.dataset.deleteTeamId);
        if (!response.ok) {
            formMessage.textContent = "No se pudo eliminar el equipo.";
            return;
        }

        formMessage.textContent = "Equipo eliminado correctamente.";
        await loadTeams();
        return;
    }

    const teamCard = event.target.closest("[data-team-id]");

    if (teamCard === null) {
        return;
    }

    window.location.assign(`/teams/${teamCard.dataset.teamId}/roster`);
});

teamFilterBranch.addEventListener("change", renderFilteredTeams);
teamFilterCategory.addEventListener("change", renderFilteredTeams);
teamForm.addEventListener("submit", registerTeam);

async function initializeTeams() {
    const usersResponse = await getAdminUsers();
    if (usersResponse.ok) {
        const users = await usersResponse.json();
        representativesState = users.filter((user) =>
            (user.roles || [user.role]).includes("team_representative")
        );
    }
    await loadTeams();
}

initializeTeams();
