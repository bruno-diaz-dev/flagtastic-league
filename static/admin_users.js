// League administrators grant cumulative least-privilege roles here.

const usersBody = document.querySelector("#admin-users-body");
const usersMessage = document.querySelector("#admin-users-message");
const staffForm = document.querySelector("#staff-account-form");
const staffMessage = document.querySelector("#staff-account-message");
const userNameFilter = document.querySelector("#admin-user-name-filter");
const usersCount = document.querySelector("#admin-users-count");

let usersState = [];

const roleLabels = {
    player: "Jugador",
    team_representative: "Representante",
    referee: "Árbitro",
    league_admin: "Administrador de liga"
};


function roleChoices(selectedRoles) {
    return Object.entries(roleLabels).map(([value, label]) => `
        <label class="role-choice role-toggle">
            <input type="checkbox" name="roles" value="${value}"
                ${selectedRoles.includes(value) ? "checked" : ""}>
            <span>${label}</span>
        </label>
    `).join("");
}


function userStatus(user) {
    if (user.must_change_password) return {label: "Cambio de contraseña pendiente", tone: "pending"};
    return user.status === "active" ? {label: "Activo", tone: "active"} : {label: "Inactivo", tone: "inactive"};
}


// The band sums up who has access to what.
function renderUsersHero() {
    if (typeof setPageHero !== "function" || usersState.length === 0) return;
    const withRole = (role) => usersState.filter((user) => (user.roles || [user.role]).includes(role)).length;
    const pending = usersState.filter((user) => user.must_change_password).length;
    setPageHero({
        tags: pending ? [{label: `${pending} con cambio de contraseña pendiente`, tone: "live"}] : [],
        stats: [
            [usersState.length, "Usuarios"],
            [withRole("league_admin"), "Administradores"],
            [withRole("referee"), "Árbitros"],
            [withRole("team_representative"), "Representantes"],
        ],
    });
}


function normalizedSearchText(value) {
    return String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase("es-MX")
        .trim();
}


function renderUsers() {
    const query = normalizedSearchText(userNameFilter.value);
    const users = usersState.filter((user) => {
        const names = [user.display_name, user.name, user.aka]
            .map(normalizedSearchText);
        return query === "" || names.some((name) => name.includes(query));
    });
    usersCount.textContent = `${users.length} usuario${users.length === 1 ? "" : "s"}`;
    if (users.length === 0) {
        usersBody.innerHTML = `
            <div class="empty-state">
                <h3>Sin coincidencias</h3>
                <p>No hay usuarios que coincidan con ese nombre.</p>
            </div>`;
        return;
    }
    // One card per person: identity, roles as toggles, official alias, and
    // the account actions; rare, sensitive ones sit under "Más".
    usersBody.innerHTML = users.map((user) => {
        const shown = user.display_name || user.name;
        const status = userStatus(user);
        return `
        <article class="user-card" data-user-id="${user.id}">
            <div class="user-identity">
                <span class="user-avatar" aria-hidden="true">${escapeHtml(nameInitials(shown))}</span>
                <div>
                    ${user.player_id
                        ? `<a class="player-profile-link" href="/players/${user.player_id}"><strong>${escapeHtml(shown)}</strong></a>`
                        : `<strong>${escapeHtml(shown)}</strong>`}
                    ${user.aka ? `<small>Nombre legal: ${escapeHtml(user.name)}</small>` : ""}
                    <span class="user-email">${escapeHtml(user.email)}</span>
                </div>
                <span class="user-status user-status-${status.tone}">${status.label}</span>
            </div>
            <fieldset class="user-roles">
                <legend>Roles</legend>
                <div class="role-choices">${roleChoices(user.roles || [user.role])}</div>
            </fieldset>
            ${(user.roles || [user.role]).includes("referee") ? `
            <div class="official-aka-editor">
                <label>AKA de oficial
                    <input class="official-aka-input" value="${escapeHtml(user.aka || "")}" maxlength="80" placeholder="Alias en la liga" aria-label="AKA de ${escapeHtml(user.name)}">
                </label>
                <button class="save-aka-button secondary-button" type="button">Guardar AKA</button>
            </div>` : '<span class="official-aka-editor not-applicable">Sin alias de oficial</span>'}
            <div class="user-actions">
                <button class="save-role-button" type="button">Guardar roles</button>
                <details class="user-more">
                    <summary>Más</summary>
                    <div class="user-more-menu">
                        <button class="recover-account-button secondary-button" type="button">Recuperar cuenta</button>
                        <button class="reset-password-button secondary-button" type="button">Reiniciar contraseña</button>
                        <button class="delete-user-button danger-button" type="button">Eliminar cuenta</button>
                    </div>
                </details>
            </div>
        </article>`;
    }).join("");
}


async function loadUsers() {
    const response = await getAdminUsers();
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 403) return window.location.assign("/teams");
    if (!response.ok) {
        usersMessage.textContent = "No se pudieron cargar los usuarios.";
        return;
    }
    usersState = await response.json();
    renderUsersHero();
    renderUsers();
}


