// Account IDs, not normalized names, keep similarly named officials separate.
const refereeAuditPanel = document.querySelector('#referee-assignment-audit');
const refereeAuditWeek = document.querySelector('#referee-audit-week');
const refereeAuditSearch = document.querySelector('#referee-audit-search');
const refereeAuditList = document.querySelector('#referee-audit-list');
const refereeAuditMessage = document.querySelector('#referee-audit-message');
const refereeAuditCount = document.querySelector('#referee-audit-count');
const refereeAuditRefresh = document.querySelector('#referee-audit-refresh');
let refereeAuditData = null;
const auditPositionLabels = {referee:'Referee',down_judge:'Down Judge',field_judge:'Field Judge',side_judge:'Side Judge',statistician:'Estadístico'};
const auditStatusLabels = {scheduled:'Pendiente',postponed:'Pospuesto',completed:'Finalizado'};
function auditSearchText(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es');
}
function renderRefereeAssignments() {
    if (!refereeAuditData) return;
    const week = Number(refereeAuditWeek.value) || null;
    const query = auditSearchText(refereeAuditSearch.value.trim());
    const people = refereeAuditData.officials.filter(person=>auditSearchText(
        `${person.display_name} ${person.name} ${person.aka || ''} ${person.email} #${person.id}`
    ).includes(query)).map(person=>({...person,games:person.games.filter(game=>!week || game.week===week)}));
    const withGames = people.filter(person=>person.games.length).length;
    const assignments = people.reduce((sum,person)=>sum+person.games.length,0);
    refereeAuditCount.textContent = `${week ? `Jornada ${week}` : 'Todas las jornadas'} · ${assignments} ${assignments===1?'asignación':'asignaciones'} · ${withGames} ${withGames===1?'oficial':'oficiales'} con juegos · ${people.length-withGames} sin juegos`;
    refereeAuditList.innerHTML = people.map(person=>`<details class="referee-audit-person" data-referee-account="${person.id}">
        <summary><span class="referee-audit-identity"><strong>${escapeHtml(person.display_name)}</strong>
            ${person.name !== person.display_name ? `<span>${escapeHtml(person.name)}</span>` : ''}
            <small>Cuenta #${person.id} · ${escapeHtml(person.email)}${person.status !== 'active' ? ' · Inactiva' : ''}</small></span>
            <span class="referee-audit-total">${person.games.length} ${person.games.length===1?'juego':'juegos'}</span></summary>
        <div class="referee-audit-games">${person.games.length ? person.games.map(game=>`<article>
            <div><p class="referee-audit-slot">J${game.week} · ${game.start_time ? escapeHtml(game.start_time.slice(0,5))+' h' : 'Hora por asignar'} · ${game.field_number ? `Campo ${game.field_number}`:'Campo por asignar'}</p>
                <h4>${escapeHtml(game.home_team)} vs ${escapeHtml(game.away_team)}</h4>
                <p>${escapeHtml(auditPositionLabels[game.position] || game.position)} · ${escapeHtml(auditStatusLabels[game.status] || game.status)}</p></div>
            <a href="/games/${game.id}" class="secondary-button">Abrir partido</a></article>`).join('') : '<p>Sin juegos asignados en esta consulta.</p>'}</div>
        </details>`).join('') || '<p>No se encontraron cuentas con esa búsqueda.</p>';
}
async function loadRefereeAssignments() {
    if (refereeAuditRefresh.disabled) return;
    refereeAuditRefresh.disabled = true;
    refereeAuditMessage.textContent = 'Cargando asignaciones…';
    try {
        const response = await getRefereeAssignmentAudit();
        if ([401,403].includes(response.status)) {
            refereeAuditPanel.classList.add('hidden');
            refereeAuditData = null;refereeAuditList.innerHTML='';return;
        }
        if (!response.ok) throw new Error('assignments');
        const data = await response.json();
        const first = !refereeAuditData;
        const selected = first ? String(data.weeks[0] || '') : refereeAuditWeek.value;
        refereeAuditData = data;
        refereeAuditWeek.innerHTML = '<option value="">Todas las jornadas</option>'+data.weeks.map(week=>`<option value="${week}">Jornada ${week}</option>`).join('');
        refereeAuditWeek.value = data.weeks.some(week=>String(week)===selected) ? selected : '';
        refereeAuditWeek.disabled = false;
        refereeAuditPanel.classList.remove('hidden');
        renderRefereeAssignments();
        refereeAuditMessage.textContent = '';
    } catch (error) {
        refereeAuditMessage.textContent = 'No se pudieron consultar las asignaciones. Pulsa Actualizar para reintentar.';
    } finally {refereeAuditRefresh.disabled=false;}
}
refereeAuditWeek.addEventListener('change',renderRefereeAssignments);
refereeAuditSearch.addEventListener('input',renderRefereeAssignments);
refereeAuditRefresh.addEventListener('click',loadRefereeAssignments);
loadRefereeAssignments();
