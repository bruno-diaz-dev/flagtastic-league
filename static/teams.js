// Teams directory controller: registration, filtering, navigation, and deletion.

const teamForm = document.querySelector("#team-form");
const formMessage = document.querySelector("#form-message");
const teamsContainer = document.querySelector("#teams");
const teamBranch = document.querySelector("#team-branch");
const teamCategory = document.querySelector("#team-category");
const teamBranchField = document.querySelector("#team-branch-field");
const teamYouthBranch = document.querySelector("#team-youth-branch");

const teamFilterBranch = document.querySelector("#team-filter-branch");
const teamFilterCategory = document.querySelector("#team-filter-category");
const teamFilterBranchField = document.querySelector("#team-filter-branch-field");
const teamFilterYouthBranch = document.querySelector("#team-filter-youth-branch");
const teamFilterSearch = document.querySelector("#team-filter-search");
const teamRegistration = document.querySelector("#team-registration");
const teamsCount = document.querySelector("#teams-count");

let teamsState = [];

const teamStatusLabels = {
    pending: "Pendiente",
    active: "Activo",
    inactive: "Inactivo"
};

const categoryOrder = ["u6", "u8", "u10", "u12", "u14", "u16", "u18", "libre"];
const branchOrder = ["varonil", "femenil", "mixto"];

function compareTeams(left, right) {
    const leftBranch = branchOrder.indexOf(left.branch);
    const rightBranch = branchOrder.indexOf(right.branch);
    const branchComparison = (leftBranch === -1 ? branchOrder.length : leftBranch)
        - (rightBranch === -1 ? branchOrder.length : rightBranch);
    if (branchComparison !== 0) {
        return branchComparison;
    }
    const leftCategory = categoryOrder.indexOf(left.category);
    const rightCategory = categoryOrder.indexOf(right.category);
    const categoryComparison = (leftCategory === -1 ? categoryOrder.length : leftCategory)
        - (rightCategory === -1 ? categoryOrder.length : rightCategory);
    if (categoryComparison !== 0) {
        return categoryComparison;
    }
    return left.name.localeCompare(right.name, "es", {sensitivity: "base"});
}

function updateTeamBranchControl() {
    const unified = isUnifiedYouthCategory(teamCategory.value);
    teamBranchField.classList.toggle("hidden", unified);
    teamYouthBranch.classList.toggle("hidden", !unified);
    teamBranch.required = !unified;
    if (unified) teamBranch.value = "mixto";
}

function updateTeamFilterBranchControl() {
    const unified = isUnifiedYouthCategory(teamFilterCategory.value);
    teamFilterBranchField.classList.toggle("hidden", unified);
    teamFilterYouthBranch.classList.toggle("hidden", !unified);
    if (unified) teamFilterBranch.value = "";
}

function renderEmptyTeamsState() {
    teamsContainer.innerHTML = `
        <div class="empty-state">
            <h3>${teamsState.length ? "Sin coincidencias" : "Sin equipos registrados"}</h3>
            <p>${teamsState.length ? "Prueba otro nombre o limpia los filtros." : "Los equipos registrados aparecerán aquí."}</p>
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
                <a class="team-card-main" href="/teams/${team.id}/roster">
                    ${team.logo_url
                        ? `<img class="team-logo" src="${team.logo_url}" alt="Logo de ${escapeHtml(team.name)}" loading="lazy" decoding="async">`
                        : `<span class="team-logo team-logo-placeholder" aria-hidden="true">${escapeHtml(team.name.charAt(0))}</span>`}
                    <div class="team-card-copy">
                        <h3>${escapeHtml(team.name)}</h3>
                        <p>${escapeHtml(divisionBranchLabel(team.branch, team.category))} / ${escapeHtml(team.category)}</p>
                        <span class="team-status team-status-${escapeHtml(team.status)}">${escapeHtml(teamStatusLabels[team.status] || team.status)}</span>
                    </div>
                </a>
                <a class="team-manage-link admin-only" href="/teams/${team.id}/manage">Administrar</a>
            </article>
        `)
        .join("");
}

function getFilteredTeams() {
    // Filters are combined so large divisions remain usable without re-fetching.
    const selectedBranch= teamFilterBranch.value;
    const selectedCategory = teamFilterCategory.value;
    const unified = isUnifiedYouthCategory(selectedCategory);
    const search = normalizeTeamSearch(teamFilterSearch.value);

    return teamsState.filter((team) => {
        const matchesBranch =
            unified || selectedBranch === "" || team.branch === selectedBranch;

        const matchesCategory =
            selectedCategory === "" || team.category === selectedCategory;

        return matchesBranch && matchesCategory && (!search || normalizeTeamSearch(team.name).includes(search));
    }).sort(compareTeams);
}

function renderFilteredTeams() {
    const filteredTeams = getFilteredTeams();
    teamsCount.textContent = `${filteredTeams.length} de ${teamsState.length} equipos`;
    renderTeams(filteredTeams);
}

function normalizeTeamSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-MX").trim();
}

function closeTeamRegistration() {
    teamRegistration.open = false;
    teamRegistration.querySelector("summary").focus();
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
    const submitButton = teamForm.querySelector('button[type="submit"]');
    if (submitButton.disabled) return;
    submitButton.disabled = true;

    const formData = new FormData(teamForm);

    const payload = {
        name: formData.get("name"),
        branch: isUnifiedYouthCategory(formData.get("category"))
            ? "mixto"
            : formData.get("branch"),
        category: formData.get("category"),
        head_coach: formData.get("head_coach"),
        coach: formData.get("coach"),
        manager: formData.get("manager")
    };

    formMessage.textContent = "Registrando equipo...";

    try {
        const response = await createTeam(payload)

        if (response.status === 409) {
            formMessage.textContent = "Ya existe un equipo con ese nombre en esta rama y categoría.";
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
            teamForm.reset();
            updateTeamBranchControl();
            closeTeamRegistration();
            await loadTeams();
            return;
        }

        teamForm.reset();
        updateTeamBranchControl();
        formMessage.textContent = "Equipo registrado correctamente.";
        closeTeamRegistration();

        await loadTeams();
    } catch (error) {
        formMessage.textContent = "No se pudo conectar con el servidor.";
    } finally {
        submitButton.disabled = false;
    }
}

teamFilterBranch.addEventListener("change", renderFilteredTeams);
teamFilterSearch.addEventListener("input", renderFilteredTeams);
document.querySelector("#clear-team-filters").addEventListener("click", () => {
    teamFilterSearch.value = "";
    teamFilterBranch.value = "";
    teamFilterCategory.value = "";
    updateTeamFilterBranchControl();
    renderFilteredTeams();
});
document.querySelector("#cancel-team-registration").addEventListener("click", closeTeamRegistration);
teamRegistration.addEventListener("toggle", () => {
    if (teamRegistration.open) teamForm.querySelector('[name="name"]').focus();
});
teamFilterCategory.addEventListener("change", () => {
    updateTeamFilterBranchControl();
    renderFilteredTeams();
});
teamCategory.addEventListener("change", updateTeamBranchControl);
teamForm.addEventListener("submit", registerTeam);

async function initializeTeams() {
    updateTeamBranchControl();
    updateTeamFilterBranchControl();
    await loadTeams();
}

initializeTeams();
