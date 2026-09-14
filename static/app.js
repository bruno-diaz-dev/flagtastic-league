const navLinks = document.querySelectorAll("[data-view]");
const views = document.querySelectorAll(".view");

const homeTeamSelect = document.querySelector("[name='home_team_id']");
const awayTeamSelect = document.querySelector("[name='away_team_id']");

const standingsForm = document.querySelector("#standings-form");
const standingsFormMessage = document.querySelector("#standings-form-message");
const standingsContainer = document.querySelector("#standings");

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


async function loadStandings(event) {
    event.preventDefault();

    const formData = new FormData(standingsForm);
    const branch = formData.get("branch");
    const category = formData.get("category");

    standingsFormMessage.textContent = "Consultando tabla...";

    try {
        const response = await getStandings(branch, category);

        if (!response.ok) {
            standingsFormMessage.textContent = "No se pudo consultar la tabla.";
            return;
        }

        const standings = await response.json();

        standingsFormMessage.textContent = "";
        renderStandings(standings);
    } catch (error) {
        standingsFormMessage.textContent = "No se pudo conectar con el servidor.";
    }
}

function renderStandings(standings) {
    if (standings.length === 0) {
        standingsContainer.innerHTML = `
            <div class="empty-state">
                <h3>Sin resultados</h3>
                <p>No hay partidos con marcador para esta rama y categoría.</p>
            </div>
        `;
        return;
    }

    standingsContainer.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Equipo</th>
                    <th>G</th>
                    <th>P</th>
                    <th>PF</th>
                    <th>PC</th>
                    <th>Dif</th>
                </tr>
            </thead>
            <tbody>
                ${standings
                    .map((team) => `
                        <tr>
                            <td>${team.team_name}</td>
                            <td>${team.wins}</td>
                            <td>${team.losses}</td>
                            <td>${team.points_for}</td>
                            <td>${team.points_against}</td>
                            <td>${team.point_difference}</td>
                        </tr>
                    `)
                    .join("")}
            </tbody>
        </table>
    `;
}

if (standingsForm !== null) {
    standingsForm.addEventListener("submit", loadStandings);
}

navLinks.forEach((link) => {
    link.addEventListener("click", () => {
        showView(link.dataset.view);
    });
});

loadTeams();