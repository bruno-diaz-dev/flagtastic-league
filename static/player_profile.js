// Read-only season profile shared by roster, leaderboard and admin links.

const publicProfilePage = document.querySelector("#public-player-profile");
const publicPlayerId = publicProfilePage.dataset.playerId;
const publicStats = document.querySelector("#public-player-stats");
const publicTeams = document.querySelector("#public-player-teams");
const publicMessage = document.querySelector("#public-player-message");

document.querySelector("#public-profile-back").addEventListener("click", () => {
    if (window.history.length > 1) window.history.back();
    else window.location.assign("/teams");
});

const publicStatisticLabels = {
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


function profileInitials(name) {
    return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}


function renderPublicProfile(profile) {
    const displayName = profile.player.aka || profile.player.name;
    document.querySelector("#public-player-name").textContent = displayName;
    document.querySelector("#public-player-identity").textContent = profile.player.aka
        ? `${profile.player.name} · ${profile.player.age} años`
        : `${profile.player.age} años`;

    const photo = document.querySelector("#public-player-photo");
    const placeholder = document.querySelector("#public-player-photo-placeholder");
    if (profile.player.profile_photo_url) {
        photo.src = profile.player.profile_photo_url;
        photo.alt = `Foto de ${displayName}`;
        photo.classList.remove("hidden");
        placeholder.classList.add("hidden");
    } else {
        placeholder.textContent = profileInitials(profile.player.name);
    }

    publicStats.innerHTML = Object.entries(publicStatisticLabels).map(([key, label]) => {
        const rawValue = profile.statistics[key];
        const value = rawValue === null ? "-" : rawValue;
        return `<article class="stat-item"><span>${label}</span><strong>${value}</strong></article>`;
    }).join("");

    publicTeams.innerHTML = profile.teams.length
        ? profile.teams.map((team) => `
            <article class="team-card">
                <div><h4>${escapeHtml(team.team_name)}</h4>
                <p>${escapeHtml(team.branch)} / ${escapeHtml(team.category)} · #${team.jersey_number}</p></div>
                <strong>${team.standing_position || "-"} / ${team.division_team_count}</strong>
            </article>`).join("")
        : `<div class="empty-state"><h4>Sin equipo registrado</h4><p>Este jugador todavía no aparece en un roster.</p></div>`;
}


async function loadPublicProfile() {
    const response = await getPublicPlayerProfile(publicPlayerId);
    if (response.status === 404) {
        publicMessage.textContent = "Jugador no encontrado.";
        return;
    }
    if (!response.ok) throw new Error("Player profile request failed");
    renderPublicProfile(await response.json());
}


loadPublicProfile().catch(() => {
    publicMessage.textContent = "No se pudo cargar el perfil del jugador.";
});
