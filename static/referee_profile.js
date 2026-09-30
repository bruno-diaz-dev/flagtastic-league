// Read-only referee experience visible to authenticated league users.

const refereeProfilePage = document.querySelector("#public-referee-profile");
const refereeUserId = refereeProfilePage.dataset.userId;
const refereeStats = document.querySelector("#referee-profile-stats");
const refereePositions = document.querySelector("#referee-profile-positions");
const refereeMessage = document.querySelector("#referee-profile-message");

const positionLabels = {
    referee: "Referee",
    down_judge: "Down Judge",
    field_judge: "Field Judge",
    side_judge: "Side Judge",
    statistician: "Estadístico"
};


function initials(name) {
    return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}


function renderRefereeProfile(profile) {
    document.querySelector("#referee-profile-name").textContent = profile.display_name;
    document.querySelector("#referee-profile-identity").textContent = profile.aka
        ? profile.name
        : "Miembro de la planilla arbitral";

    const photo = document.querySelector("#referee-profile-photo");
    const placeholder = document.querySelector("#referee-profile-photo-placeholder");
    if (profile.profile_photo_url) {
        photo.src = profile.profile_photo_url;
        photo.alt = `Foto de ${profile.display_name}`;
        photo.classList.remove("hidden");
        placeholder.classList.add("hidden");
    } else {
        placeholder.textContent = initials(profile.display_name);
    }

    const statistics = profile.statistics;
    refereeStats.innerHTML = [
        ["Partidos registrados", statistics.games],
        ["Partidos completados", statistics.completed_games],
        ["Jornadas con participación", statistics.weeks]
    ].map(([label, value]) => `
        <article class="stat-item"><span>${label}</span><strong>${value}</strong></article>
    `).join("");

    refereePositions.innerHTML = statistics.positions.length
        ? statistics.positions.map((position) => `
            <article class="referee-position-item">
                <span>${positionLabels[position.position] || position.position}</span>
                <strong>${position.games}</strong>
                <small>${position.games === 1 ? "partido" : "partidos"}</small>
            </article>
        `).join("")
        : `<div class="empty-state"><h4>Sin asignaciones registradas</h4><p>Su experiencia aparecerá al asignarle partidos.</p></div>`;
}


document.querySelector("#referee-profile-back").addEventListener("click", () => {
    window.location.assign("/referees");
});


getPublicRefereeProfile(refereeUserId).then(async (response) => {
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 404) {
        refereeMessage.textContent = "Árbitro no encontrado.";
        return;
    }
    if (!response.ok) throw new Error("Referee profile request failed");
    renderRefereeProfile(await response.json());
}).catch(() => {
    refereeMessage.textContent = "No se pudo cargar el perfil arbitral.";
});
