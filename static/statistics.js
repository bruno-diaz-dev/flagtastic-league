// Public leaderboard controller. Totals are calculated by the backend.

const leaderboardForm = document.querySelector("#leaderboard-form");
const leaderboardsContainer = document.querySelector("#leaderboards");
const statisticsImportForm = document.querySelector("#statistics-import-form");
const statisticsImportMessage = document.querySelector("#statistics-import-message");
const statisticsImportProgress = document.querySelector("#statistics-import-progress");
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
    passer_rating: {
        title: "El Francotirador",
        statistic: "Índice de QB (0–100): promedio de precisión (completos/intentos), productividad (puntos por pase completo) y seguridad (intercepciones por intento) · mínimo 50 intentos totales"
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
    // A player's chosen alias is shown exactly as written.
    const legalName = displayName(leader.player_name);
    const shownName = leader.player_aka || legalName;
    const photo = leader.profile_photo_url
        ? `<img class="leaderboard-photo" src="${escapeHtml(leader.profile_photo_url)}" alt="Foto de ${escapeHtml(shownName)}" loading="lazy" decoding="async">`
        : `<span class="leaderboard-photo profile-placeholder" aria-hidden="true">${escapeHtml(nameInitials(leader.player_name))}</span>`;
    const legalNameLine = leader.player_aka
        ? `<small>${escapeHtml(legalName)}</small>`
        : "";
    return `
        <div class="leaderboard-identity">
            <a class="leaderboard-player player-profile-link" href="/players/${leader.player_id}?team_id=${leader.team_id}">
                ${photo}
                <div>
                    <strong>${escapeHtml(shownName)}</strong>
                    ${legalNameLine}
                </div>
            </a>
            <span class="leaderboard-team">
                #${leader.jersey_number} ·
                <a class="team-roster-link" href="/teams/${leader.team_id}/roster">${escapeHtml(displayName(leader.team_name))}</a>
            </span>
        </div>`;
}


function renderLeaderboards(leaderboards) {
    leaderboardsContainer.innerHTML = Object.entries(leaderboardDefinitions)
        .map(([metric, definition]) => {
            const leaders = leaderboards[metric] || [];
            const rows = leaders.length
                ? leaders.map((leader, index) => `
                    <tr>
                        <td class="rank-cell">${leader.rank ?? index + 1}</td>
                        <td>${leaderboardIdentity(leader)}</td>
                        <td class="stat-value">${
                            metric === "passer_rating"
                                ? `<strong>${leader.value}</strong><small class="leaderboard-pass-detail">${leader.passes_completed}/${leader.passes_attempted} C/I</small><small class="leaderboard-pass-detail">${leader.passing_points ?? 0} pts · ${leader.passes_intercepted ?? 0} int</small>`
                                : `<strong>${leader.value}</strong>`
                        }</td>
                    </tr>
                `).join("")
                : `<tr><td colspan="3">${metric === "passer_rating"
                    ? `Sin pasadores con ${leaderboards.passing_qualification?.minimum_attempts ?? 50} intentos acumulados.`
                    : "Sin estadísticas registradas."}</td></tr>`;

            return `
                <section class="leaderboard-panel">
                    <header class="leaderboard-heading">
                        <h3>${definition.title}</h3>
                        <p class="leaderboard-statistic">${definition.statistic}</p>
                    </header>
                    <table class="leaderboard-table">
                        <colgroup><col class="leaderboard-rank-column"><col><col class="leaderboard-total-column"></colgroup>
                        <thead><tr><th>Pos.</th><th>Jugador</th><th>${metric === "passer_rating" ? "Índice" : "Total"}</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                    ${leaderboards.tie_breakers?.[metric]
                        ? `<p class="leaderboard-note">${escapeHtml(leaderboards.tie_breakers[metric])}</p>`
                        : ""}
                </section>
            `;
        })
        .join("");
}


