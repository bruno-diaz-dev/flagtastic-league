// Shared sidebar behavior applies consistently across every operations page.

const sidebarToggle = document.querySelector("#sidebar-toggle");

if (sidebarToggle !== null) {
    sidebarToggle.addEventListener("click", () => {
        const isCollapsed = document.body.classList.toggle("sidebar-collapsed");

        sidebarToggle.setAttribute("aria-expanded", String(!isCollapsed));
        sidebarToggle.setAttribute(
            "aria-label",
            isCollapsed ? "Expandir menu" : "Contraer menu"
        );
    });
}

const sessionUser = document.querySelector("#session-user");
const loginLink = document.querySelector("#login-link");
const logoutButton = document.querySelector("#logout-button");
const dashboardLink = document.querySelector("#dashboard-link");
const adminUsersLink = document.querySelector("#admin-users-link");


async function loadSessionIdentity() {
    if (!sessionUser || !loginLink || !logoutButton) return;

    try {
        const response = await fetch("/api/auth/me");
        if (!response.ok) return;

        const user = await response.json();
        document.body.classList.add(`role-${user.role}`);
        sessionUser.textContent = user.name;
        loginLink.classList.add("hidden");
        logoutButton.classList.remove("hidden");
        if (user.role === "player" && dashboardLink) {
            dashboardLink.classList.remove("hidden");
        }
        if (user.role === "league_admin" && adminUsersLink) {
            adminUsersLink.classList.remove("hidden");
        }
    } catch (error) {
        // Public navigation remains available when the session check fails.
    }
}


if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
        await fetch("/api/auth/logout", {method: "POST"});
        window.location.assign("/login");
    });
}

loadSessionIdentity();
