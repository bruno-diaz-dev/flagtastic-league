// Password reset requests always display the same account-neutral response.

const forgotPasswordForm = document.querySelector("#forgot-password-form");
const forgotPasswordMessage = document.querySelector("#forgot-password-message");

forgotPasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = new FormData(forgotPasswordForm).get("email");
    forgotPasswordMessage.textContent = "Enviando solicitud...";
    try {
        const response = await requestPasswordReset(email);
        const body = await response.json();
        forgotPasswordMessage.textContent = response.ok
            ? body.message
            : "No se pudo procesar la solicitud.";
        if (response.ok) forgotPasswordForm.reset();
    } catch (error) {
        forgotPasswordMessage.textContent = "No se pudo conectar con el servidor.";
    }
});
