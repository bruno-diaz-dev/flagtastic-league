// Public leaderboard controller. Totals are calculated by the backend.

const leaderboardForm = document.querySelector("#leaderboard-form");
const leaderboardsContainer = document.querySelector("#leaderboards");
const statisticsImportForm = document.querySelector("#statistics-import-form");
const statisticsImportMessage = document.querySelector("#statistics-import-message");
const statisticsImportSkipped = document.querySelector("#statistics-import-skipped");
const statisticsImportMode = document.querySelector("#statistics-import-mode");
const statisticsDivisionFields = document.querySelector("#statistics-division-fields");
const statisticsAllFields = document.querySelector("#statistics-all-fields");
const statisticsWeekInput = document.querySelector("#statistics-import-week");
const statisticsBranchInput = document.querySelector("#statistics-import-branch");
const statisticsCategoryInput = document.querySelector("#statistics-import-category");
const statisticsAllWeekInput = document.querySelector("#statistics-import-all-week");

const leaderboardBranch = document.querySelector("#leaderboard-branch");
const leaderboardCategory = document.querySelector("#leaderboard-category");
const leaderboardBranchField = document.querySelector("#leaderboard-branch-field");
const leaderboardYouthBranch = document.querySelector("#leaderboard-youth-branch");

const leaderboardDefinitions = {
    completion_percentage: {
        title: "El Francotirador",
        statistic: "Porcentaje de pases completos · mínimo 15 intentos totales (completos + incompletos)"
    },
    receptions: {title: "Manos de Acero", statistic: "Recepciones"},
    points: {title: "Máquina de Puntos", statistic: "Puntos"},
    tackles: {title: "El Muro", statistic: "Tacleadas"},
    interceptions: {title: "Cazador Aéreo", statistic: "Intercepciones"},
    sacks: {title: "Cazador de QBs", statistic: "Capturas"}
};

function updateLeaderboardBranchControl() {
    const unified = isUnifiedYouthCategory(leaderboardCategory.value);
    leaderboardBranchField.classList.toggle("hidden", unified);
    leaderboardYouthBranch.classList.toggle("hidden", !unified);
    leaderboardBranch.disabled = unified;
    if (unified) leaderboardBranch.value = "mixto";
}


function leaderboardIdentity(leader) {
    const displayName = leader.player_aka || leader.player_name;
    const photo = leader.profile_photo_url
        ? `<img class="leaderboard-photo" src="${escapeHtml(leader.profile_photo_url)}" alt="Foto de ${escapeHtml(displayName)}" loading="lazy" decoding="async">`
        : `<span class="leaderboard-photo profile-placeholder" aria-hidden="true">${escapeHtml(leader.player_name.charAt(0))}</span>`;
    const legalName = leader.player_aka
        ? `<small>${escapeHtml(leader.player_name)}</small>`
        : "";
    return `
        <div class="leaderboard-identity">
            <a class="leaderboard-player player-profile-link" href="/players/${leader.player_id}">
                ${photo}
                <div>
                    <strong>${escapeHtml(displayName)}</strong>
                    ${legalName}
                </div>
            </a>
            <span class="leaderboard-team">
                #${leader.jersey_number} ·
                <a class="team-roster-link" href="/teams/${leader.team_id}/roster">${escapeHtml(leader.team_name)}</a>
            </span>
        </div>`;
}


function renderLeaderboards(leaderboards) {
    leaderboardsContainer.innerHTML = Object.entries(leaderboardDefinitions)
        .map(([metric, definition]) => {
            const leaders = leaderboards[metric];
            const rows = leaders.length
                ? leaders.map((leader, index) => `
                    <tr>
                        <td class="rank-cell">${leader.rank ?? index + 1}</td>
                        <td>${leaderboardIdentity(leader)}</td>
                        <td class="stat-value">${
                            metric === "completion_percentage"
                                ? `<strong>${leader.value}%</strong><small class="leaderboard-pass-detail">${leader.passes_completed}/${leader.passes_attempted} C/I</small>`
                                : `<strong>${leader.value}</strong>`
                        }</td>
                    </tr>
                `).join("")
                : `<tr><td colspan="3">${metric === "completion_percentage"
                    ? `Sin pasadores con ${leaderboards.passing_qualification?.minimum_attempts ?? 15} intentos acumulados.`
                    : "Sin estadísticas registradas."}</td></tr>`;

            return `
                <section class="leaderboard-panel">
                    <p class="form-help">${escapeHtml(leaderboards.tie_breakers?.[metric] || "")}</p>
                    <h3>${definition.title}</h3>
                    <p class="leaderboard-statistic">${definition.statistic}</p>
                    <table class="leaderboard-table">
                        <colgroup><col class="leaderboard-rank-column"><col><col class="leaderboard-total-column"></colgroup>
                        <thead><tr><th>Pos.</th><th>Jugador</th><th>${metric === "completion_percentage" ? "% (C/I)" : "Total"}</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </section>
            `;
        })
        .join("");
}


