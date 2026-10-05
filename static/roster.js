// Dedicated team roster page: public identity display and authorized additions.

const rosterPage = document.querySelector("#roster-page");
const teamId = rosterPage.dataset.teamId;
const rosterTitle = document.querySelector("#roster-title");
const rosterSubtitle = document.querySelector("#roster-subtitle");
const rosterContainer = document.querySelector("#roster");
const playerForm = document.querySelector("#player-form");
const playerFormMessage = document.querySelector("#player-form-message");
const registeredPlayerForm = document.querySelector("#registered-player-form");
const registeredPlayerSearch = document.querySelector("#registered-player-search");
const registeredPlayerResults = document.querySelector("#registered-player-results");
const registeredPlayerMessage = document.querySelector("#registered-player-message");
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
        return `<img class="roster-player-photo" src="${player.profile_photo_url}" alt="Foto de ${escapeHtml(player.aka || player.name)}" loading="lazy" decoding="async">`;
    }
    return `<span class="roster-player-photo profile-placeholder" aria-hidden="true">${escapeHtml(initials(player.name))}</span>`;
}


function renderRoster(team) {
    rosterTitle.textContent = `Roster de ${team.name}`;
    rosterSubtitle.textContent = `${divisionBranchLabel(team.branch, team.category)} / ${team.category} · ${team.players.length} jugadores`;
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
                    <label class="file-input-label">
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
                    <label>Tipo de identificación<select name="identity_type"><option value="curp">CURP (18 caracteres)</option><option value="provisional">Documento provisional o escolar</option></select></label>
                    <label><span data-identity-label>CURP</span><input name="curp" minlength="18" maxlength="18" required></label>
                    <label class="hidden" data-birth-date-field>Fecha de nacimiento<input name="birth_date" type="date" disabled></label>
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
        identity_type: fields.get("identity_type"),
        birth_date: fields.get("birth_date") || null,
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
    if (!["curp", "birth_date"].includes(event.target.name)) return;
    const form = event.target.closest(".roster-edit-form");
    if (!form) return;
    updatePlayerIdentityAge(form);
});

rosterContainer.addEventListener("change", (event) => {
    if (event.target.name !== "identity_type") return;
    const form = event.target.closest(".roster-edit-form");
    if (form) updatePlayerIdentityFields(form);
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
        form.elements.identity_type.value = player.identity_type || "curp";
        form.elements.birth_date.value = player.birth_date || "";
        updatePlayerIdentityFields(form);
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
    const submitButton = playerForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    const fields = new FormData(playerForm);

    try {
        const response = await createPlayer(teamId, {
            name: fields.get("name"),
            curp: fields.get("curp"),
            identity_type: fields.get("identity_type"),
            birth_date: fields.get("birth_date") || null,
            age: Number(fields.get("age")) || null,
            jersey_number: Number(fields.get("jersey_number"))
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            playerFormMessage.textContent = body.detail || "No se pudo registrar al jugador.";
            return;
        }
        playerForm.reset();
        updatePlayerIdentityFields(playerForm);
        playerFormMessage.textContent = "Jugador registrado correctamente.";
        await loadRoster();
    } finally {
        submitButton.disabled = false;
    }
});


bindPlayerIdentityFields(playerForm);


let registeredPlayerSearchTimer;

registeredPlayerSearch.addEventListener("input", () => {
    window.clearTimeout(registeredPlayerSearchTimer);
    const query = registeredPlayerSearch.value.trim();
    registeredPlayerResults.disabled = true;
    registeredPlayerForm.querySelector('button[type="submit"]').disabled = true;
    if (query.length < 2) {
        registeredPlayerResults.innerHTML = '<option value="">Busca un perfil de jugador</option>';
        registeredPlayerMessage.textContent = "";
        return;
    }
    registeredPlayerMessage.textContent = "Buscando...";
    registeredPlayerSearchTimer = window.setTimeout(async () => {
        try {
            const response = await searchRegisteredPlayers(teamId, query);
            const players = await response.json();
            if (!response.ok) {
                registeredPlayerMessage.textContent = players.detail || "No se pudo realizar la búsqueda.";
                return;
            }
            if (!players.length) {
                registeredPlayerResults.innerHTML = '<option value="">Sin jugadores elegibles</option>';
                registeredPlayerMessage.textContent = "No hay coincidencias elegibles para esta división.";
                return;
            }
            registeredPlayerResults.innerHTML = [
                '<option value="">Selecciona un jugador</option>',
                ...players.map((player) => {
                    const displayName = player.aka
                        ? `${player.aka} (${player.name})`
                        : player.name;
                    const accountLabel = player.has_account ? "cuenta activa" : "perfil de roster";
                    return `<option value="${player.id}">${escapeHtml(displayName)} - ${accountLabel}</option>`;
                })
            ].join("");
            registeredPlayerResults.disabled = false;
            registeredPlayerMessage.textContent = `${players.length} coincidencia(s).`;
        } catch (error) {
            registeredPlayerMessage.textContent = "No se pudo conectar con el servidor.";
        }
    }, 300);
});


registeredPlayerResults.addEventListener("change", () => {
    registeredPlayerForm.querySelector('button[type="submit"]').disabled = (
        !registeredPlayerResults.value
    );
});


registeredPlayerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(registeredPlayerForm);
    registeredPlayerMessage.textContent = "Agregando al roster...";
    const response = await addRegisteredPlayer(teamId, {
        player_id: Number(fields.get("player_id")),
        jersey_number: Number(fields.get("jersey_number"))
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        registeredPlayerMessage.textContent = body.detail || "No se pudo agregar al jugador.";
        return;
    }
    registeredPlayerForm.reset();
    registeredPlayerResults.disabled = true;
    registeredPlayerForm.querySelector('button[type="submit"]').disabled = true;
    registeredPlayerResults.innerHTML = '<option value="">Busca un perfil de jugador</option>';
    registeredPlayerMessage.textContent = "Jugador agregado correctamente.";
    await loadRoster();
});


rosterImportForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(rosterImportForm);
    const submitButton = rosterImportForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    rosterImportMessage.textContent = "Validando e importando roster...";

    try {
        const response = await importRoster(teamId, fields.get("file"));
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            rosterImportMessage.textContent = data.detail || "No se pudo importar el roster.";
            return;
        }

        rosterImportForm.reset();
        const conflicts = data.conflicts || [];
        const parts = [
            `${data.created || 0} nuevos`,
            `${data.updated || 0} actualizados`,
            `${data.skipped || 0} ya existentes`
        ];
        if (conflicts.length) {
            parts.push(`${conflicts.length} conflictos`);
        }
        rosterImportMessage.textContent = parts.join(" · ") + ".";
        await loadRoster();
    } catch (error) {
        rosterImportMessage.textContent = "Ocurrió un error al procesar el roster. Intenta nuevamente.";
    } finally {
        submitButton.disabled = false;
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
