// League administrators grant cumulative least-privilege roles here.

const usersBody = document.querySelector("#admin-users-body");
const usersMessage = document.querySelector("#admin-users-message");
const staffForm = document.querySelector("#staff-account-form");
const staffMessage = document.querySelector("#staff-account-message");

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


async function loadUsers() {
    const response = await getAdminUsers();
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 403) return window.location.assign("/teams");
    if (!response.ok) {
        usersMessage.textContent = "No se pudieron cargar los usuarios.";
        return;
    }
    const users = await response.json();
    usersBody.innerHTML = users.map((user) => `
        <tr data-user-id="${user.id}">
            <td><strong>${escapeHtml(user.display_name || user.name)}</strong>${user.aka ? `<small>Nombre legal: ${escapeHtml(user.name)}</small>` : ""}</td>
            <td>${escapeHtml(user.email)}</td>
            <td><div class="role-choices">${roleChoices(user.roles || [user.role])}</div></td>
            <td>${user.status === "active" ? "Activo" : "Inactivo"}</td>
            <td><button class="save-role-button" type="button">Guardar</button></td>
        </tr>`).join("");
}


usersBody.addEventListener("click", async (event) => {
    if (!event.target.classList.contains("save-role-button")) return;
    const row = event.target.closest("tr");
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


loadUsers().catch(() => {
    usersMessage.textContent = "No se pudo conectar con el servidor.";
});
