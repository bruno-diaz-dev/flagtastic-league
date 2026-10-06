// Administrator-only name-coincidence review across every division.

const duplicateNameFilter = document.querySelector("#duplicate-name-filter");
const duplicateCategoryFilter = document.querySelector("#duplicate-category-filter");
const duplicateBranchFilter = document.querySelector("#duplicate-branch-filter");
const duplicateAuditCount = document.querySelector("#duplicate-audit-count");
const duplicateAuditMessage = document.querySelector("#duplicate-audit-message");
const duplicateAuditResults = document.querySelector("#duplicate-audit-results");
let duplicateGroups = [];

function normalizeAuditText(value) {
    return String(value || "").normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();
}

function renderDuplicateAudit() {
    const search = normalizeAuditText(duplicateNameFilter.value.trim());
    const category = duplicateCategoryFilter.value;
    const branch = duplicateBranchFilter.value;
    const visible = duplicateGroups.filter((group) => (
        (!category || group.category === category)
        && (!branch || group.teams.some(team => team.branch === branch))
        && (!search || group.teams.some((team) => (
            normalizeAuditText(team.name).includes(search)
        )))
    ));

    duplicateAuditCount.textContent = `${visible.length} posible${visible.length === 1 ? "" : "s"} duplicado${visible.length === 1 ? "" : "s"}`;
    if (!visible.length) {
        duplicateAuditResults.innerHTML = `
            <div class="empty-state">
                <h3>Sin coincidencias</h3>
                <p>No hay coincidencias de nombres con estos filtros.</p>
            </div>`;
        return;
    }

    duplicateAuditResults.innerHTML = visible.map((group) => `
        <article class="duplicate-team-group">
            <header>
                <div>
                    <span class="status-badge">${escapeHtml(group.category.toUpperCase())}</span>
                    <h3>${escapeHtml(group.teams[0].name)}</h3>
                </div>
                <span>${group.teams.length} registros</span>
            </header>
            <div class="duplicate-team-list">
                ${group.teams.map((team) => `
                    <div class="duplicate-team-row">
                        <div>
                            <strong>${escapeHtml(team.name)}</strong>
                            <p>${escapeHtml(team.branch)} / ${escapeHtml(team.category)} · ${escapeHtml(team.status)}</p>
                        </div>
                        <div class="duplicate-team-actions">
                            <a class="secondary-link" href="/teams/${team.id}/roster">Ver roster</a>
                            <a class="secondary-link" href="/teams/${team.id}/manage">Administrar</a>
                        </div>
                    </div>
                `).join("")}
            </div>
        </article>
    `).join("");
}

async function loadDuplicateAudit() {
    duplicateAuditMessage.textContent = "Buscando posibles duplicados...";
    try {
        const response = await getTeamDuplicateCandidates();
        if (response.status === 401) {
            window.location.assign("/login");
            return;
        }
        if (response.status === 403) {
            window.location.assign("/teams");
            return;
        }
        if (!response.ok) throw new Error("duplicate audit failed");
        duplicateGroups = await response.json();
        duplicateAuditMessage.textContent = "";
        renderDuplicateAudit();
    } catch (error) {
        duplicateAuditMessage.textContent = "No se pudo cargar la auditoría de equipos.";
    }
}

duplicateNameFilter.addEventListener("input", renderDuplicateAudit);
duplicateCategoryFilter.addEventListener("change", renderDuplicateAudit);
duplicateBranchFilter.addEventListener("change", renderDuplicateAudit);
loadDuplicateAudit();
