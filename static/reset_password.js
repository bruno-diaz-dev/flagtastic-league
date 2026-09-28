// Consume the token from the URL without persisting it in browser storage.

const resetPasswordForm = document.querySelector("#reset-password-form");
const resetPasswordMessage = document.querySelector("#reset-password-message");
const resetToken = new URLSearchParams(window.location.search).get("token");

if (!resetToken) {
    resetPasswordMessage.textContent = "El enlace no es válido.";
    resetPasswordForm.classList.add("hidden");
}

resetPasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(resetPasswordForm);
    if (data.get("new_password") !== data.get("confirmation")) {
        resetPasswordMessage.textContent = "Las contraseñas no coinciden.";
        return;
    }
    const response = await resetPassword(resetToken, data.get("new_password"));
    if (!response.ok) {
        const body = await response.json();
        resetPasswordMessage.textContent = body.detail || "No se pudo cambiar la contraseña.";
        return;
    }
    resetPasswordMessage.textContent = "Contraseña actualizada. Redirigiendo...";
    window.setTimeout(() => window.location.assign("/login"), 800);
});
