// Private directory for signed-in league users and referee photo completion.

const roster = document.querySelector("#referee-roster");
const rosterMessage = document.querySelector("#referee-roster-message");
const photoPanel = document.querySelector("#referee-photo-panel");
const photoForm = document.querySelector("#referee-photo-form");
const photoMessage = document.querySelector("#referee-photo-message");


function refereeCard(referee) {
    const initials = referee.display_name
        .split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
    return `
        <article class="referee-roster-card">
            ${referee.profile_photo_url
                ? `<img src="${referee.profile_photo_url}" alt="Foto de ${escapeHtml(referee.display_name)}" loading="lazy" decoding="async">`
                : `<span class="referee-photo-placeholder" aria-hidden="true">${escapeHtml(initials)}</span>`}
            <div>
                <h3>${escapeHtml(referee.display_name)}</h3>
                ${referee.aka ? `<p>${escapeHtml(referee.name)}</p>` : ""}
            </div>
        </article>`;
}


async function loadRefereeRoster() {
    const response = await getRefereeRoster();
    if (response.status === 401) return window.location.assign("/login");
    if (!response.ok) {
        rosterMessage.textContent = "No se pudo cargar la plantilla de árbitros.";
        return;
    }
    const referees = await response.json();
    roster.innerHTML = referees.length
        ? referees.map(refereeCard).join("")
        : `<div class="empty-state"><h3>Sin árbitros activos</h3></div>`;
}


async function loadMyRefereeProfile() {
    const sessionResponse = await fetch("/api/auth/me");
    if (!sessionResponse.ok) return;
    const user = await sessionResponse.json();
    if (!(user.roles || [user.role]).includes("referee")) return;
    const response = await getMyRefereeProfile();
    if (!response.ok) return;
    const profile = await response.json();
    photoPanel.classList.remove("hidden");
    photoPanel.querySelector("h3").textContent = profile.profile_photo_url
        ? "Actualiza tu foto arbitral"
        : "Completa tu perfil arbitral";
}


photoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = new FormData(photoForm).get("file");
    photoMessage.textContent = "Guardando foto...";
    const response = await uploadMyRefereePhoto(file);
    photoMessage.textContent = response.ok
        ? "Foto arbitral actualizada correctamente."
        : ((await response.json()).detail || "No se pudo guardar la foto.");
    if (response.ok) {
        photoForm.reset();
        await Promise.all([loadRefereeRoster(), loadMyRefereeProfile()]);
    }
});


Promise.all([loadRefereeRoster(), loadMyRefereeProfile()]).catch(() => {
    rosterMessage.textContent = "No se pudo conectar con el servidor.";
});