usersBody.addEventListener("click", async (event) => {
    const row = event.target.closest("[data-user-id]");
    if (!row) return;
    // An action from the "Más" menu closes it.
    if (event.target.closest(".user-more-menu")) event.target.closest("details").open = false;
    if (event.target.classList.contains("recover-account-button")) {
        const name = row.querySelector("strong").textContent;
        const email = window.prompt(`Nuevo correo de ${name}:`);
        if (!email || !email.trim()) return;
        if (!window.confirm(
            `¿Confirmaste la identidad de ${name} personalmente o por un teléfono conocido y que controla ${email.trim()}? Se cambiará el correo, se cerrarán todas sus sesiones y se invalidarán sus enlaces de recuperación.`
        )) return;
        const button = event.target;
        button.disabled = true;
        try {
            const response = await recoverAdminUserAccount(row.dataset.userId, email.trim());
            const body = await response.json().catch(() => ({}));
            if (!response.ok) {
                usersMessage.textContent = typeof body.detail === "string"
                    ? body.detail : "No se pudo recuperar la cuenta. Revisa el correo ingresado.";
                return;
            }
            usersMessage.textContent = `Cuenta de ${name} recuperada con ${body.email}. Debe cambiar la contraseña en la web antes de usar la app.`;
            window.prompt(
                "Copia la contraseña temporal y entrégala por el medio confirmado, nunca al correo anterior. No volverá a mostrarse:",
                body.temporary_password
            );
            await loadUsers();
        } catch {
            usersMessage.textContent = "No se pudo confirmar el resultado. Recarga los usuarios antes de volver a intentar.";
        } finally {
            button.disabled = false;
        }
        return;
    }
    if (event.target.classList.contains("reset-password-button")) {
        const name = row.querySelector("strong").textContent;
        if (!window.confirm(
            `¿Reiniciar la contraseña de ${name}? Se cerrarán todas sus sesiones activas.`
        )) return;

        event.target.disabled = true;
        const response = await resetAdminUserPassword(row.dataset.userId);
        const body = await response.json().catch(() => ({}));
        event.target.disabled = false;

        if (!response.ok) {
            usersMessage.textContent = body.detail || "No se pudo reiniciar la contraseña.";
            return;
        }

        usersMessage.textContent =
            `Contraseña de ${name} reiniciada. Debe cambiarla al iniciar sesión.`;
        window.prompt(
            "Contraseña temporal. Cópiala ahora; no volverá a mostrarse:",
            body.temporary_password
        );
        await loadUsers();
        return;
    }
    if (event.target.classList.contains("delete-user-button")) {
        const name = row.querySelector("strong").textContent;
        if (!window.confirm(`¿Eliminar la cuenta de ${name}? Su historial deportivo se conservará.`)) return;
        event.target.disabled = true;
        const response = await deleteAdminUser(row.dataset.userId);
        if (response.ok) {
            usersMessage.textContent = `Cuenta de ${name} eliminada.`;
            await loadUsers();
            return;
        }
        const body = await response.json();
        usersMessage.textContent = body.detail || "No se pudo eliminar la cuenta.";
        event.target.disabled = false;
        return;
    }
    if (event.target.classList.contains("save-aka-button")) {
        const input = row.querySelector(".official-aka-input");
        event.target.disabled = true;
        const response = await updateAdminRefereeAka(
            row.dataset.userId,
            input.value.trim()
        );
        const body = await response.json();
        usersMessage.textContent = response.ok
            ? `AKA de ${body.name} actualizado.`
            : (body.detail || "No se pudo actualizar el AKA.");
        event.target.disabled = false;
        if (response.ok) await loadUsers();
        return;
    }
    if (!event.target.classList.contains("save-role-button")) return;
    const roles = [...row.querySelectorAll("[name='roles']:checked")]
        .map((input) => input.value);
    if (roles.length === 0) {
        usersMessage.textContent = "Selecciona al menos un rol.";
        return;
    }
    event.target.disabled = true;
    const response = await updateAdminUserRoles(row.dataset.userId, roles);
    const body = await response.json();
    usersMessage.textContent = response.ok
        ? `Roles de ${body.display_name || body.name} actualizados.`
        : (body.detail || "No se pudieron actualizar los roles.");
    event.target.disabled = false;
    if (response.ok) await loadUsers();
});


staffForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(staffForm);
    const roles = data.getAll("staff_roles");
    if (roles.length === 0) {
        staffMessage.textContent = "Selecciona al menos un rol.";
        return;
    }
    const submit = staffForm.querySelector("button[type='submit']");
    submit.disabled = true;
    const response = await createStaffAccount({
        name: data.get("name"),
        email: data.get("email"),
        password: data.get("password"),
        roles
    });
    const body = await response.json();
    staffMessage.textContent = response.ok
        ? `Cuenta de ${body.display_name || body.name} creada.`
        : (body.detail || "No se pudo crear la cuenta.");
    submit.disabled = false;
    if (response.ok) {
        staffForm.reset();
        await loadUsers();
    }
});


userNameFilter.addEventListener("input", renderUsers);


loadUsers().catch(() => {
    usersMessage.textContent = "No se pudo conectar con el servidor.";
});
