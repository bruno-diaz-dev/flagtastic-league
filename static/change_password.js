// Mandatory first-login password replacement for administrator-created users.

const passwordForm = document.querySelector("#change-password-form");
const passwordMessage = document.querySelector("#change-password-message");

passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(passwordForm);
    if (data.get("new_password") !== data.get("confirmation")) {
        passwordMessage.textContent = "Las contraseñas nuevas no coinciden.";
        return;
    }
    const response = await changePassword({
        current_password: data.get("current_password"),
        new_password: data.get("new_password")
    });
    if (!response.ok) {
        const body = await response.json();
        passwordMessage.textContent = body.detail || "No se pudo cambiar la contraseña.";
        return;
    }
    window.location.assign("/teams");
});
