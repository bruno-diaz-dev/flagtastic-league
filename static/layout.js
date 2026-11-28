// Shared sidebar behavior applies consistently across every operations page.

const sidebarToggle = document.querySelector("#sidebar-toggle");
// On phones the tab bar's "Más" opens the same menu as a bottom sheet.
const tabbarMore = document.querySelector("#tabbar-more");
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
    tabbarMore?.setAttribute("aria-expanded", String(!isCollapsed));
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
        // Focus returns to whichever control opened the menu and is visible.
        const opener = tabbarMore?.getClientRects().length ? tabbarMore : sidebarToggle;
        if (wasOpen) opener?.focus();
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

tabbarMore?.addEventListener("click", () => {
    setSidebarCollapsed(!document.body.classList.contains("sidebar-collapsed"), true);
});

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
// The phone tab bar marks the same section as the main navigation.
const tabbar = document.querySelector(".tabbar");
if (tabbar) {
    const tabs = [...tabbar.querySelectorAll(".tabbar-link")];
    const activeTab = tabs.filter((tab) => {
        const href = tab.getAttribute("href");
        return pagePath === href || pagePath.startsWith(`${href}/`);
    })[0];
    if (activeTab) activeTab.setAttribute("aria-current", "page");
}

// Full-width page bands size themselves to the viewport minus a classic
// scrollbar, so their content lines up with the page column.
function updateScrollbarWidth() {
    const root = document.documentElement;
    if (!root?.style) return;
    root.style.setProperty("--scrollbar-width", `${Math.max(0, window.innerWidth - root.clientWidth)}px`);
}
updateScrollbarWidth();
window.addEventListener("resize", updateScrollbarWidth);

// Role tools live in a "Más" menu in the desktop top bar.
const navMore = document.querySelector("#nav-more");
const navMoreToggle = document.querySelector("#nav-more-toggle");

function setNavMoreOpen(isOpen) {
    if (!navMore || !navMoreToggle) return;
    navMore.classList.toggle("open", isOpen);
    navMoreToggle.setAttribute("aria-expanded", String(isOpen));
}

function revealNavMore() {
    if (!navMore) return;
    const hasRoleLinks = [...navMore.querySelectorAll(".nav-link")]
        .some((link) => !link.classList.contains("hidden"));
    navMore.classList.toggle("hidden", !hasRoleLinks);
    // Selecting a role page keeps "Más" highlighted in the top bar.
    if (navMore.querySelector('[aria-current="page"]')) {
        navMoreToggle?.classList.add("active");
        tabbarMore?.classList.add("active");
    }
}

if (navMore && navMoreToggle) {
    navMoreToggle.addEventListener("click", () => {
        setNavMoreOpen(!navMore.classList.contains("open"));
    });
    // Close on a click elsewhere, on Escape inside the menu, or when focus leaves it.
    document.addEventListener("click", (event) => {
        if (navMore.classList.contains("open") && !navMore.contains(event.target)) setNavMoreOpen(false);
    });
    navMore.addEventListener("keydown", (event) => {
        if (event.key !== "Escape" || !navMore.classList.contains("open")) return;
        setNavMoreOpen(false);
        navMoreToggle.focus();
    });
    navMore.addEventListener("focusout", (event) => {
        if (event.relatedTarget && !navMore.contains(event.relatedTarget)) setNavMoreOpen(false);
    });
}

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
const adminFinalsEligibilityLink = document.querySelector("#admin-finals-eligibility-link");
const refereeGamesLink = document.querySelector("#referee-games-link");
const refereeRosterLink = document.querySelector("#referee-roster-link");


// One session lookup per page, shared with page scripts so they can skip
// private requests for visitors. Resolves to the user, or null for a visitor.
// A visitor is a normal state: /api/auth/session answers 200 with user null.
if (sessionUser && loginLink && logoutButton) {
    window.flagtasticSession = fetch("/api/auth/session", {cache: "no-store"})
        .then((response) => (response.ok ? response.json() : {user: null}))
        .then((body) => body?.user || null)
        .catch(() => null);
}


async function loadSessionIdentity() {
    if (!sessionUser || !loginLink || !logoutButton) return;

    try {
        const user = await window.flagtasticSession;
        if (!user) return;

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
        if (roles.includes("league_admin") && adminFinalsEligibilityLink) {
            adminFinalsEligibilityLink.classList.remove("hidden");
        }
        if (
            roles.some((role) => ["referee", "league_admin"].includes(role))
            && refereeGamesLink
        ) {
            refereeGamesLink.classList.remove("hidden");
        }
        revealNavMore();
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