function csvReportCell(value) {
    let text = value == null ? "" : String(value);
    if (/^\s*[=+\-@]/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
}

function quarterbackWarningText(warning) {
    const times = warning.count > 1 ? ` (${warning.count} veces)` : "";
    if (warning.reason === "interception_thrower_unresolved") {
        return {
            reason: "Intercepción lanzada sin QB identificado",
            detail: `"${warning.label}": el #${warning.jersey_number}${times} no lanzó pases en este partido; la intercepción no se atribuyó a ningún QB.`,
        };
    }
    if (warning.reason === "passing_points_thrower_unresolved") {
        return {
            reason: "Puntos de pase sin QB identificado",
            detail: `"${warning.label}": el #${warning.jersey_number}${times} no lanzó pases en este partido; los puntos de pase no se atribuyeron a ningún QB.`,
        };
    }
    return null;
}

// Workbook problems that skip one game or one sheet instead of the import.
const SHEET_WARNING_REASONS = {
    unknown_category: "Categoría desconocida: se omitió ese partido",
    incomplete_block: "Bloque de equipo incompleto: se omitió",
    unpaired_block: "Equipo sin rival: se omitió ese bloque",
    division_mismatch: "Rivales de distinta división: se omitió ese partido",
    empty_week: "Hoja sin estadísticas: se omitió",
};

// Individual records skipped so the rest of the workbook still imports.
const OTHER_SKIPPED_REASONS = {
    live_capture_game: "Partido con captura en vivo: se corrige solo desde la captura",
    duplicate_player_row: "Jugador repetido en el mismo partido: se conservó la primera fila",
    player_game_unidentified: "Jugador en varios partidos sin partido identificado",
    several_stored_rows: "Varios registros guardados para el jugador: no se actualizó",
};

function sheetWarningText(warning) {
    const reason = SHEET_WARNING_REASONS[warning.reason];
    return reason ? {reason, detail: warning.detail || ""} : null;
}

function isPassingWarning(warning) {
    return !quarterbackWarningText(warning) && !sheetWarningText(warning);
}

function downloadSkippedStatisticsReport(data) {
    const columns = [
        "Tipo", "Motivo", "Jornada", "Hoja", "Fila", "Partido",
        "Equipo en archivo", "Equipo registrado", "Rama", "Categoría",
        "Número", "Puntos", "Recepciones", "Intercepciones", "Capturas",
        "Tacleadas", "Pases completos", "Pases intentados", "Posibles equipos",
        "Detalle",
    ];
    const reasonLabels = {
        team_unresolved: "No se pudo identificar el equipo",
        game_unresolved: "No se pudo identificar o enlazar el partido",
        game_team_unresolved: "Se omitió el partido completo por equipo no identificado",
        jersey_number_not_found: "Número no registrado en el equipo",
        unlinked_duplicate_retained: "Registro anterior sin partido conservado para revisión",
        ...OTHER_SKIPPED_REASONS,
    };
    const rows = (data.skipped || []).map(row => [
        "Registro omitido", reasonLabels[row.reason] || row.reason || "Registro omitido",
        row.week, row.sheet, row.row_number ?? row.source_row,
        row.game_index == null ? "" : row.game_index + 1,
        row.source_team_name || row.team_name,
        row.team_id == null ? "" : row.team_name,
        row.branch, row.category, row.jersey_number, row.points, row.receptions,
        row.interceptions, row.sacks, row.tackles, row.passes_completed,
        row.passes_attempted, (row.candidate_names || []).join("; "), row.detail,
    ]);
    for (const warning of data.warnings || []) {
        const sheetIssue = sheetWarningText(warning);
        if (sheetIssue) {
            rows.push([
                "Dato omitido", sheetIssue.reason, warning.week, warning.sheet,
                warning.row ?? "", "", warning.team_name, "", "", "", "", "", "",
                "", "", "", "", "", "", sheetIssue.detail,
            ]);
            continue;
        }
        const quarterback = quarterbackWarningText(warning);
        rows.push(quarterback
            ? [
                "Dato omitido", quarterback.reason, warning.week, warning.sheet,
                warning.row, warning.game_index == null ? "" : warning.game_index + 1,
                warning.team_name, warning.team_name, warning.branch,
                warning.category, warning.jersey_number, "", "", "", "", "", "",
                "", "", quarterback.detail,
            ]
            : [
                "Dato omitido", "Pases inconsistentes omitidos", warning.week,
                warning.sheet, warning.row, "", warning.team_name, warning.team_name,
                warning.branch, warning.category, warning.jersey_number, "", "", "", "",
                "", warning.source_completed, warning.source_attempted, "",
                `${warning.source_completed} completos y ${warning.source_attempted} intentos en el archivo; se conservaron los pases publicados si existían.`,
            ]);
    }
    const csv = "\uFEFF" + [columns, ...rows]
        .map(row => row.map(csvReportCell).join(","))
        .join("\r\n");
    const blobUrl = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().replace(/[:T]/g, "-").slice(0, 16);
    link.href = blobUrl;
    link.download = `estadisticas-omitidas-${timestamp}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}


function renderSkippedStatistics(data) {
    statisticsImportSkipped.replaceChildren();
    const skipped = data.skipped || [];
    const warnings = data.warnings || [];
    const passingWarnings = warnings.filter(isPassingWarning);
    const quarterbackWarnings = warnings.filter(warning => quarterbackWarningText(warning));
    const sheetWarnings = warnings.filter(warning => sheetWarningText(warning));
    if (sheetWarnings.length) {
        const heading = document.createElement("p");
        heading.textContent = `${sheetWarnings.length} problema(s) del archivo omitieron partidos u hojas; el resto se importó.`;
        const list = document.createElement("ul");
        for (const warning of sheetWarnings) {
            const item = document.createElement("li");
            item.textContent = `Jornada ${warning.week} · ${sheetWarningText(warning).reason}. ${warning.detail || ""}`;
            list.append(item);
        }
        statisticsImportSkipped.append(heading, list);
    }
    if (passingWarnings.length) {
        const heading = document.createElement("p");
        heading.textContent = `${passingWarnings.length} advertencia(s): pases inconsistentes omitidos. No se inventaron intentos; si había pases publicados, se conservaron.`;
        const list = document.createElement("ul");
        for (const warning of passingWarnings) {
            const item = document.createElement("li");
            item.textContent = `${warning.sheet}, bloque desde fila ${warning.row} · Jornada ${warning.week} · ${warning.team_name} (${warning.branch} / ${warning.category}) · #${warning.jersey_number}: ${warning.source_completed} completos y ${warning.source_attempted} intentos en el archivo. Se procesaron las demás estadísticas válidas.`;
            list.append(item);
        }
        statisticsImportSkipped.append(heading, list);
    }
    if (quarterbackWarnings.length) {
        const heading = document.createElement("p");
        heading.textContent = `${quarterbackWarnings.length} dato(s) de QB omitidos: el número anotado no lanzó pases en ese partido, así que no se atribuyeron a nadie. Detalle en el CSV.`;
        statisticsImportSkipped.append(heading);
    }
    if (!skipped.length && !warnings.length) return;
    const unresolvedReasons = new Set(["team_unresolved", "game_unresolved", "game_team_unresolved"]);
    const unresolved = skipped.filter(row => unresolvedReasons.has(row.reason));
    const missingJersey = skipped.filter(row =>
        row.reason === "jersey_number_not_found" || !row.reason
    );
    const otherSkipped = skipped.filter(row => OTHER_SKIPPED_REASONS[row.reason]);
    if (otherSkipped.length) {
        const heading = document.createElement("p");
        heading.textContent = `${otherSkipped.length} registro(s) omitidos por reglas de seguridad de datos; el resto se importó.`;
        const list = document.createElement("ul");
        const counts = {};
        for (const row of otherSkipped) counts[row.reason] = (counts[row.reason] || 0) + 1;
        for (const [reason, count] of Object.entries(counts)) {
            const item = document.createElement("li");
            item.textContent = `${OTHER_SKIPPED_REASONS[reason]}: ${count}`;
            list.append(item);
        }
        statisticsImportSkipped.append(heading, list);
    }
    const unlinkedDuplicates = skipped.filter(row => row.reason === "unlinked_duplicate_retained");
    if (unlinkedDuplicates.length) {
        const heading = document.createElement("p");
        heading.textContent = `${unlinkedDuplicates.length} registro(s) anteriores sin partido ligado duplican a jugadores ya ligados a su partido. Se actualizó el registro del partido y el anterior se conservó sin cambios para revisión (detalle en el CSV).`;
        statisticsImportSkipped.append(heading);
    }
    if (unresolved.length) {
        const heading = document.createElement("p");
        heading.textContent = `${unresolved.length} registros omitidos porque no se pudo identificar con seguridad su equipo o partido. Los demás datos válidos sí se importaron.`;
        const list = document.createElement("ul");
        const identities = new Set();
        for (const row of unresolved) {
            const identity = JSON.stringify([row.week, row.game_index, row.team_name, row.branch, row.category, row.reason]);
            if (identities.has(identity)) continue;
            identities.add(identity);
            const item = document.createElement("li");
            const gameLabel = row.game_index == null ? "" : ` · partido #${row.game_index + 1}`;
            const candidates = row.candidate_names?.length
                ? ` · Posibles equipos: ${row.candidate_names.join(", ")}` : "";
            item.textContent = `Jornada ${row.week}${gameLabel} · ${row.team_name} (${row.branch} / ${row.category})${candidates}`;
            list.append(item);
        }
        statisticsImportSkipped.append(heading, list);
    }
    if (missingJersey.length) {
        const heading = document.createElement("p");
        heading.textContent = `${missingJersey.length} registros omitidos: número no registrado en el equipo.`;
        const list = document.createElement("ul");
        const identities = new Set();
        for (const row of missingJersey) {
            const identity = JSON.stringify([row.week, row.team_id, row.jersey_number]);
            if (identities.has(identity)) continue;
            identities.add(identity);
            const item = document.createElement("li");
            item.textContent = `Jornada ${row.week} · ${row.team_name} (${row.branch} / ${row.category}) · #${row.jersey_number}`;
            list.append(item);
        }
        statisticsImportSkipped.append(heading, list);
    }
    if (data.preserved_weeks?.length) {
        const notice = document.createElement("p");
        notice.textContent = `Sin registros válidos en las jornadas ${data.preserved_weeks.join(", ")}. Se conservaron sus datos anteriores.`;
        statisticsImportSkipped.append(notice);
    }
    const download = document.createElement("button");
    download.type = "button";
    download.className = "statistics-skipped-download";
    download.textContent = "Descargar archivo de registros omitidos (CSV)";
    download.addEventListener("click", () => downloadSkippedStatisticsReport(data));
    statisticsImportSkipped.append(download);
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
    statisticsImportProgress.hidden = false;
    updateImportProgress(statisticsImportProgress, 1, "Preparando archivo");
    statisticsImportForm.setAttribute("aria-busy", "true");
    statisticsImportSkipped.replaceChildren();
    statisticsImportMessage.textContent = "Preparando archivo...";
    let stage = "prepare";
    try {
        const file = await prepareStatisticsUpload(fields.get("file"), (percent, message) => updateImportProgress(statisticsImportProgress, percent, message));
        updateImportProgress(statisticsImportProgress, 40, "Archivo preparado");
        const onProgress = event => {
            if (event.phase === "upload") updateImportProgress(statisticsImportProgress, 40 + 50 * event.loaded / event.total, "Enviando archivo");
            else if (event.phase === "processing") updateImportProgress(statisticsImportProgress, 92, "Procesando en servidor");
            else if (event.phase === "response") updateImportProgress(statisticsImportProgress, 98, "Recibiendo resultado");
        };
        stage = "send";
        statisticsImportMessage.textContent = "Importando estadísticas...";
        const mode = statisticsImportMode.value;
        let response;
        if (mode === "division") {
            response = await importDivisionStatistics(
                Number(statisticsWeekInput.value),
                statisticsBranchInput.value,
                statisticsCategoryInput.value,
                file, existingRecords, onProgress
            );
        } else if (statisticsAllWeekInput.value) {
            response = await importWeekStatistics(Number(statisticsAllWeekInput.value), file, existingRecords, onProgress);
        } else {
            response = await importOfficialStatistics(file, existingRecords, onProgress);
        }
        stage = "response";
        const data = await readStatisticsImportResponse(response);
        statisticsImportForm.reset();
        updateStatisticsImportMode();
        const omittedCount = (data.skipped?.length || 0) + (data.warnings?.length || 0);
        const importSummary = `${data.imported} registros procesados (${data.created ?? "?"} nuevos, ${data.updated ?? "?"} actualizados, ${data.retained_count || 0} existentes conservados) en ${data.weeks?.length ?? 1} jornada(s).`;
        const attendanceSummary = typeof data.attendance_added === "number"
            ? ` Asistencias: ${data.attendance_added} añadidas y ${data.attendance_already_registered || 0} ya registradas.`
            : "";
        statisticsImportMessage.textContent = omittedCount
            ? `${importSummary}${attendanceSummary} Se omitieron ${omittedCount} registros o datos; el resumen y la descarga CSV están debajo.`
            : `${importSummary}${attendanceSummary} No se omitieron registros.`;
        renderSkippedStatistics(data);
        await loadLeaderboards();
        finishImportProgress(statisticsImportProgress, true);
    } catch (error) {
        finishImportProgress(statisticsImportProgress, false);
        statisticsImportMessage.textContent = error instanceof TypeError
            ? (stage === "send"
                ? "Se interrumpió el envío del Excel y no se pudo confirmar el resultado. Comprueba la conexión y vuelve a intentar con el mismo archivo y modo."
                : stage === "prepare"
                    ? "No se pudo preparar el archivo en este navegador. Vuelve a seleccionarlo e inténtalo de nuevo."
                    : "No se pudo procesar la respuesta del servidor. Revisa las estadísticas antes de repetir la carga.")
            : error.message || "No se pudo importar el archivo.";
    } finally {
        statisticsImportForm.removeAttribute("aria-busy");
        submit.disabled = false;
    }
}


