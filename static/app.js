const navLinks = document.querySelectorAll("[data-view]");
const views = document.querySelectorAll(".view");
const sidebarToggle = document.querySelector("#sidebar-toggle");

const homeTeamSelect = document.querySelector("[name='home_team_id']");
const awayTeamSelect = document.querySelector("[name='away_team_id']");

function showView(viewName) {
    views.forEach((view) => {
        view.classList.toggle("active-view", view.id === `${viewName}-view`);
    });

    navLinks.forEach((link) => {
        link.classList.toggle("active", link.dataset.view === viewName);
    });

    window.location.hash = viewName;

    if (viewName === "games") {
        loadGames();
    }
}

navLinks.forEach((link) => {
    link.addEventListener("click", () => {
        showView(link.dataset.view);
    });
});

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

loadTeams();

const initialView = window.location.hash.replace("#", "") || "teams";
showView(initialView);
