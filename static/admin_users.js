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
        <label class="role-choice">
            <input type="checkbox" name="roles" value="${value}"
                ${selectedRoles.includes(value) ? "checked" : ""}>
            <span>${label}</span>
        </label>
    `).join("");
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
            <tr><td colspan="6" class="table-empty-state">
                No hay usuarios que coincidan con ese nombre.
            </td></tr>`;
        return;
    }
    usersBody.innerHTML = users.map((user) => `
        <tr data-user-id="${user.id}">
            <td>${user.player_id
                ? `<a class="player-profile-link" href="/players/${user.player_id}"><strong>${escapeHtml(user.display_name || user.name)}</strong></a>`
                : `<strong>${escapeHtml(user.display_name || user.name)}</strong>`
            }${user.aka ? `<small>Nombre legal: ${escapeHtml(user.name)}</small>` : ""}</td>
            <td>${escapeHtml(user.email)}</td>
            <td><div class="role-choices">${roleChoices(user.roles || [user.role])}</div></td>
            <td>${(user.roles || [user.role]).includes("referee") ? `
                <div class="official-aka-editor">
                    <input class="official-aka-input" value="${escapeHtml(user.aka || "")}" maxlength="80" aria-label="AKA de ${escapeHtml(user.name)}">
                    <button class="save-aka-button" type="button">Guardar AKA</button>
                </div>` : '<span class="not-applicable">No aplica</span>'}</td>
            <td>${user.status === "active" ? "Activo" : "Inactivo"}</td>
            <td class="user-actions">
                <button class="save-role-button" type="button">Guardar</button>
                <button class="delete-user-button" type="button">Eliminar</button>
            </td>
        </tr>`).join("");
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
    renderUsers();
}


usersBody.addEventListener("click", async (event) => {
    const row = event.target.closest("tr");
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
