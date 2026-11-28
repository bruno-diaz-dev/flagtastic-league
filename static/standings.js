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

    standingsFormMessage.textContent = "";
    if (typeof skeletonMarkup === "function") standingsContainer.innerHTML = skeletonMarkup("table", 8, "Consultando la tabla");

    try {
        const response = await getStandings(branch, category);

        if (!response.ok) {
            standingsFormMessage.textContent = "No se pudo consultar la tabla.";
            return;
        }

        const standings = await response.json();

        standingsFormMessage.textContent = "";
        renderStandings(standings);
        updateStandingsHero(branch, category, standings);
    } catch (error) {
        standingsFormMessage.textContent = "No se pudo conectar con el servidor.";
    }
}

// The band names the division on screen and sums it up.
function updateStandingsHero(branch, category, standings) {
    if (typeof setPageHero !== "function") return;
    const division = `${unifiedYouthCategories.has(category) ? "Infantiles" : displayName(branch)} · ${displayName(category)}`;
    const played = standings.reduce((total, team) => total + (team.games_played || 0), 0) / 2;
    setPageHero({
        tags: [{label: division, tone: "gold"}, ...(standings[0] ? [{label: `Líder: ${displayName(standings[0].team_name)}`}] : [])],
        stats: standings.length ? [[standings.length, "Equipos"], [Math.round(played), "Partidos jugados"]] : [],
    });
}

function renderStandings(standings) {
    if (standings.length === 0) {
        const title = "La tabla aún no arranca";
        const text = "No hay partidos con marcador en esta rama y categoría. En cuanto se jueguen, aquí verás quién manda.";
        standingsContainer.innerHTML = typeof emptyStateMarkup === "function"
            ? emptyStateMarkup({icon: "trophy", title, text, action: {label: "Ver calendario", href: "/games"}})
            : `<div class="empty-state"><h3>${title}</h3><p>${text}</p></div>`;
        return;
    }

    standingsContainer.innerHTML = `
        <table class="standings-data-table">
            <thead>
                <tr>
                    <th scope="col">Posición / Equipo</th>
                    <th scope="col" title="Juegos jugados" aria-label="Juegos jugados">JJ</th>
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
                                    <span class="standings-team-name">${escapeHtml(displayName(team.team_name))}</span>
                                </a>
                            </td>
                            <td>${team.games_played}</td>
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

// Opening the page shows a table straight away (Varonil · Libre) instead of
// an empty form; any other division is one selection away.
function loadDefaultStandings() {
    const hasOption = (select, value) => [...select.options].some((option) => option.value === value);
    if (standingsBranch.value || standingsCategory.value) return;
    if (!hasOption(standingsBranch, "varonil") || !hasOption(standingsCategory, "libre")) return;
    standingsBranch.value = "varonil";
    standingsCategory.value = "libre";
    updateDivisionControls();
    loadStandings(new Event("submit"));
}

if (standingsForm !== null) {
    standingsForm.addEventListener("submit", loadStandings);
    standingsCategory.addEventListener("change", updateDivisionControls);
    updateDivisionControls();
    loadDefaultStandings();
}