function renderSkippedStatistics(data) {
    statisticsImportSkipped.replaceChildren();
    const skipped = data.skipped || [];
    const warnings = data.warnings || [];
    if (warnings.length) {
        const heading = document.createElement("p");
        heading.textContent = `${warnings.length} advertencia(s): pases inconsistentes omitidos. No se inventaron intentos; si había pases publicados, se conservaron.`;
        const list = document.createElement("ul");
        for (const warning of warnings) {
            const item = document.createElement("li");
            item.textContent = `${warning.sheet}, bloque desde fila ${warning.row} · Jornada ${warning.week} · ${warning.team_name} (${warning.branch} / ${warning.category}) · #${warning.jersey_number}: ${warning.source_completed} completos y ${warning.source_attempted} intentos en el archivo. Se procesaron las demás estadísticas válidas.`;
            list.append(item);
        }
        statisticsImportSkipped.append(heading, list);
    }
    if (!skipped.length) return;
    const heading = document.createElement("p");
    heading.textContent = `${skipped.length} registros omitidos: número no registrado en el equipo.`;
    const list = document.createElement("ul");
    const identities = new Set();
    for (const row of skipped) {
        const identity = JSON.stringify([row.week, row.team_id, row.jersey_number]);
        if (identities.has(identity)) continue;
        identities.add(identity);
        const item = document.createElement("li");
        item.textContent = `Jornada ${row.week} · ${row.team_name} (${row.branch} / ${row.category}) · #${row.jersey_number}`;
        list.append(item);
    }
    statisticsImportSkipped.append(heading, list);
    if (data.preserved_weeks?.length) {
        const notice = document.createElement("p");
        notice.textContent = `Sin registros válidos en las jornadas ${data.preserved_weeks.join(", ")}. Se conservaron sus datos anteriores.`;
        statisticsImportSkipped.append(notice);
    }
}


function updateStatisticsImportMode() {
    const singleDivision = statisticsImportMode.value === "division";
    statisticsDivisionFields.hidden = !singleDivision;
    statisticsAllFields.hidden = singleDivision;
    for (const input of [statisticsWeekInput, statisticsBranchInput, statisticsCategoryInput]) {
        input.disabled = !singleDivision;
    }
    statisticsAllWeekInput.disabled = singleDivision;
}

async function submitStatisticsImport(event) {
    event.preventDefault();
    const fields = new FormData(statisticsImportForm);
    const existingRecords = fields.get("existing_records") || "preserve";
    const submit = statisticsImportForm.querySelector('button[type="submit"]');
    if (submit.disabled) return;
    submit.disabled = true;
    statisticsImportSkipped.replaceChildren();
    statisticsImportMessage.textContent = "Preparando archivo...";
    let stage = "prepare";
    try {
        const file = await prepareStatisticsUpload(fields.get("file"));
        stage = "send";
        statisticsImportMessage.textContent = "Importando estadísticas...";
        const mode = statisticsImportMode.value;
        let response;
        if (mode === "division") {
            response = await importDivisionStatistics(
                Number(statisticsWeekInput.value),
                statisticsBranchInput.value,
                statisticsCategoryInput.value,
                file, existingRecords
            );
        } else if (statisticsAllWeekInput.value) {
            response = await importWeekStatistics(Number(statisticsAllWeekInput.value), file, existingRecords);
        } else {
            response = await importOfficialStatistics(file, existingRecords);
        }
        stage = "response";
        const data = await readStatisticsImportResponse(response);
        statisticsImportForm.reset();
        updateStatisticsImportMode();
        statisticsImportMessage.textContent = `${data.imported} registros procesados (${data.created ?? "?"} nuevos, ${data.updated ?? "?"} actualizados, ${data.retained_count || 0} existentes conservados) en ${data.weeks?.length ?? 1} jornada(s).`;
        renderSkippedStatistics(data);
        await loadLeaderboards();
    } catch (error) {
        statisticsImportMessage.textContent = error instanceof TypeError
            ? (stage === "send"
                ? "Se interrumpió el envío del Excel y no se pudo confirmar el resultado. Comprueba la conexión y vuelve a intentar con el mismo archivo y modo."
                : stage === "prepare"
                    ? "No se pudo preparar el archivo en este navegador. Vuelve a seleccionarlo e inténtalo de nuevo."
                    : "No se pudo procesar la respuesta del servidor. Revisa las estadísticas antes de repetir la carga.")
            : error.message || "No se pudo importar el archivo.";
    } finally {
        submit.disabled = false;
    }
}


async function loadLeaderboards(event) {
    if (event) event.preventDefault();
    const formData = new FormData(leaderboardForm);
    leaderboardsContainer.innerHTML = "<p>Cargando estadísticas...</p>";

    try {
        const response = await getLeaderboards(
            isUnifiedYouthCategory(formData.get("category"))
                ? "mixto"
                : formData.get("branch"),
            formData.get("category")
        );
        if (!response.ok) throw new Error("Request failed");
        renderLeaderboards(await response.json());
    } catch (error) {
        leaderboardsContainer.innerHTML = "<p>No se pudieron cargar las estadísticas.</p>";
    }
}


leaderboardForm.addEventListener("submit", loadLeaderboards);
leaderboardCategory.addEventListener("change", updateLeaderboardBranchControl);
if (statisticsImportForm) {
    statisticsImportForm.addEventListener("submit", submitStatisticsImport);
    statisticsImportMode.addEventListener("change", updateStatisticsImportMode);
    updateStatisticsImportMode();
}
updateLeaderboardBranchControl();
loadLeaderboards();

