// Signed-in directory and referee self-service profile.
const roster = document.querySelector("#referee-roster");
const rosterMessage = document.querySelector("#referee-roster-message");
const photoPanel = document.querySelector("#referee-photo-panel");
const photoForm = document.querySelector("#referee-photo-form");
const photoMessage = document.querySelector("#referee-photo-message");
const profileEditor = document.querySelector("#referee-profile-editor");
const search = document.querySelector("#referee-search");
const directoryCount = document.querySelector("#referee-directory-count");
let directory = [];
let saving = false;

function initialsFor(name) {
    return String(name || "Árbitro").trim().split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
}

function refereeCard(referee) {
    const name = escapeHtml(referee.display_name);
    return `<a class="referee-profile-link" href="/referees/${referee.id}" aria-label="Ver perfil de ${name}">
        <article class="referee-roster-card">
            ${referee.profile_photo_url
                ? `<img src="${escapeHtml(referee.profile_photo_url)}" alt="" loading="lazy" decoding="async">`
                : `<span class="referee-photo-placeholder" aria-hidden="true">${escapeHtml(initialsFor(referee.display_name))}</span>`}
            <div class="referee-card-identity"><h3>${name}</h3>
                ${referee.aka ? `<p>${escapeHtml(referee.name)}</p>` : ""}
                <span class="referee-profile-action">Ver trayectoria arbitral</span>
            </div><span class="referee-card-arrow" aria-hidden="true">›</span>
        </article></a>`;
}

function searchable(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es");
}

function renderDirectory() {
    const query = searchable(search.value.trim());
    const visible = directory.filter(referee => searchable(`${referee.name} ${referee.display_name} ${referee.aka || ""}`).includes(query));
    directoryCount.textContent = query
        ? `${visible.length} de ${directory.length} árbitros`
        : `${directory.length} ${directory.length === 1 ? "árbitro en la planilla" : "árbitros en la planilla"}`;
    roster.innerHTML = visible.length ? visible.map(refereeCard).join("")
        : `<div class="empty-state"><h3>${query ? "No encontramos coincidencias" : "Sin árbitros activos"}</h3><p>${query ? "Prueba otro nombre o AKA." : "El equipo arbitral aparecerá aquí."}</p></div>`;
}

async function loadRefereeRoster() {
    const response = await getRefereeRoster();
    if (response.status === 401) return window.location.assign("/login");
    if (!response.ok) {
        rosterMessage.textContent = "No se pudo cargar la planilla de árbitros.";
        directoryCount.textContent = "Planilla no disponible";
        return;
    }
    directory = await response.json();
    rosterMessage.textContent = "";
    renderDirectory();
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
    photoForm.querySelector("[name='aka']").value = profile.aka || "";
    document.querySelector("#referee-self-name").textContent = profile.display_name || profile.name;
    document.querySelector("#referee-self-avatar").innerHTML = profile.profile_photo_url
        ? `<img src="${escapeHtml(profile.profile_photo_url)}" alt="">`
        : escapeHtml(initialsFor(profile.display_name || profile.name));
}

search.addEventListener("input", renderDirectory);
document.querySelector("#referee-edit-cancel").addEventListener("click", () => {
    profileEditor.open = false;
    profileEditor.querySelector("summary").focus();
});

photoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (saving) return;
    saving = true;
    const button = photoForm.querySelector("[type='submit']");
    button.disabled = true;
    button.textContent = "Guardando…";
    const data = new FormData(photoForm);
    const file = data.get("file");
    photoMessage.textContent = "Guardando perfil…";
    try {
        const profileResponse = await updateMyRefereeProfile({ aka: data.get("aka") });
        if (!profileResponse.ok) {
            const body = await profileResponse.json();
            photoMessage.textContent = body.detail || "No se pudo guardar el AKA.";
            return;
        }
        if (file instanceof File && file.size > 0) {
            const photoResponse = await uploadMyRefereePhoto(file);
            if (!photoResponse.ok) {
                const body = await photoResponse.json();
                photoMessage.textContent = body.detail || "El AKA se guardó, pero no se pudo guardar la foto.";
                await loadRefereeRoster();
                return;
            }
        }
        photoForm.querySelector("[name='file']").value = "";
        await Promise.all([loadRefereeRoster(), loadMyRefereeProfile()]);
        photoMessage.textContent = "Perfil actualizado.";
        profileEditor.open = false;
        profileEditor.querySelector("summary").focus();
    } catch {
        photoMessage.textContent = "No se pudo conectar. Revisa tu conexión e intenta de nuevo.";
    } finally {
        saving = false;
        button.disabled = false;
        button.textContent = "Guardar cambios";
    }
});

Promise.allSettled([loadRefereeRoster(), loadMyRefereeProfile()]).then(results => {
    if (results[0].status === "rejected") {
        rosterMessage.textContent = "No se pudo conectar con el servidor.";
        directoryCount.textContent = "Planilla no disponible";
    }
});
