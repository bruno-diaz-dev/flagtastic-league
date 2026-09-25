// Public leaderboard controller. Totals are calculated by the backend.

const leaderboardForm = document.querySelector("#leaderboard-form");
const leaderboardsContainer = document.querySelector("#leaderboards");
const statisticsImportForm = document.querySelector("#statistics-import-form");
const statisticsImportMessage = document.querySelector("#statistics-import-message");

const leaderboardDefinitions = {
    completion_percentage: {
        title: "El Francotirador",
        statistic: "Porcentaje de pases completos"
    },
    receptions: {title: "Manos de Acero", statistic: "Recepciones"},
    points: {title: "Máquina de Puntos", statistic: "Puntos"},
    tackles: {title: "El Muro", statistic: "Tacleadas"},
    interceptions: {title: "Cazador Aéreo", statistic: "Intercepciones"},
    sacks: {title: "Cazador de QBs", statistic: "Capturas"}
};


function leaderboardIdentity(leader) {
    const displayName = leader.player_aka || leader.player_name;
    const photo = leader.profile_photo_url
        ? `<img class="leaderboard-photo" src="${escapeHtml(leader.profile_photo_url)}" alt="Foto de ${escapeHtml(displayName)}">`
        : `<span class="leaderboard-photo profile-placeholder" aria-hidden="true">${escapeHtml(leader.player_name.charAt(0))}</span>`;
    const legalName = leader.player_aka
        ? `<small>${escapeHtml(leader.player_name)}</small>`
        : "";
    return `
        <div class="leaderboard-player">
            ${photo}
            <div>
                <strong>${escapeHtml(displayName)}</strong>
                ${legalName}
                <span>#${leader.jersey_number} · ${escapeHtml(leader.team_name)}</span>
            </div>
        </div>`;
}


function renderLeaderboards(leaderboards) {
    leaderboardsContainer.innerHTML = Object.entries(leaderboardDefinitions)
        .map(([metric, definition]) => {
            const leaders = leaderboards[metric];
            const rows = leaders.length
                ? leaders.map((leader, index) => `
                    <tr>
                        <td class="rank-cell">${index + 1}</td>
                        <td>${leaderboardIdentity(leader)}</td>
                        <td class="stat-value">${
                            metric === "completion_percentage"
                                ? `${leader.value}% (${leader.passes_completed}/${leader.passes_attempted})`
                                : leader.value
                        }</td>
                    </tr>
                `).join("")
                : `<tr><td colspan="3">Sin estadísticas registradas.</td></tr>`;

            return `
                <section class="leaderboard-panel">
                    <h3>${definition.title}</h3>
                    <p class="leaderboard-statistic">${definition.statistic}</p>
                    <table class="leaderboard-table">
                        <thead><tr><th>Pos.</th><th>Jugador</th><th>${metric === "completion_percentage" ? "% (C/I)" : "Total"}</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </section>
            `;
        })
        .join("");
}


async function submitStatisticsImport(event) {
    event.preventDefault();
    const fields = new FormData(statisticsImportForm);
    statisticsImportMessage.textContent = "Importando estadísticas...";
    try {
        const response = await importOfficialStatistics(fields.get("file"));
        const data = await response.json();
        if (!response.ok) {
            statisticsImportMessage.textContent = data.detail || "No se pudo importar el archivo.";
            return;
        }
        statisticsImportForm.reset();
        statisticsImportMessage.textContent = `${data.imported} registros de ${data.weeks.length} jornadas importados correctamente.`;
        await loadLeaderboards();
    } catch (error) {
        statisticsImportMessage.textContent = "No se pudo conectar con el servidor.";
    }
}


async function loadLeaderboards(event) {
    if (event) event.preventDefault();
    const formData = new FormData(leaderboardForm);
    leaderboardsContainer.innerHTML = "<p>Cargando estadísticas...</p>";

    try {
        const response = await getLeaderboards(
            formData.get("branch"),
            formData.get("category")
        );
        if (!response.ok) throw new Error("Request failed");
        renderLeaderboards(await response.json());
    } catch (error) {
        leaderboardsContainer.innerHTML = "<p>No se pudieron cargar las estadísticas.</p>";
    }
}


leaderboardForm.addEventListener("submit", loadLeaderboards);
if (statisticsImportForm) {
    statisticsImportForm.addEventListener("submit", submitStatisticsImport);
}
loadLeaderboards();
