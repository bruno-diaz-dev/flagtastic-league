// Personal dashboard controller. All displayed data is scoped by the session.

const joinForm = document.querySelector("#join-team-form");
const joinMessage = document.querySelector("#join-team-message");
const teamSelect = joinForm.elements.team_id;
const statsContainer = document.querySelector("#personal-stats");
const teamsContainer = document.querySelector("#dashboard-teams");
const profileForm = document.querySelector("#profile-form");
const profileMessage = document.querySelector("#profile-message");

const statisticLabels = {
    games: "Partidos",
    receptions: "Recepciones",
    points: "Puntos",
    tackles: "Tacleadas",
    interceptions: "Intercepciones",
    sacks: "Capturas",
    passes_completed: "Pases completos",
    passes_attempted: "Pases lanzados",
    completion_percentage: "% de pases completos"
};

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
    if (dashboard.player.profile_photo_url) {
        profilePhoto.src = dashboard.player.profile_photo_url;
        profilePhoto.alt = `Foto de ${displayName}`;
        profilePhoto.classList.remove("hidden");
    }

    statsContainer.innerHTML = Object.entries(statisticLabels).map(([key, label]) => {
        const rawValue = dashboard.statistics[key];
        const value = rawValue === null ? "-" : rawValue;
        return `<article class="stat-item"><span>${label}</span><strong>${value}</strong></article>`;
    }).join("");

    teamsContainer.innerHTML = dashboard.teams.length
        ? dashboard.teams.map((team) => `
            <article class="team-card">
                <div><h4>${escapeHtml(team.team_name)}</h4>
                <p>${escapeHtml(team.branch)} / ${escapeHtml(team.category)} · #${team.jersey_number}</p></div>
                <strong>${team.standing_position || "-"} / ${team.division_team_count}</strong>
            </article>`).join("")
        : `<div class="empty-state"><h4>Aún no tienes equipo</h4><p>Selecciona uno para comenzar.</p></div>`;
}

async function loadTeams() {
    const response = await getTeams();
    const teams = await response.json();
    teamSelect.innerHTML = `<option value="">Selecciona un equipo</option>` + teams.map(
        (team) => `<option value="${team.id}">${escapeHtml(team.name)} · ${escapeHtml(team.branch)} / ${escapeHtml(team.category)}</option>`
    ).join("");
}

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
