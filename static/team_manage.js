// League-administration change center for one team.

const managementPage = document.querySelector("#team-management-page");
const teamId = Number(managementPage.dataset.teamId);
const nameForm = document.querySelector("#team-name-form");
const statusForm = document.querySelector("#team-status-form");
const representativeForm = document.querySelector("#team-representative-form");
const representativesContainer = document.querySelector("#assigned-representatives");
const deleteButton = document.querySelector("#delete-managed-team");

let managedTeam = null;
let assignments = [];

function renderTeam() {
    document.querySelector("#managed-team-title").textContent = managedTeam.name;
    document.querySelector("#managed-team-division").textContent =
        `${managedTeam.branch} / ${managedTeam.category}`;
    nameForm.elements.name.value = managedTeam.name;
    statusForm.elements.status.value = managedTeam.status;
    const logo = document.querySelector("#managed-team-logo");
    if (managedTeam.logo_url) {
        logo.src = managedTeam.logo_url;
        logo.alt = `Logo de ${managedTeam.name}`;
        logo.classList.remove("hidden");
    }
}

function renderAssignments() {
    const teamAssignments = assignments.filter(
        (assignment) => assignment.team_id === teamId
    );
    representativesContainer.innerHTML = teamAssignments.length
        ? teamAssignments.map((assignment) => `
            <div class="assigned-representative">
                <span>${escapeHtml(assignment.display_name)}</span>
                <button type="button" data-remove-user-id="${assignment.user_id}">Quitar</button>
            </div>
        `).join("")
        : '<p class="empty-inline-state">Sin representantes vinculados.</p>';
}

async function loadManagementData() {
    const [teamResponse, usersResponse, assignmentsResponse] = await Promise.all([
        getTeamDetail(teamId),
        getAdminUsers(),
        getTeamRepresentativeAssignments()
    ]);
    if (teamResponse.status === 404) {
        window.location.replace("/teams");
        return;
    }
    if (!usersResponse.ok || !assignmentsResponse.ok) {
        window.location.replace("/teams");
        return;
    }
    managedTeam = await teamResponse.json();
    assignments = await assignmentsResponse.json();
    const users = await usersResponse.json();
    const representatives = users.filter((user) =>
        (user.roles || [user.role]).includes("team_representative")
    );
    representativeForm.elements.user_id.innerHTML = `
        <option value="">Selecciona una persona</option>
        ${representatives.map((user) => `
            <option value="${user.id}">${escapeHtml(user.display_name || user.name)}</option>
        `).join("")}
    `;
    renderTeam();
    renderAssignments();
}

nameForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.querySelector("#team-name-message");
    const response = await updateTeamName(teamId, nameForm.elements.name.value.trim());
    const body = await response.json().catch(() => ({}));
    message.textContent = response.ok ? "Nombre actualizado." : (body.detail || "No se pudo actualizar.");
    if (response.ok) {
        managedTeam = body;
        renderTeam();
    }
});

statusForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.querySelector("#team-status-message");
    const response = await updateTeamStatus(teamId, statusForm.elements.status.value);
    const body = await response.json().catch(() => ({}));
    message.textContent = response.ok ? "Estado actualizado." : (body.detail || "No se pudo actualizar.");
    if (response.ok) {
        managedTeam = body;
        renderTeam();
    }
});

representativeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.querySelector("#team-representative-message");
    const response = await assignTeamRepresentative(teamId, representativeForm.elements.user_id.value);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        message.textContent = body.detail || "No se pudo vincular.";
        return;
    }
    assignments = await (await getTeamRepresentativeAssignments()).json();
    representativeForm.reset();
    message.textContent = "Representante vinculado.";
    renderAssignments();
});

representativesContainer.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-remove-user-id]");
    if (!button) return;
    const response = await removeTeamRepresentative(teamId, button.dataset.removeUserId);
    const body = await response.json().catch(() => ({}));
    const message = document.querySelector("#team-representative-message");
    if (!response.ok) {
        message.textContent = body.detail || "No se pudo quitar.";
        return;
    }
    assignments = await (await getTeamRepresentativeAssignments()).json();
    message.textContent = "Representante desvinculado.";
    renderAssignments();
});

deleteButton.addEventListener("click", async () => {
    if (!window.confirm(`¿Eliminar ${managedTeam.name}? Esta acción no se puede deshacer.`)) return;
    const response = await deleteTeam(teamId);
    if (response.ok) {
        window.location.replace("/teams");
        return;
    }
    document.querySelector("#team-delete-message").textContent = "No se pudo eliminar el equipo.";
});

loadManagementData();
