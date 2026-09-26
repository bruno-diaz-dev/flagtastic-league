// Dedicated team roster page: public identity display and authorized additions.

const rosterPage = document.querySelector("#roster-page");
const teamId = rosterPage.dataset.teamId;
const rosterTitle = document.querySelector("#roster-title");
const rosterSubtitle = document.querySelector("#roster-subtitle");
const rosterContainer = document.querySelector("#roster");
const playerForm = document.querySelector("#player-form");
const playerFormMessage = document.querySelector("#player-form-message");
const rosterImportForm = document.querySelector("#roster-import-form");
const rosterImportMessage = document.querySelector("#roster-import-message");
const teamLogoForm = document.querySelector("#team-logo-form");
const teamLogoMessage = document.querySelector("#team-logo-message");
const teamStaff = document.querySelector("#team-staff");
const teamStaffForm = document.querySelector("#team-staff-form");
const teamStaffMessage = document.querySelector("#team-staff-message");


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
    const teamLogo = document.querySelector("#roster-team-logo");
    if (team.logo_url) {
        teamLogo.src = `${team.logo_url}?v=${Date.now()}`;
        teamLogo.alt = `Logo de ${team.name}`;
        teamLogo.classList.remove("hidden");
    } else {
        teamLogo.classList.add("hidden");
    }
    const staff = [
        ["Head Coach", team.head_coach],
        ["Coach", team.coach],
        ["Manager", team.manager]
    ].filter((entry) => entry[1]);
    teamStaff.innerHTML = staff.length
        ? staff.map(([role, name]) => `<div><span>${role}</span><strong>${escapeHtml(name)}</strong></div>`).join("")
        : `<p class="muted-text">Cuerpo técnico pendiente de registrar.</p>`;
    teamStaffForm.elements.head_coach.value = team.head_coach || "";
    teamStaffForm.elements.coach.value = team.coach || "";
    teamStaffForm.elements.manager.value = team.manager || "";

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
                <a class="roster-player-identity player-profile-link" href="/players/${player.id}">
                    <h3>${escapeHtml(displayName)}</h3>
                    <p>${identity}</p>
                </a>
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


rosterImportForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(rosterImportForm);
    rosterImportMessage.textContent = "Validando e importando roster...";
    try {
        const response = await importRoster(teamId, fields.get("file"));
        const data = await response.json();
        if (!response.ok) {
            rosterImportMessage.textContent = data.detail || "No se pudo importar el roster.";
            return;
        }
        rosterImportForm.reset();
        rosterImportMessage.textContent = `${data.imported} jugadores importados correctamente.`;
        await loadRoster();
    } catch (error) {
        rosterImportMessage.textContent = "No se pudo conectar con el servidor.";
    }
});


teamLogoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(teamLogoForm);
    teamLogoMessage.textContent = "Actualizando logo...";
    try {
        const response = await uploadTeamLogo(teamId, fields.get("logo"));
        if (!response.ok) {
            const error = await response.json();
            teamLogoMessage.textContent = error.detail || "No se pudo actualizar el logo.";
            return;
        }
        teamLogoForm.reset();
        teamLogoMessage.textContent = "Logo actualizado correctamente.";
        await loadRoster();
    } catch (error) {
        teamLogoMessage.textContent = "No se pudo conectar con el servidor.";
    }
});


teamStaffForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(teamStaffForm);
    const response = await updateTeamStaff(teamId, {
        head_coach: fields.get("head_coach"),
        coach: fields.get("coach"),
        manager: fields.get("manager")
    });
    if (!response.ok) {
        teamStaffMessage.textContent = "No se pudo actualizar el cuerpo técnico.";
        return;
    }
    teamStaffMessage.textContent = "Cuerpo técnico actualizado.";
    await loadRoster();
});


loadRoster().catch(() => {
    rosterTitle.textContent = "No se pudo cargar el roster";
    rosterSubtitle.textContent = "Intenta recargar la página.";
});
