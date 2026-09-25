// Dedicated team roster page: public identity display and authorized additions.

const rosterPage = document.querySelector("#roster-page");
const teamId = rosterPage.dataset.teamId;
const rosterTitle = document.querySelector("#roster-title");
const rosterSubtitle = document.querySelector("#roster-subtitle");
const rosterContainer = document.querySelector("#roster");
const playerForm = document.querySelector("#player-form");
const playerFormMessage = document.querySelector("#player-form-message");


function initials(name) {
    return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}


function playerPhoto(player) {
    if (player.profile_photo_url) {
        return `<img class="roster-player-photo" src="${player.profile_photo_url}" alt="Foto de ${escapeHtml(player.aka || player.name)}">`;
    }
    return `<span class="roster-player-photo profile-placeholder" aria-hidden="true">${escapeHtml(initials(player.name))}</span>`;
}


function renderRoster(team) {
    rosterTitle.textContent = `Roster de ${team.name}`;
    rosterSubtitle.textContent = `${team.branch} / ${team.category} · ${team.players.length} jugadores`;

    if (team.players.length === 0) {
        rosterContainer.innerHTML = `
            <div class="empty-state">
                <h3>Sin jugadores registrados</h3>
                <p>Este equipo todavía no tiene jugadores registrados.</p>
            </div>`;
        return;
    }

    rosterContainer.innerHTML = team.players.map((player) => {
        const displayName = player.aka || player.name;
        const identity = player.aka
            ? `${escapeHtml(player.name)} · ${player.age} años`
            : `${player.age} años`;
        return `
            <article class="roster-player">
                ${playerPhoto(player)}
                <div class="roster-player-identity">
                    <h3>${escapeHtml(displayName)}</h3>
                    <p>${identity}</p>
                </div>
                <span class="jersey-number">#${player.jersey_number}</span>
            </article>`;
    }).join("");
}


async function loadRoster() {
    const response = await getTeamDetail(teamId);
    if (response.status === 404) {
        rosterTitle.textContent = "Equipo no encontrado";
        rosterSubtitle.textContent = "Regresa al directorio y selecciona otro equipo.";
        rosterContainer.innerHTML = "";
        return;
    }
    if (!response.ok) throw new Error("Roster request failed");
    renderRoster(await response.json());
}


playerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(playerForm);
    const response = await createPlayer(teamId, {
        name: fields.get("name"),
        curp: fields.get("curp"),
        age: Number(fields.get("age")),
        jersey_number: Number(fields.get("jersey_number"))
    });
    if (!response.ok) {
        const error = await response.json();
        playerFormMessage.textContent = error.detail || "No se pudo registrar al jugador.";
        return;
    }
    playerForm.reset();
    playerFormMessage.textContent = "Jugador registrado correctamente.";
    await loadRoster();
});


loadRoster().catch(() => {
    rosterTitle.textContent = "No se pudo cargar el roster";
    rosterSubtitle.textContent = "Intenta recargar la página.";
});
