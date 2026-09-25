// Shared sidebar behavior applies consistently across every operations page.

const sidebarToggle = document.querySelector("#sidebar-toggle");
const SIDEBAR_STORAGE_KEY = "flagtastic-sidebar-collapsed";


function setSidebarCollapsed(isCollapsed, remember = false) {
    document.body.classList.toggle("sidebar-collapsed", isCollapsed);
    sidebarToggle?.setAttribute("aria-expanded", String(!isCollapsed));
    sidebarToggle?.setAttribute(
        "aria-label",
        isCollapsed ? "Expandir menu" : "Contraer menu"
    );
    if (remember) {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isCollapsed));
    }
}


// The menu is closed by default and keeps the user's explicit choice.
const savedSidebarState = localStorage.getItem(SIDEBAR_STORAGE_KEY);
setSidebarCollapsed(savedSidebarState === null ? true : savedSidebarState === "true");

if (sidebarToggle !== null) {
    sidebarToggle.addEventListener("click", () => {
        setSidebarCollapsed(
            !document.body.classList.contains("sidebar-collapsed"),
            true
        );
    });
}

const sessionUser = document.querySelector("#session-user");
const loginLink = document.querySelector("#login-link");
const logoutButton = document.querySelector("#logout-button");
const dashboardLink = document.querySelector("#dashboard-link");
const adminUsersLink = document.querySelector("#admin-users-link");
const refereeGamesLink = document.querySelector("#referee-games-link");


async function loadSessionIdentity() {
    if (!sessionUser || !loginLink || !logoutButton) return;

    try {
        const response = await fetch("/api/auth/me");
        if (!response.ok) return;

        const user = await response.json();
        const roles = user.roles || [user.role];
        roles.forEach((role) => document.body.classList.add(`role-${role}`));
        sessionUser.textContent = user.display_name || user.name;
        loginLink.classList.add("hidden");
        logoutButton.classList.remove("hidden");
        if (roles.includes("player") && dashboardLink) {
            dashboardLink.classList.remove("hidden");
        }
        if (roles.includes("league_admin") && adminUsersLink) {
            adminUsersLink.classList.remove("hidden");
        }
        if (
            roles.some((role) => ["referee", "league_admin"].includes(role))
            && refereeGamesLink
        ) {
            refereeGamesLink.classList.remove("hidden");
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
