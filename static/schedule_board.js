// Administrative schedule map. All writes are authorized and checked by the API.
const scheduleBoard = document.querySelector('#admin-schedule-board');
const boardWeek = document.querySelector('#schedule-board-week');
const boardGrid = document.querySelector('#schedule-board-grid');
const boardMessage = document.querySelector('#schedule-board-message');
const boardForm = document.querySelector('#schedule-board-edit');
let boardSaving = false;
let boardCrewSaving = false;

function boardGameEditable(game) {
    return game.status !== 'completed' && game.home_score == null && game.away_score == null;
}
function boardSelectedGame() {
    return gamesState.find(game => String(game.id) === boardForm.elements.game_id.value
        && String(game.week) === boardWeek.value);
}
function populateBoardDestination() {
    const game = boardSelectedGame();
    boardForm.elements.start_time.value = game?.start_time?.slice(0, 5) || '';
    boardForm.elements.field_number.value = String(game?.field_number || 1);
    loadBoardOfficials();
}
function renderScheduleBoard() {
    if (!scheduleBoard) return;
    const weeks = [...new Set(gamesState.map(game => game.week))].sort((a, b) => a - b);
    const chosenWeek = Number(boardWeek.value);
    const initialWeek = weeks.find(week => gamesState.some(game => game.week === week && boardGameEditable(game))) || weeks[0];
    boardWeek.innerHTML = weeks.map(week => `<option value="${week}">Jornada ${week}</option>`).join('');
    boardWeek.value = String(weeks.includes(chosenWeek) ? chosenWeek : initialWeek || '');
    const games = gamesState.filter(game => String(game.week) === boardWeek.value);
    const hours = games.filter(game => game.start_time).map(game => Number(game.start_time.slice(0, 2)));
    const firstHour = hours.length ? Math.max(0, Math.min(...hours) - 1) : 8;
    const lastHour = hours.length ? Math.min(23, Math.max(...hours) + 2) : 22;
    const times = new Set(Array.from({length: lastHour - firstHour + 1}, (_, i) => `${String(i + firstHour).padStart(2, '0')}:00`));
    games.forEach(game => {if (game.start_time) times.add(game.start_time.slice(0, 5));});
    const card = game => `<button type="button" class="schedule-board-card ${game.status === 'postponed' ? 'is-postponed' : ''}" data-board-game="${game.id}" draggable="${boardGameEditable(game) && !boardSaving && !boardCrewSaving}" ${!boardGameEditable(game) || boardSaving || boardCrewSaving ? 'disabled' : ''} aria-label="Administrar ${escapeHtml(gameLabel(game))}">
        <strong>${escapeHtml(game.home_team.name)}</strong><span>vs ${escapeHtml(game.away_team.name)}</span>
        <small>${escapeHtml(game.home_team.category.toUpperCase())} · ${escapeHtml(game.home_team.branch)}${game.is_friendly ? ' · Amistoso' : ''}${game.status === 'postponed' ? ' · Pospuesto' : ''}${!boardGameEditable(game) ? ' · Finalizado' : ''}</small></button>`;
    boardGrid.innerHTML = !games.length ? '<p>No hay partidos en esta jornada.</p>' : `<table class="schedule-board-table"><thead><tr><th scope="col">Hora</th>${Array.from({length: 8}, (_, i) => `<th scope="col">Campo ${i + 1}</th>`).join('')}</tr></thead><tbody>${[...times].sort().map(time => `<tr><th scope="row">${time}</th>${Array.from({length: 8}, (_, i) => `<td data-board-time="${time}" data-board-field="${i + 1}" aria-label="${time}, campo ${i + 1}">${games.filter(game => game.field_number === i + 1 && game.start_time?.slice(0, 5) === time).map(card).join('')}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    const unscheduled = games.filter(game => !game.start_time);
    if (unscheduled.length) boardGrid.insertAdjacentHTML('beforeend', `<div class="schedule-board-unscheduled"><strong>Sin horario</strong>${unscheduled.map(card).join('')}</div>`);
    const selectedId = boardForm.elements.game_id.value;
    const editable = games.filter(boardGameEditable);
    boardForm.elements.game_id.innerHTML = editable.map(game => `<option value="${game.id}">${escapeHtml(gameLabel(game))} · ${gameTime(game)} · Campo ${game.field_number}</option>`).join('');
    if (editable.some(game => String(game.id) === selectedId)) boardForm.elements.game_id.value = selectedId;
    boardForm.querySelectorAll('input, select, button').forEach(control => {control.disabled = boardSaving || boardCrewSaving || !editable.length;});
    boardWeek.disabled = boardSaving || boardCrewSaving || !weeks.length;
    populateBoardDestination();
}
async function saveBoardMove(gameId, time, field) {
    if (boardSaving || boardCrewSaving) return;
    const game = gamesState.find(game => game.id === gameId && String(game.week) === boardWeek.value);
    if (!game || !boardGameEditable(game)) return;
    if (gamesState.some(other => other.id !== gameId && other.week === game.week
        && other.field_number === field && other.start_time?.slice(0, 5) === time)) {
        boardMessage.textContent = 'Ese campo ya tiene otro partido en la misma jornada y hora. Elige un espacio libre.';
        return;
    }
    boardSaving = true;
    syncBoardCrewControls();
    boardMessage.textContent = 'Guardando cambio…';
    scheduleBoard.setAttribute('aria-busy', 'true');
    boardForm.querySelectorAll('input, select, button').forEach(control => {control.disabled = true;});
    boardWeek.disabled = true;
    try {
        const response = await updateGameSchedule(gameId, time, field);
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = Array.isArray(body.detail) ? body.detail.map(error => error.msg).join('. ') : body.detail;
            boardMessage.textContent = detail || 'No se pudo mover el partido.';
            return;
        }
        gamesState = gamesState.map(current => current.id === body.id
            ? {...current, start_time: body.start_time, field_number: body.field_number} : current);
        boardMessage.textContent = `Cambio guardado: ${body.start_time.slice(0, 5)}, campo ${body.field_number}. Se conservan los oficiales.`;
        renderFilteredGames();
    } catch (error) {
        boardMessage.textContent = 'No se pudo confirmar el cambio. Revisa el rol antes de reintentar.';
    } finally {
        boardSaving = false;
        syncBoardCrewControls();
        scheduleBoard.removeAttribute('aria-busy');
        renderScheduleBoard();
    }
}
boardWeek?.addEventListener('change', () => {boardMessage.textContent = ''; renderScheduleBoard();});
boardForm?.elements.game_id.addEventListener('change', populateBoardDestination);
boardForm?.addEventListener('submit', event => {
    event.preventDefault();
    saveBoardMove(Number(boardForm.elements.game_id.value), boardForm.elements.start_time.value,
        Number(boardForm.elements.field_number.value));
});
boardGrid?.addEventListener('click', event => {
    const card = event.target.closest('[data-board-game]');
    if (!card || boardSaving || boardCrewSaving || card.disabled) return;
    boardForm.elements.game_id.value = card.dataset.boardGame;
    populateBoardDestination();
    boardForm.scrollIntoView({block: 'nearest'});
    boardForm.elements.start_time.focus({preventScroll: true});
});
boardGrid?.addEventListener('dragstart', event => {
    const card = event.target.closest('[data-board-game]');
    if (!card || boardSaving || boardCrewSaving || card.disabled) {event.preventDefault(); return;}
    event.dataTransfer.setData('application/x-flagtastic-game', card.dataset.boardGame);
    event.dataTransfer.effectAllowed = 'move';
});
boardGrid?.addEventListener('dragover', event => {
    if (!boardSaving && !boardCrewSaving && event.target.closest('[data-board-time]')) {
        event.preventDefault(); event.dataTransfer.dropEffect = 'move';
        boardGrid.querySelectorAll('.is-drop-target').forEach(cell => cell.classList.remove('is-drop-target'));
        event.target.closest('[data-board-time]').classList.add('is-drop-target');
    }
});
boardGrid?.addEventListener('dragend', () => {
    boardGrid.querySelectorAll('.is-drop-target').forEach(cell => cell.classList.remove('is-drop-target'));
});
boardGrid?.addEventListener('dragleave', event => {
    const cell = event.target.closest('[data-board-time]');
    if (cell && !cell.contains(event.relatedTarget)) cell.classList.remove('is-drop-target');
});
boardGrid?.addEventListener('drop', event => {
    boardGrid.querySelectorAll('.is-drop-target').forEach(cell => cell.classList.remove('is-drop-target'));
    const cell = event.target.closest('[data-board-time]');
    if (!cell || boardSaving || boardCrewSaving) return;
    event.preventDefault();
    saveBoardMove(Number(event.dataTransfer.getData('application/x-flagtastic-game')),
        cell.dataset.boardTime, Number(cell.dataset.boardField));
});


const boardCrewPanel = document.querySelector('#schedule-board-officials');
const boardCrewSlots = document.querySelector('#schedule-board-officials-slots');
const boardCrewMessage = document.querySelector('#schedule-board-officials-message');
const boardCrewGameLabel = document.querySelector('#schedule-board-officials-game');
const boardCrewRefresh = document.querySelector('#schedule-board-refresh-officials');
const boardCrewPositions = [
    ['referee', 'Referee'], ['down_judge', 'Down Judge'],
    ['field_judge', 'Field Judge'], ['side_judge', 'Side Judge'],
    ['statistician', 'Estadístico']
];
let boardCrewLoadedId = null;
let boardCrewRequest = 0;
let boardCrewAssignments = new Map();
let boardCrewLoading = false;

function syncBoardCrewControls() {
    const disabled = boardSaving || boardCrewSaving || boardCrewLoading;
    boardCrewPanel?.querySelectorAll('select, button').forEach(control => {control.disabled = disabled;});
}
async function loadBoardOfficials(force = false) {
    if (!boardCrewPanel || !scheduleBoard.querySelector('details').open) return;
    const game = boardSelectedGame();
    if (!game) {
        boardCrewRequest++;
        boardCrewLoadedId = null;
        boardCrewLoading = false;
        syncBoardCrewControls();
        boardCrewPanel.classList.add('hidden');
        return;
    }
    boardCrewPanel.classList.remove('hidden');
    boardCrewGameLabel.textContent = gameLabel(game);
    if (!force && boardCrewLoadedId === game.id) return;
    const request = ++boardCrewRequest;
    boardCrewLoadedId = game.id;
    boardCrewSlots.innerHTML = '';
    boardCrewMessage.textContent = 'Cargando oficiales…';
    boardCrewLoading = true;
    syncBoardCrewControls();
    try {
        const [usersResponse, crewResponse] = await Promise.all([getAdminUsers(), getGameReferees(game.id)]);
        if (!usersResponse.ok || !crewResponse.ok) throw new Error('No se pudieron cargar los oficiales.');
        const [users, crew] = await Promise.all([usersResponse.json(), crewResponse.json()]);
        if (request !== boardCrewRequest || boardSelectedGame()?.id !== game.id) return;
        const active = users.filter(user => user.status === 'active' && (user.roles || [user.role]).includes('referee'));
        const candidates = [...active];
        crew.forEach(official => {
            if (!candidates.some(user => user.id === official.id)) candidates.push({...official, unavailable: true});
        });
        candidates.sort((a, b) => (a.display_name || a.name).localeCompare(b.display_name || b.name, 'es'));
        boardCrewAssignments = new Map(crew.map(official => [official.position, official.id]));
        boardCrewSlots.innerHTML = boardCrewPositions.map(([position, label]) => {
            const selected = boardCrewAssignments.get(position);
            return `<form class="schedule-board-official-slot" data-board-position="${position}">
                <label>${label}<select name="official_id" aria-label="${label} del partido">
                    <option value="">Sin asignar</option>${candidates.map(user => `<option value="${user.id}" ${user.id === selected ? 'selected' : ''} ${user.unavailable && user.id !== selected ? 'disabled' : ''}>${escapeHtml(refereeIdentityLabel(user))}${user.unavailable ? ' (no activo)' : ''}</option>`).join('')}
                </select></label>
                <button type="submit">Guardar ${label}</button>
                <p class="form-message" role="status"></p>
            </form>`;
        }).join('');
        boardCrewMessage.textContent = 'Cada puesto se guarda por separado. Selecciona Sin asignar y guarda para dejarlo vacante.';
    } catch (error) {
        if (request !== boardCrewRequest) return;
        boardCrewLoadedId = null;
        boardCrewMessage.textContent = 'No se pudieron cargar los oficiales. Pulsa Actualizar lista para reintentar.';
    } finally {
        if (request === boardCrewRequest) {
            boardCrewLoading = false;
            syncBoardCrewControls();
        }
    }
}
boardCrewSlots?.addEventListener('submit', async event => {
    event.preventDefault();
    if (boardCrewSaving || boardSaving) return;
    const form = event.target;
    const position = form.dataset.boardPosition;
    const game = boardSelectedGame();
    if (!game || game.id !== boardCrewLoadedId || !boardCrewPositions.some(([key]) => key === position)) return;
    const nextId = Number(form.elements.official_id.value) || null;
    const previousId = boardCrewAssignments.get(position) || null;
    const message = form.querySelector('.form-message');
    if (nextId === previousId) {message.textContent = 'Sin cambios.'; return;}
    if (nextId && [...boardCrewAssignments].some(([key, id]) => key !== position && id === nextId)) {
        message.textContent = 'Esta persona ya tiene otro puesto en el partido.';
        return;
    }
    const request = boardCrewRequest;
    boardCrewSaving = true;
    const button = form.querySelector('button');
    const label = button.textContent;
    button.textContent = 'Guardando…';
    message.textContent = 'Guardando asignación…';
    form.setAttribute('aria-busy', 'true');
    syncBoardCrewControls();
    boardForm.querySelectorAll('input, select, button').forEach(control => {control.disabled = true;});
    boardWeek.disabled = true;
    try {
        const response = nextId
            ? await assignGameReferee(game.id, nextId, position)
            : await removeGameReferee(game.id, previousId);
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            const detail = Array.isArray(body.detail) ? body.detail.map(error => error.msg).join('. ') : body.detail;
            message.textContent = detail || 'No se pudo guardar la asignación.';
            return;
        }
        if (request !== boardCrewRequest) return;
        if (nextId) boardCrewAssignments.set(position, nextId);
        else boardCrewAssignments.delete(position);
        message.textContent = nextId ? 'Asignación guardada.' : 'Puesto sin asignar.';
    } catch (error) {
        message.textContent = 'No se pudo confirmar el guardado. Actualiza la lista para comprobar la asignación.';
    } finally {
        boardCrewSaving = false;
        if (request === boardCrewRequest) {
            syncBoardCrewControls();
            button.textContent = label;
            form.removeAttribute('aria-busy');
        }
        renderScheduleBoard();
    }
});
boardCrewRefresh?.addEventListener('click', () => {if (!boardCrewSaving) loadBoardOfficials(true);});
scheduleBoard?.querySelector('details').addEventListener('toggle', () => {
    if (scheduleBoard.querySelector('details').open) loadBoardOfficials();
});
renderScheduleBoard();