let leaderboardRequest = 0;

async function loadLeaderboards(event) {
    const request = ++leaderboardRequest;
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
        const body = await response.json();
        if (request !== leaderboardRequest) return;
        renderLeaderboards(body);
        if (typeof setPageHero === "function") {
            const category = formData.get("category");
            const branch = isUnifiedYouthCategory(category) ? "Infantiles" : displayName(formData.get("branch"));
            const week = body.passing_qualification?.latest_week;
            setPageHero({tags: [
                {label: `${branch} · ${displayName(category)}`, tone: "gold"},
                ...(week ? [{label: `Hasta la jornada ${week}`}] : []),
            ]});
        }
    } catch (error) {
        if (request !== leaderboardRequest) return;
        leaderboardsContainer.innerHTML = "<p>No se pudieron cargar las estadísticas.</p>";
    }
}


leaderboardForm.addEventListener("submit", loadLeaderboards);
leaderboardCategory.addEventListener("change", () => {
    updateLeaderboardBranchControl();
    loadLeaderboards();
});
leaderboardBranch.addEventListener("change", loadLeaderboards);
if (statisticsImportForm) {
    statisticsImportForm.addEventListener("submit", submitStatisticsImport);
    statisticsImportMode.addEventListener("change", updateStatisticsImportMode);
    updateStatisticsImportMode();
}
updateLeaderboardBranchControl();
loadLeaderboards();




