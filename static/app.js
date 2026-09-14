const navLinks = document.querySelectorAll("[data-view]");
const views = document.querySelectorAll(".view");

const homeTeamSelect = document.querySelector("[name='home_team_id']");
const awayTeamSelect = document.querySelector("[name='away_team_id']");

function showView(viewName) {
    views.forEach((view) => {
        view.classList.toggle("active-view", view.id === `${viewName}-view`);
    });

    navLinks.forEach((link) => {
        link.classList.toggle("active", link.dataset.view === viewName);
    });

    if (viewName === "games") {
        loadGames();
    }
}

navLinks.forEach((link) => {
    link.addEventListener("click", () => {
        showView(link.dataset.view);
    });
});

loadTeams();