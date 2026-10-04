// Shared sidebar behavior applies consistently across every operations page.

const sidebarToggle = document.querySelector("#sidebar-toggle");
const sidebarBackdrop = document.querySelector("#sidebar-backdrop");
const SIDEBAR_STORAGE_KEY = "flagtastic-sidebar-collapsed";
const MOBILE_BREAKPOINT = 820;


function setSidebarCollapsed(isCollapsed, remember = false) {
    document.body.classList.toggle("sidebar-collapsed", isCollapsed);
    sidebarToggle?.setAttribute("aria-expanded", String(!isCollapsed));
    sidebarToggle?.setAttribute(
        "aria-label",
        isCollapsed ? "Expandir menu" : "Contraer menu"
    );
    if (remember) {
        try {
            localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isCollapsed));
        } catch (error) {
            // Navigation also works when browser storage is unavailable.
        }
    }
}


function closeMobileSidebar() {
    if (window.innerWidth <= MOBILE_BREAKPOINT) {
        const wasOpen = !document.body.classList.contains("sidebar-collapsed");
        setSidebarCollapsed(true, true);
        if (wasOpen) sidebarToggle?.focus();
    }
}


// Keep mobile browsing unobstructed and desktop navigation discoverable.
let savedSidebarState = null;
try {
    savedSidebarState = localStorage.getItem(SIDEBAR_STORAGE_KEY);
} catch (error) {
    // Use responsive defaults when storage is blocked.
}
const startsCollapsed = window.innerWidth <= MOBILE_BREAKPOINT
    ? true
    : savedSidebarState === "true";
setSidebarCollapsed(startsCollapsed);

if (sidebarToggle !== null) {
    sidebarToggle.addEventListener("click", () => {
        setSidebarCollapsed(
            !document.body.classList.contains("sidebar-collapsed"),
            true
        );
    });
}


// Mobile navigation behaves as a modal drawer and never obscures the selected page.
sidebarBackdrop?.addEventListener("click", closeMobileSidebar);
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMobileSidebar();
    if (event.key !== "Tab" || window.innerWidth > MOBILE_BREAKPOINT
        || document.body.classList.contains("sidebar-collapsed")) return;
    const controls = [...document.querySelectorAll('.sidebar button, .sidebar a[href]')]
        .filter((control) => !control.disabled && control.getClientRects().length);
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (!first) return;
    if (!controls.includes(document.activeElement)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
    } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
});
document.querySelectorAll(".navigation .nav-link").forEach((link) => {
    link.addEventListener("click", closeMobileSidebar);
});

window.addEventListener("resize", () => {
    if (window.innerWidth <= MOBILE_BREAKPOINT) closeMobileSidebar();
});

// Parent sections stay selected when opening a roster, game, or profile.
const navigationLinks = [...document.querySelectorAll(".navigation .nav-link")];
const pagePath = window.location.pathname.replace(/\/$/, "") || "/";
const activeNavigation = navigationLinks.filter((link) => {
    const href = link.getAttribute("href");
    return pagePath === href || pagePath.startsWith(`${href}/`);
}).sort((a, b) => b.getAttribute("href").length - a.getAttribute("href").length)[0];
navigationLinks.forEach((link) => {
    const label = link.querySelector(".nav-text")?.textContent.trim();
    if (label) {
        link.setAttribute("aria-label", label);
        link.setAttribute("title", label);
    }
    if (link === activeNavigation) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
    }
});
const pageHeading = document.querySelector(".content h2")?.textContent.trim();
const mobilePageLabel = document.querySelector("#current-page-label");
if (mobilePageLabel) mobilePageLabel.textContent = pageHeading || "La liga";
if (pageHeading) document.title = `${pageHeading} | FlagTastic`;

// Reveal a collapsed action before focusing a field with a validation error.
document.addEventListener("invalid", (event) => {
    let disclosure = event.target.closest("details");
    while (disclosure) {
        disclosure.open = true;
        disclosure = disclosure.parentElement.closest("details");
    }
}, true);

const sessionUser = document.querySelector("#session-user");
const loginLink = document.querySelector("#login-link");
const logoutButton = document.querySelector("#logout-button");
const dashboardLink = document.querySelector("#dashboard-link");
const representativeDashboardLink = document.querySelector("#representative-dashboard-link");
const adminUsersLink = document.querySelector("#admin-users-link");
const adminTeamAuditLink = document.querySelector("#admin-team-audit-link");
const refereeGamesLink = document.querySelector("#referee-games-link");
const refereeRosterLink = document.querySelector("#referee-roster-link");


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
        refereeRosterLink?.classList.remove("hidden");
        if (roles.includes("player") && dashboardLink) {
            dashboardLink.classList.remove("hidden");
        }
        if (roles.includes("team_representative") && representativeDashboardLink) {
            representativeDashboardLink.classList.remove("hidden");
        }
        if (roles.includes("league_admin") && adminUsersLink) {
            adminUsersLink.classList.remove("hidden");
        }
        if (roles.includes("league_admin") && adminTeamAuditLink) {
            adminTeamAuditLink.classList.remove("hidden");
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
