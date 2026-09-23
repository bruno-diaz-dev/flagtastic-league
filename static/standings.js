// Standings page controller: division selection and table rendering.

const standingsForm = document.querySelector("#standings-form");
const standingsFormMessage = document.querySelector("#standings-form-message");
const standingsContainer = document.querySelector("#standings");

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
        <table class="standings-data-table">
            <thead>
                <tr>
                    <th>Equipo</th>
                    <th>G</th>
                    <th>P</th>
                    <th>PF</th>
                    <th>PC</th>
                    <th>DIF</th>
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
