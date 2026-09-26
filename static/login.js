// Login page controller. The session token remains inaccessible to JavaScript.

const loginForm = document.querySelector("#login-form");
const loginMessage = document.querySelector("#login-message");


loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    loginMessage.textContent = "Verificando credenciales...";

    try {
        const response = await login({
            email: formData.get("email"),
            password: formData.get("password")
        });

        if (!response.ok) {
            loginMessage.textContent = "Correo o contraseña incorrectos.";
            return;
        }

        const user = await response.json();
        if (user.must_change_password) {
            window.location.assign("/change-password");
            return;
        }
        const roles = user.roles || [user.role];
        const destination = roles.includes("player")
            ? "/dashboard"
            : roles.includes("team_representative")
                ? "/representative-dashboard"
                : "/teams";
        window.location.assign(destination);
    } catch (error) {
        loginMessage.textContent = "No se pudo conectar con el servidor.";
    }
});
