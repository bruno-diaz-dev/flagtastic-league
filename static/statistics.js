// Public leaderboard controller. Totals are calculated by the backend.

const leaderboardForm = document.querySelector("#leaderboard-form");
const leaderboardsContainer = document.querySelector("#leaderboards");

const metricLabels = {
    touchdowns: "Touchdowns",
    interceptions: "Intercepciones",
    sacks: "Capturas",
    flag_pulls: "Tackleos"
};


function renderLeaderboards(leaderboards) {
    leaderboardsContainer.innerHTML = Object.entries(metricLabels)
        .map(([metric, label]) => {
            const leaders = leaderboards[metric];
            const rows = leaders.length
                ? leaders.map((leader, index) => `
                    <tr>
                        <td class="rank-cell">${index + 1}</td>
                        <td>
                            <strong>${leader.player_name}</strong>
                            <span>#${leader.jersey_number} · ${leader.team_name}</span>
                        </td>
                        <td class="stat-value">${leader.value}</td>
                    </tr>
                `).join("")
                : `<tr><td colspan="3">Sin estadísticas registradas.</td></tr>`;

            return `
                <section class="leaderboard-panel">
                    <h3>${label}</h3>
                    <table class="leaderboard-table">
                        <thead><tr><th>Pos.</th><th>Jugador</th><th>Total</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </section>
            `;
        })
        .join("");
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
loadLeaderboards();
