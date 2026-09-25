// League administrators use this controller to grant least-privilege roles.

const usersBody = document.querySelector("#admin-users-body");
const usersMessage = document.querySelector("#admin-users-message");

const roleLabels = {
    player: "Jugador",
    team_representative: "Representante",
    league_admin: "Administrador de liga"
};

function roleOptions(selected) {
    return Object.entries(roleLabels).map(([value, label]) =>
        `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`
    ).join("");
}

async function loadUsers() {
    const response = await getAdminUsers();
    if (response.status === 401) {
        window.location.assign("/login");
        return;
    }
    if (response.status === 403) {
        window.location.assign("/teams");
        return;
    }
    if (!response.ok) {
        usersMessage.textContent = "No se pudieron cargar los usuarios.";
        return;
    }
    const users = await response.json();
    usersBody.innerHTML = users.map((user) => `
        <tr data-user-id="${user.id}">
            <td><strong>${escapeHtml(user.name)}</strong></td>
            <td>${escapeHtml(user.email)}</td>
            <td><select name="role" aria-label="Rol de ${escapeHtml(user.name)}">${roleOptions(user.role)}</select></td>
            <td>${user.status === "active" ? "Activo" : "Inactivo"}</td>
            <td><button class="save-role-button" type="button">Guardar</button></td>
        </tr>`).join("");
}

usersBody.addEventListener("click", async (event) => {
    if (!event.target.classList.contains("save-role-button")) return;
    const row = event.target.closest("tr");
    const role = row.querySelector("[name='role']").value;
    event.target.disabled = true;
    const response = await updateAdminUserRole(row.dataset.userId, role);
    const body = await response.json();
    usersMessage.textContent = response.ok
        ? `Rol de ${body.name} actualizado.`
        : (body.detail || "No se pudo actualizar el rol.");
    event.target.disabled = false;
    if (response.ok) await loadUsers();
});

loadUsers().catch(() => {
    usersMessage.textContent = "No se pudo conectar con el servidor.";
});
