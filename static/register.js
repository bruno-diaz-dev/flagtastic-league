// Public player registration controller; credentials are sent only to the API.

const registerForm = document.querySelector("#register-form");
const registerMessage = document.querySelector("#register-message");

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(registerForm);
    registerMessage.textContent = "Creando cuenta...";

    try {
        const response = await registerPlayerAccount(fields);
        if (!response.ok) {
            let detail = "No se pudo crear la cuenta.";
            if (response.headers.get("content-type")?.includes("application/json")) {
                const error = await response.json();
                detail = error.detail || detail;
            } else if (response.status >= 500) {
                detail = "Ocurrió un error interno. Revisa las migraciones del servidor.";
            }
            registerMessage.textContent = detail;
            return;
        }
        window.location.assign("/login");
    } catch (error) {
        registerMessage.textContent = "No se pudo conectar con el servidor.";
    }
});
