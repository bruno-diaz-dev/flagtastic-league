// Standings page controller: division selection and table rendering.

const standingsForm = document.querySelector("#standings-form");
const standingsFormMessage = document.querySelector("#standings-form-message");
const standingsContainer = document.querySelector("#standings");
const standingsBranch = document.querySelector("#standings-branch");
const standingsCategory = document.querySelector("#standings-category");
const youthStandingsRule = document.querySelector("#youth-standings-rule");
const standingsBranchField = document.querySelector("#standings-branch-field");
const standingsYouthBranch = document.querySelector("#standings-youth-branch");
const unifiedYouthCategories = new Set(["u8", "u10", "u12"]);

function updateDivisionControls() {
    const unified = unifiedYouthCategories.has(standingsCategory.value);
    standingsBranch.disabled = unified;
    standingsBranch.required = !unified;
    if (unified) standingsBranch.value = "mixto";
    standingsBranchField.classList.toggle("hidden", unified);
    standingsYouthBranch.classList.toggle("hidden", !unified);
    youthStandingsRule.classList.toggle("hidden", !unified);
}

async function loadStandings(event) {
    event.preventDefault();

    const formData = new FormData(standingsForm);
    const category = formData.get("category");
    const branch = unifiedYouthCategories.has(category)
        ? "mixto"
        : formData.get("branch");

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
                    <th scope="col">Posición / Equipo</th>
                    <th>G</th>
                    <th>P</th>
                    <th>PF</th>
                    <th>PC</th>
                    <th>DIF</th>
                </tr>
            </thead>
            <tbody>
                ${standings
                    .map((team, index) => `
                        <tr>
                            <td>
                                <a class="standings-team team-roster-link" href="/teams/${team.team_id}/roster">
                                    <span class="standings-position" aria-label="Posición ${index + 1}">${index + 1}</span>
                                    ${team.team_logo_url ? `<img class="team-logo team-logo-small" src="${team.team_logo_url}" alt="" loading="lazy" decoding="async">` : ""}
                                    <span class="standings-team-name">${escapeHtml(team.team_name)}</span>
                                </a>
                            </td>
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
    standingsCategory.addEventListener("change", updateDivisionControls);
    updateDivisionControls();
}
