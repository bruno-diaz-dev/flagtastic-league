// Personal dashboard controller. All displayed data is scoped by the session.

const joinForm = document.querySelector("#join-team-form");
const joinMessage = document.querySelector("#join-team-message");
const teamSelect = joinForm.elements.team_id;
const teamBranchFilter = document.querySelector("#join-team-branch");
const teamCategoryFilter = document.querySelector("#join-team-category");
const teamResults = document.querySelector("#join-team-results");
const statsContainer = document.querySelector("#personal-stats");
const teamsContainer = document.querySelector("#dashboard-teams");
const profileForm = document.querySelector("#profile-form");
const profileMessage = document.querySelector("#profile-message");

const statisticLabels = {
    weeks: "Jornadas con estadísticas",
    receptions: "Recepciones",
    points: "Puntos",
    tackles: "Tacleadas",
    interceptions: "Intercepciones",
    sacks: "Capturas",
    passes_completed: "Pases completos",
    passes_attempted: "Pases lanzados",
    completion_percentage: "% de pases completos"
};

const branchOrder = ["varonil", "femenil", "mixto"];
const categoryOrder = ["u6", "u8", "u10", "u12", "u14", "u16", "u18", "libre"];
let availableTeams = [];

function orderedValues(values, preferredOrder) {
    return [...new Set(values)].sort((left, right) => {
        const leftIndex = preferredOrder.indexOf(left);
        const rightIndex = preferredOrder.indexOf(right);
        const normalizedLeftIndex = leftIndex === -1 ? preferredOrder.length : leftIndex;
        const normalizedRightIndex = rightIndex === -1 ? preferredOrder.length : rightIndex;
        return normalizedLeftIndex - normalizedRightIndex
            || left.localeCompare(right, "es", {sensitivity: "base"});
    });
}

function renderTeamFilters() {
    const branches = orderedValues(availableTeams.map((team) => team.branch), branchOrder);
    const categories = orderedValues(availableTeams.map((team) => team.category), categoryOrder);

    teamBranchFilter.innerHTML = `<option value="">Todas las ramas</option>` + branches.map(
        (branch) => `<option value="${escapeHtml(branch)}">${escapeHtml(branch)}</option>`
    ).join("");
    teamCategoryFilter.innerHTML = `<option value="">Todas las categorías</option>` + categories.map(
        (category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`
    ).join("");
}

function renderTeamOptions() {
    const selectedTeamId = teamSelect.value;
    const branch = teamBranchFilter.value;
    const category = teamCategoryFilter.value;
    const matchingTeams = availableTeams.filter((team) => (
        (!branch || team.branch === branch)
        && (!category || team.category === category)
    ));

    teamSelect.innerHTML = `<option value="">${matchingTeams.length
        ? "Selecciona un equipo"
        : "No hay equipos con estos filtros"}</option>` + matchingTeams.map(
        (team) => `<option value="${team.id}">${escapeHtml(team.name)} · ${escapeHtml(team.branch)} / ${escapeHtml(team.category)}</option>`
    ).join("");
    teamSelect.disabled = matchingTeams.length === 0;
    if (matchingTeams.some((team) => String(team.id) === selectedTeamId)) {
        teamSelect.value = selectedTeamId;
    }
    teamResults.textContent = `${matchingTeams.length} ${matchingTeams.length === 1 ? "equipo disponible" : "equipos disponibles"}.`;
}

async function loadDashboard() {
    const response = await getMyDashboard();
    if (response.status === 401) {
        window.location.assign("/login");
        return;
    }
    if (response.status === 403) {
        window.location.assign("/teams");
        return;
    }
    const dashboard = await response.json();
    const displayName = dashboard.player.aka || dashboard.player.name;
    profileForm.elements.aka.value = dashboard.player.aka || "";
    document.querySelector("#dashboard-player-name").textContent = displayName;
    document.querySelector("#dashboard-greeting").textContent = dashboard.player.aka
        ? `${dashboard.player.name} · esta es tu temporada.`
        : "Esta es tu temporada.";

    const profilePhoto = document.querySelector("#dashboard-photo");
    const profilePhotoPlaceholder = document.querySelector("#dashboard-photo-placeholder");
    const initials = dashboard.player.name
        .split(/\s+/)
        .slice(0, 2)
        .map((part) => part.charAt(0))
        .join("")
        .toUpperCase();
    profilePhotoPlaceholder.textContent = initials;
    if (dashboard.player.profile_photo_url) {
        profilePhoto.src = dashboard.player.profile_photo_url;
        profilePhoto.alt = `Foto de ${displayName}`;
        profilePhoto.classList.remove("hidden");
        profilePhotoPlaceholder.classList.add("hidden");
        profilePhoto.onerror = () => {
            profilePhoto.classList.add("hidden");
            profilePhotoPlaceholder.classList.remove("hidden");
        };
    } else {
        profilePhoto.classList.add("hidden");
        profilePhotoPlaceholder.classList.remove("hidden");
    }

    statsContainer.innerHTML = Object.entries(statisticLabels).map(([key, label]) => {
        const rawValue = dashboard.statistics[key];
        const value = rawValue === null ? "-" : rawValue;
        return `<article class="stat-item"><span>${label}</span><strong>${value}</strong></article>`;
    }).join("");

    teamsContainer.innerHTML = dashboard.teams.length
        ? dashboard.teams.map((team) => `
            <article class="team-card">
                <div><h4><a class="team-roster-link" href="/teams/${team.team_id}/roster">${escapeHtml(team.team_name)}</a></h4>
                <p>${escapeHtml(team.branch)} / ${escapeHtml(team.category)} · #${team.jersey_number}</p></div>
                <strong>${team.standing_position || "-"} / ${team.division_team_count}</strong>
            </article>`).join("")
        : `<div class="empty-state"><h4>Aún no tienes equipo</h4><p>Selecciona uno para comenzar.</p></div>`;
}

async function loadTeams() {
    const response = await getTeams();
    if (!response.ok) {
        throw new Error("No se pudieron cargar los equipos");
    }
    availableTeams = await response.json();
    renderTeamFilters();
    renderTeamOptions();
}

teamBranchFilter.addEventListener("change", renderTeamOptions);
teamCategoryFilter.addEventListener("change", renderTeamOptions);

joinForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(joinForm);
    const response = await joinMyTeam(fields.get("team_id"), {
        jersey_number: Number(fields.get("jersey_number"))
    });
    if (!response.ok) {
        const error = await response.json();
        joinMessage.textContent = error.detail || "No se pudo completar el registro.";
        return;
    }
    joinMessage.textContent = "Registro completado.";
    joinForm.reset();
    renderTeamOptions();
    await loadDashboard();
});

profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const aka = new FormData(profileForm).get("aka").trim();
    const response = await updateMyProfile({aka: aka || null});
    const body = await response.json();
    profileMessage.textContent = response.ok
        ? "AKA actualizado correctamente."
        : (body.detail || "No se pudo actualizar el AKA.");
    if (response.ok) {
        await loadDashboard();
        await loadSessionIdentity();
    }
});

Promise.all([loadTeams(), loadDashboard()]).catch(() => {
    joinMessage.textContent = "No se pudo conectar con el servidor.";
});
