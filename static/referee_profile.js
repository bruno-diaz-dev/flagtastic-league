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
        ["Partidos completados", statistics.completed_games, "referee-kpi-completed"],
        ["Partidos registrados", statistics.games, ""],
        ["Jornadas con participación", statistics.weeks, ""]
    ].map(([label, value, className]) => `
        <article class="referee-profile-kpi ${className}">
            <strong>${escapeHtml(String(value))}</strong><span>${label}</span>
        </article>
    `).join("");

    const positions = [...statistics.positions].sort((a, b) => b.games - a.games);
    const total = positions.reduce((sum, position) => sum + position.games, 0);
    document.querySelector("#referee-profile-primary-position").textContent = positions[0]?.games > 0
        ? positionLabels[positions[0].position] || positions[0].position
        : "Sin asignaciones";
    refereePositions.innerHTML = positions.length && total > 0
        ? positions.map((position) => {
            const percent = Math.round(position.games / total * 100);
            return `
                <article class="referee-profile-bar">
                    <div class="referee-profile-bar-heading">
                        <span>${escapeHtml(positionLabels[position.position] || position.position)}</span>
                        <strong>${position.games} <small>${position.games === 1 ? "partido" : "partidos"}</small></strong>
                    </div>
                    <div class="referee-profile-bar-body">
                        <div class="referee-profile-bar-track" aria-hidden="true"><span style="width: ${percent}%"></span></div>
                        <span class="referee-profile-bar-percent">${percent}%</span>
                    </div>
                </article>`;
        }).join("")
        : `<div class="empty-state"><h4>Sin asignaciones registradas</h4><p>Su participación por puesto aparecerá al asignarle partidos.</p></div>`;
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
