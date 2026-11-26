// Administrator view of active players below the finals attendance threshold.

const eligibilitySearch = document.querySelector("#eligibility-search");
const eligibilityCategory = document.querySelector("#eligibility-category");
const eligibilityBranch = document.querySelector("#eligibility-branch");
const eligibilityCount = document.querySelector("#eligibility-count");
const eligibilityMessage = document.querySelector("#eligibility-message");
const eligibilityResults = document.querySelector("#eligibility-results");
let ineligiblePlayers = [];

function normalizeEligibilityText(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function populateEligibilityFilter(select, values) {
    const selected = select.value;
    select.innerHTML = `<option value="">Todas</option>${values.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`;
    if (values.includes(selected)) select.value = selected;
}

function renderEligibility() {
    const search = normalizeEligibilityText(eligibilitySearch.value.trim());
    const category = eligibilityCategory.value;
    const branch = eligibilityBranch.value;
    const visible = ineligiblePlayers.filter(player => (
        (!category || player.category === category)
        && (!branch || player.branch === branch)
        && (!search || [player.player_name, player.team_name, player.jersey_number]
            .some(value => normalizeEligibilityText(value).includes(search)))
    ));

    eligibilityCount.textContent = `${visible.length} jugador${visible.length === 1 ? "" : "es"} que aún no cumple${visible.length === 1 ? "" : "n"}`;
    if (!visible.length) {
        eligibilityResults.innerHTML = `
            <div class="empty-state">
                <h3>${ineligiblePlayers.length ? "Sin coincidencias" : "Todos cumplen por ahora"}</h3>
                <p>${ineligiblePlayers.length ? "No hay jugadores pendientes con estos filtros." : "No hay jugadores activos por debajo del requisito de asistencias en el calendario actual."}</p>
            </div>`;
        return;
    }

    eligibilityResults.innerHTML = visible.map(player => `
        <article class="finals-eligibility-player">
            <div class="finals-eligibility-identity">
                <div>
                    <span class="status-badge">${escapeHtml(player.category)} · ${escapeHtml(player.branch)}</span>
                    <h3>${escapeHtml(player.player_name)}</h3>
                    <p>#${escapeHtml(player.jersey_number)} · ${escapeHtml(player.team_name)}</p>
                </div>
                <a class="secondary-link" href="/teams/${player.team_id}/roster">Ver equipo</a>
            </div>
            <p class="finals-eligibility-progress"><strong>${player.attended_games} de ${player.scheduled_games} asistencias</strong><span>Requiere ${player.required_games}</span></p>
            <progress max="${player.required_games}" value="${Math.min(player.attended_games, player.required_games)}" aria-label="${player.attended_games} de ${player.required_games} asistencias requeridas"></progress>
        </article>
    `).join("");
}

async function loadEligibility() {
    eligibilityMessage.textContent = "Cargando jugadores…";
    try {
        const response = await fetch("/api/admin/finals-eligibility", {cache: "no-store"});
        if (response.status === 401) { window.location.assign("/login"); return; }
        if (response.status === 403) { window.location.assign("/teams"); return; }
        if (!response.ok) throw new Error("eligibility report unavailable");
        ineligiblePlayers = await response.json();
        populateEligibilityFilter(eligibilityCategory, [...new Set(ineligiblePlayers.map(row => row.category))].sort());
        populateEligibilityFilter(eligibilityBranch, [...new Set(ineligiblePlayers.map(row => row.branch))].sort());
        eligibilityMessage.textContent = "";
        renderEligibility();
    } catch (error) {
        eligibilityMessage.textContent = "No se pudo cargar el reporte de elegibilidad. Intenta actualizar la página.";
    }
}

eligibilitySearch.addEventListener("input", renderEligibility);
eligibilityCategory.addEventListener("change", renderEligibility);
eligibilityBranch.addEventListener("change", renderEligibility);
loadEligibility();

