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
                <form class="roster-photo-form team-scope-manager-only" data-player-id="${player.id}">
                    <label>
                        <span class="sr-only">Foto de ${escapeHtml(displayName)}</span>
                        <input name="photo" type="file" accept="image/jpeg,image/png,image/webp" required>
                    </label>
                    <button type="submit">Guardar foto</button>
                    <span class="roster-photo-message" role="status"></span>
                </form>
                <div class="roster-player-actions team-scope-manager-only">
                    <button class="secondary-button" type="button" data-edit-player="${player.id}">Editar</button>
                    <button class="danger-button" type="button" data-deactivate-player="${player.id}">Dar de baja</button>
                </div>
                <form class="roster-edit-form team-scope-manager-only hidden" data-player-id="${player.id}">
                    <label>Nombre<input name="name" required></label>
                    <label>CURP<input name="curp" minlength="18" maxlength="18" required></label>
                    <label>Edad calendario<input name="age" type="number" readonly tabindex="-1"></label>
                    <label>Número<input name="jersey_number" type="number" min="0" required></label>
                    <div class="form-actions">
                        <button type="submit">Guardar cambios</button>
                        <button class="secondary-button" type="button" data-cancel-edit>Cancelar</button>
                    </div>
                    <span class="roster-edit-message" role="status"></span>
                </form>
            </article>`;
    }).join("");
}


rosterContainer.addEventListener("submit", async (event) => {
    const form = event.target.closest(".roster-photo-form");
    if (!form) return;
    event.preventDefault();
    const message = form.querySelector(".roster-photo-message");
    const file = form.elements.photo.files[0];
    message.textContent = "Guardando...";
    const response = await uploadRosterPlayerPhoto(
        teamId,
        form.dataset.playerId,
        file
    );
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        message.textContent = body.detail || "No se pudo guardar la foto.";
        return;
    }
    message.textContent = "Foto actualizada.";
    await loadRoster();
});


rosterContainer.addEventListener("submit", async (event) => {
    const form = event.target.closest(".roster-edit-form");
    if (!form) return;
    event.preventDefault();
    const message = form.querySelector(".roster-edit-message");
    const fields = new FormData(form);
    message.textContent = "Guardando...";
    const response = await updateRosterPlayer(teamId, form.dataset.playerId, {
        name: fields.get("name"),
        curp: fields.get("curp"),
        age: Number(fields.get("age")) || null,
        jersey_number: Number(fields.get("jersey_number"))
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        message.textContent = body.detail || "No se pudo actualizar al jugador.";
        return;
    }
    await loadRoster();
});


rosterContainer.addEventListener("input", (event) => {
    if (event.target.name !== "curp") return;
    const form = event.target.closest(".roster-edit-form");
    if (!form) return;
    form.elements.age.value = calendarAgeFromCurp(event.target.value) ?? "";
});


rosterContainer.addEventListener("click", async (event) => {
    const editButton = event.target.closest("[data-edit-player]");
    if (editButton) {
        const playerId = editButton.dataset.editPlayer;
        const form = rosterContainer.querySelector(
            `.roster-edit-form[data-player-id="${playerId}"]`
        );
        const response = await getManagedRosterPlayer(teamId, playerId);
        if (!response.ok) return;
        const player = await response.json();
        form.elements.name.value = player.name;
        form.elements.curp.value = player.curp;
        form.elements.age.value = player.age;
        form.elements.jersey_number.value = player.jersey_number;
        form.classList.remove("hidden");
        return;
    }

    const cancelButton = event.target.closest("[data-cancel-edit]");
    if (cancelButton) {
        cancelButton.closest(".roster-edit-form").classList.add("hidden");
        return;
    }

    const deactivateButton = event.target.closest("[data-deactivate-player]");
    if (!deactivateButton) return;
    if (!window.confirm("¿Dar de baja a este jugador del roster? Sus estadísticas se conservarán.")) return;
    const response = await deactivateRosterPlayer(
        teamId,
        deactivateButton.dataset.deactivatePlayer
    );
    if (response.ok) await loadRoster();
});


async function loadRoster() {
    const response = await getTeamDetail(teamId);
    if (response.status === 404) {
        rosterTitle.textContent = "Equipo no encontrado";
        rosterSubtitle.textContent = "Regresa al directorio y selecciona otro equipo.";
        rosterContainer.innerHTML = "";
        return;
    }
    if (!response.ok) throw new Error("Roster request failed");
    const team = await response.json();
    // A representative role does not grant league-wide access. The API
    // resolves whether this user manages this particular team.
    document.body.classList.toggle("can-manage-team", team.can_manage === true);
    renderRoster(team);
}


playerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(playerForm);
    const response = await createPlayer(teamId, {
        name: fields.get("name"),
        curp: fields.get("curp"),
        age: Number(fields.get("age")) || null,
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


playerForm.elements.curp.addEventListener("input", (event) => {
    playerForm.elements.age.value = calendarAgeFromCurp(event.target.value) ?? "";
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
