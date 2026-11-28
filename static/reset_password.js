// Consume the token from the URL without persisting it in browser storage.
// New links carry it in the fragment (#token=...), which browsers never send
// to the server, so it stays out of request logs; older links used ?token=.

const resetPasswordForm = document.querySelector("#reset-password-form");
const resetPasswordMessage = document.querySelector("#reset-password-message");
const resetToken = (
    new URLSearchParams(window.location.hash.slice(1)).get("token")
    || new URLSearchParams(window.location.search).get("token")
);
if (resetToken) {
    // Keep the token out of the address bar and browser history.
    window.history.replaceState(null, "", window.location.pathname);
}

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
