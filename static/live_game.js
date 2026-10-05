// Live sporting feed; refresh only while visible and never overlap requests.
const liveRoot = document.querySelector("#live-match");
const liveGameId = document.querySelector(".game-detail-page").dataset.gameId;
const liveForm = document.querySelector("#live-event-form");
const liveMessage = document.querySelector("#live-operation-message");
const liveStatus = document.querySelector("#live-update-status");
const liveLabels = {
    pass_complete: "Pase completo", pass_incomplete: "Pase incompleto", passing_touchdown: "Pase de touchdown · +6",
    touchdown: "Touchdown · +6", extra_one: "Extra · +1", extra_two: "Extra · +2", safety: "Safety · +2",
    sack: "Sack", flag: "Flag retirado", interception: "Intercepción", attendance: "Asistencia",
};
let liveData = null;
let liveUser = null;
let liveBusy = false;
let liveFetching = false;
let liveForcePending = false;
let liveTimer;
let liveFailures = 0;
let liveQueue = null;
let liveEditing = null;
let liveCaptureSaving = 0;
let liveLastTap = null;
const livePassers = new Map();
const liveActors = new Map();
const liveShortLabels = {pass_complete:"Pase completo",pass_incomplete:"Incompleto",passing_touchdown:"TD por pase",touchdown:"TD carrera / retorno",extra_one:"Extra +1",extra_two:"Extra +2",safety:"Safety",sack:"Sack",flag:"Flag",interception:"Intercepción",attendance:"Asistencia"};

function liveIsPass(kind) { return ["pass_complete","pass_incomplete","passing_touchdown"].includes(kind); }

function liveSelectTeam(id) {
    liveForm.elements.team_id.value = String(id);
    liveOptions();
}

function liveRememberPlayer() {
    const team = Number(liveForm.elements.team_id.value);
    const player = liveForm.elements.player_id.value;
    (liveIsPass(liveForm.elements.kind.value) ? livePassers : liveActors).set(team, player);
    renderLiveQuickControls();
    if (liveIsPass(liveForm.elements.kind.value) && liveForm.elements.kind.value !== "pass_incomplete") document.querySelector("#live-passer-choices").open = !player;
}

function liveSelectKind(kind) {
    liveForm.elements.kind.value = kind;
    const team = Number(liveForm.elements.team_id.value);
    liveForm.elements.player_id.value = (liveIsPass(kind) ? livePassers : liveActors).get(team) || "";
    liveForm.elements.receiver_id.value = "";
    liveKindControls();
}

function renderLiveQuickControls() {
    if (!liveData) return;
    const teamId = Number(liveForm.elements.team_id.value);
    const kind = liveForm.elements.kind.value;
    const players = liveData.roster.filter(player => player.team_id === teamId);
    document.querySelector("#live-team-buttons").innerHTML = [liveData.home_team,liveData.away_team].map(team =>
        `<button type="button" data-live-team="${team.id}" aria-pressed="${team.id === teamId}">${escapeHtml(team.name)}</button>`
    ).join("");
    document.querySelector("#live-kind-buttons").innerHTML = Object.entries(liveShortLabels).map(([key,label]) =>
        `<button type="button" data-live-kind="${key}" aria-pressed="${key === kind}">${label}</button>`
    ).join("");
    for (const field of ["player_id","receiver_id"]) {
        const isReceiver = field === "receiver_id";
        const selected = liveForm.elements[field].value;
        const target = document.querySelector(isReceiver ? "#live-receiver-buttons" : "#live-player-buttons");
        target.innerHTML = players.length ? players.map(player =>
            `<button type="button" data-live-player="${player.player_id}" data-live-field="${field}" aria-pressed="${String(player.player_id) === selected}" ${isReceiver && String(player.player_id) === liveForm.elements.player_id.value ? "disabled" : ""}><strong>#${player.jersey_number}</strong><span>${escapeHtml(player.display_name)}</span></button>`
        ).join("") : '<p class="form-help">Este equipo no tiene jugadores en su roster. Agrégalos antes de capturar.</p>';
    }
    document.querySelector("#live-tap-hint").textContent = liveIsPass(kind) && kind !== "pass_incomplete"
        ? "Fija al pasador y toca al receptor para registrar el pase. El pasador se conserva."
        : "Toca el dorsal del jugador para registrar esta estadística.";
    const player = players.find(p => String(p.player_id) === liveForm.elements.player_id.value);
    const receiver = players.find(p => String(p.player_id) === liveForm.elements.receiver_id.value);
    document.querySelector("#live-passer-summary").textContent = player && liveIsPass(kind) ? `Pasador: #${player.jersey_number} ${player.display_name} · Cambiar` : liveIsPass(kind) ? "Selecciona al pasador" : "Selecciona al jugador";
    if (!player || !liveIsPass(kind) || kind === "pass_incomplete") document.querySelector("#live-passer-choices").open = true;
    document.querySelector("#live-selection-summary").textContent = `${liveShortLabels[kind]} · ${player ? "#" + player.jersey_number + " " + player.display_name : "Selecciona jugador"}${receiver ? " → #" + receiver.jersey_number + " " + receiver.display_name : ""}`;
}

function renderLiveOutbox(rows) {
    document.querySelector("#live-outbox").classList.toggle("hidden", !rows.length);
    document.querySelector("#live-queue-status").textContent = rows.length
        ? `${rows.length} jugada${rows.length === 1 ? "" : "s"} pendiente${rows.length === 1 ? "" : "s"} de confirmar${rows[0].status === "blocked" ? " · Requiere revisión" : rows[0].status === "retry" ? " · Reintentando" : ""}`
        : "Todo enviado · puedes seguir capturando";
    document.querySelector("#live-outbox-list").innerHTML = [...rows].reverse().map(row =>
        `<article class="live-pending-play"><strong>${escapeHtml(liveShortLabels[row.payload.kind])} · ${escapeHtml(row.labels.player)}${row.labels.receiver ? " → " + escapeHtml(row.labels.receiver) : ""}</strong><span>${escapeHtml(row.labels.team)} · P${row.payload.period} ${String(row.payload.minute).padStart(2,"0")}:${String(row.payload.second).padStart(2,"0")} · ${{pending:"En espera",sending:"Enviando",retry:"Pendiente de confirmación",blocked:"No aceptada"}[row.status] || "En espera"}</span>${row.error ? `<p>${escapeHtml(row.error)}</p>` : ""}${row.status === "blocked" && row.httpStatus === 422 ? `<button type="button" class="secondary-button" data-live-edit="${row.id}">Corregir selección</button>` : ""}</article>`
    ).join("");
    document.querySelector("#live-finish").disabled = Boolean(rows.length || liveQueue?.working || liveBusy || liveCaptureSaving);
}

function liveQueueError(error) {
    liveMessage.textContent = `No se pudo guardar la captura local: ${error.message}. Conserva esta pantalla abierta y reintenta.`;
}

async function initializeLiveQueue() {
    if (!liveHasRole("referee")) return;
    try {
        const store = new LiveCaptureStore(`game:${liveGameId}:user:${liveUser.id}`);
        await store.open();
        liveQueue = new LiveCaptureQueue({
            store, send: payload => liveWrite("events", payload),
            onChange: renderLiveOutbox, onConfirmed: () => refreshLive(true),
            onError: liveQueueError,
            canSend: () => Boolean(liveData?.state === "live" && !liveBusy && navigator.onLine !== false),
        });
        await liveQueue.reload();
    } catch (error) {
        liveQueue = null;
        liveMessage.textContent = "No se pudo abrir el guardado local. La captura está desactivada para evitar perder jugadas. Recarga o prueba otro navegador.";
        document.querySelector("#live-save-play").disabled = true;
        document.querySelector("#live-finish").disabled = true;
    }
}

function liveCapturePayload() {
    const field = name => liveForm.elements[name].value;
    return {kind:field("kind"),team_id:Number(field("team_id")),player_id:field("player_id") ? Number(field("player_id")) : null,receiver_id:liveForm.elements.receiver_id.disabled || !field("receiver_id") ? null : Number(field("receiver_id")),period:Number(field("period")),minute:Number(field("minute")),second:Number(field("second"))};
}

async function liveCapturePlay() {
    if (liveBusy || !liveQueue || !liveHasRole("referee") || liveData?.state !== "live") return;
    if (!liveForm.reportValidity()) return;
    const payload = liveCapturePayload();
    if (payload.receiver_id === payload.player_id) { liveMessage.textContent = "Selecciona un receptor distinto al pasador."; return; }
    const signature = JSON.stringify(payload);
    if (!liveEditing && liveLastTap?.signature === signature && Date.now() - liveLastTap.at < 400) return;
    const tap = {signature,at:Date.now()};
    liveLastTap = tap;
    liveCaptureSaving += 1;
    try {
        const players = liveData.roster.filter(player => player.team_id === payload.team_id);
        const label = id => { const player = players.find(p => p.player_id === id); return player ? `#${player.jersey_number} ${player.display_name}` : ""; };
        const labels = {player:label(payload.player_id),receiver:label(payload.receiver_id),team:payload.team_id === liveData.home_team.id ? liveData.home_team.name : liveData.away_team.name};
        if (liveEditing) await liveQueue.replace(liveEditing, payload, labels);
        else await liveQueue.enqueue({...payload,client_id:crypto.randomUUID()}, labels);
        liveEditing = null;
        document.querySelector("#live-save-play").textContent = "Registrar jugada";
        liveMessage.textContent = `${liveShortLabels[payload.kind]} · ${labels.player}${labels.receiver ? " → " + labels.receiver : ""}. Guardada en este dispositivo; esperando confirmación.`;
        document.querySelector("#live-last-capture").textContent = `Última captura: ${liveShortLabels[payload.kind]} · ${labels.player}${labels.receiver ? " → " + labels.receiver : ""}`;
        if (payload.receiver_id && Number(liveForm.elements.receiver_id.value) === payload.receiver_id && Number(liveForm.elements.team_id.value) === payload.team_id && liveForm.elements.kind.value === payload.kind) liveForm.elements.receiver_id.value = "";
        renderLiveQuickControls();
        liveQueue.flush().catch(liveQueueError);
    } catch (error) { if (liveLastTap === tap) liveLastTap = null; liveQueueError(error); }
    finally { liveCaptureSaving -= 1; }
}

function liveHasRole(role) { return Boolean(liveUser && (liveUser.roles || [liveUser.role]).includes(role)); }
function liveOptions() {
    if (!liveData) return;
    const teamId = Number(liveForm.elements.team_id.value);
    const players = liveData.roster.filter(player => player.team_id === teamId);
    for (const field of ["player_id", "receiver_id"]) {
        const selected = field === "player_id" ? (liveIsPass(liveForm.elements.kind.value) ? livePassers : liveActors).get(teamId) || "" : "";
        liveForm.elements[field].innerHTML = '<option value="">Selecciona jugador</option>' + players.map(player =>
            `<option value="${player.player_id}">#${player.jersey_number} ${escapeHtml(player.display_name)}</option>`
        ).join("");
        liveForm.elements[field].value = players.some(player => String(player.player_id) === selected) ? selected : "";
    }
    liveKindControls();
    document.querySelector("#live-passer-choices").open = !liveForm.elements.player_id.value || liveForm.elements.receiver_id.disabled;
}

function liveKindControls() {
    const kind = liveForm.elements.kind.value;
    const hasReceiver = ["pass_complete", "passing_touchdown"].includes(kind);
    document.querySelector("#live-receiver-field").classList.toggle("hidden", !hasReceiver);
    liveForm.elements.receiver_id.disabled = !hasReceiver;
    liveForm.elements.receiver_id.required = hasReceiver;
    liveForm.elements.player_id.required = true;
    document.querySelector("#live-player-label").textContent = liveIsPass(kind) ? "Pasador · se conserva por equipo" : "Jugador";
    renderLiveQuickControls();
}

function liveNarrative(event, teamName) {
    const player = event.player_label || "Jugador";
    const receiver = event.receiver_label || "Receptor";
    const descriptions = {
        pass_complete: `${player} completa un pase con ${receiver}.`,
        pass_incomplete: `Pase incompleto de ${player}.`,
        passing_touchdown: `${player} conecta con ${receiver} para touchdown. +6 puntos.`,
        touchdown: `${player} anota un touchdown por carrera o retorno. +6 puntos.`,
        extra_one: `${player} consigue la conversión de 1 punto.`,
        extra_two: `${player} consigue la conversión de 2 puntos.`,
        safety: `${player} registra un safety. +2 puntos.`,
        sack: `${player} consigue un sack.`,
        flag: `${player} retira un flag.`,
        interception: `${player} intercepta el pase.`,
        attendance: `${player} queda registrado en la asistencia.`,
    };
    return `${teamName} · ${descriptions[event.kind] || "Registro histórico."}`;
}

function renderLive(data) {
    if (liveData && data.version < liveData.version) return;
    const previousState = liveData?.state;
    const rosterChanged = !liveData || JSON.stringify(liveData.roster) !== JSON.stringify(data.roster);
    const changed = !liveData || data.version !== liveData.version || data.state !== liveData.state;
    liveData = data;
    document.querySelector("#live-home-name").textContent = data.home_team.name;
    document.querySelector("#live-away-name").textContent = data.away_team.name;
    document.querySelector("#live-home-score").textContent = data.home_score ?? "—";
    document.querySelector("#live-away-score").textContent = data.away_score ?? "—";
    const state = document.querySelector("#live-state");
    state.dataset.state = data.state;
    state.textContent = {live:"En vivo", completed:"Finalizado", postponed:"Pospuesto", not_started:"Por iniciar"}[data.state];
    const official = liveHasRole("referee");
    document.querySelector("#live-official-controls").classList.toggle("hidden", !official);
    document.querySelector("#live-start").classList.toggle("hidden", data.state !== "not_started");
    document.querySelector("#live-capture-panel").classList.toggle("hidden", data.state !== "live");
    document.querySelector("#live-finish").classList.toggle("hidden", data.state !== "live");
    if (official && data.state === "live" && previousState !== "live") document.querySelector("#live-capture-panel").open = true;
    if (rosterChanged) {
        const selectedTeam = liveForm.elements.team_id.value;
        liveForm.elements.team_id.innerHTML = [data.home_team, data.away_team].map(team => `<option value="${team.id}">${escapeHtml(team.name)}</option>`).join("");
        if ([data.home_team.id, data.away_team.id].some(id => String(id) === selectedTeam)) liveForm.elements.team_id.value = selectedTeam;
        liveOptions();
    }
    if (changed) {
        document.querySelector("#live-timeline").innerHTML = data.events.length ? [...data.events].reverse().map(event => {
            const team = event.team_id === data.home_team.id ? data.home_team : data.away_team;
            const canCorrect = !event.voided_at && ((data.state === "live" && official) || (data.state === "completed" && liveHasRole("league_admin")));
            return `<article class="live-event ${event.voided_at ? "live-event-void" : ""}"><time>${String(event.minute).padStart(2,"0")}:${String(event.second).padStart(2,"0")}<small>Periodo ${event.period}</small></time>
                <div><h4>${liveLabels[event.kind] || "Registro histórico"}${event.voided_at ? " · Anulada" : ""}</h4><p>${escapeHtml(liveNarrative(event, team.name))}</p>
                ${canCorrect ? `<button type="button" class="secondary-button" data-void-event="${event.id}">Anular jugada</button>` : ""}</div></article>`;
        }).join("") : '<div class="empty-state"><h4>Aún no hay jugadas</h4><p>La cobertura aparecerá cuando el árbitro inicie la captura.</p></div>';
    }
    document.querySelector("#live-statistics").innerHTML = data.statistics.length ? `<table><thead><tr><th>Jugador / Equipo</th><th>PTS</th><th>REC</th><th>INT</th><th>SAC</th><th>FLG</th><th>PC/PI</th><th>PP</th><th>ASIS</th></tr></thead><tbody>${data.statistics.map(row => `<tr><td>#${row.jersey_number ?? "—"} ${escapeHtml(row.display_name)}<br><small>${escapeHtml(row.team_id === data.home_team.id ? data.home_team.name : data.away_team.name)}</small></td><td>${row.points}</td><td>${row.receptions}</td><td>${row.interceptions}</td><td>${row.sacks}</td><td>${row.tackles}</td><td>${row.passes_completed}/${row.passes_attempted}</td><td>${row.passing_points}</td><td>${row.attendance ? "Sí" : "—"}</td></tr>`).join("")}</tbody></table>` : '<div class="empty-state"><p>Sin estadísticas capturadas todavía.</p></div>';
    const updated = new Date().toLocaleTimeString("es-MX", {hour:"2-digit",minute:"2-digit",second:"2-digit"});
    liveStatus.textContent = data.state === "live" ? `Última actualización ${updated} · se actualiza automáticamente` : data.state === "completed" ? "Resultado final. La captura arbitral está cerrada." : "La cobertura se actualiza cuando el árbitro registra una jugada.";
    document.querySelector("#game-score").classList.add("hidden");
    if (official && liveQueue) {
        renderLiveOutbox(liveQueue.rows);
        if (data.state !== "live" && liveQueue.rows.length) liveMessage.textContent = "El partido está cerrado y hay capturas locales sin confirmar. Conserva este dispositivo y solicita revisión a un administrador.";
        liveQueue.flush().catch(liveQueueError);
    }
}

async function refreshLive(force = false) {
    clearTimeout(liveTimer);
    if (liveFetching) { if (force) liveForcePending = true; return; }
    if (document.hidden && !force) return;
    liveFetching = true;
    try {
        const response = await fetch(`/api/games/${liveGameId}/live${force ? `?refresh=${Date.now()}` : ""}`, {cache: force ? "no-store" : "default"});
        if (!response.ok) throw new Error("No se pudo consultar la cobertura.");
        renderLive(await response.json());
        liveFailures = 0;
    } catch {
        liveFailures += 1;
        liveStatus.textContent = "Sin conexión con la cobertura. Los datos visibles pueden estar desactualizados. Reintentando…";
    } finally {
        liveFetching = false;
        if (liveForcePending) { liveForcePending = false; return refreshLive(true); }
        if (!document.hidden && liveData?.state !== "completed" && liveData?.state !== "postponed") liveTimer = setTimeout(refreshLive, Math.min(60000, liveFailures ? 15000 * liveFailures : liveData?.state === "live" ? 12000 : 30000));
    }
}

async function liveWrite(path, body = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    let response;
    try {
        response = await fetch(`/api/games/${liveGameId}/live/${path}`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body),signal:controller.signal});
    } finally { clearTimeout(timeout); }
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        const detail = Array.isArray(error.detail)
            ? error.detail.map(item => item.msg || "Dato inválido").join(". ")
            : error.detail;
        const failure = new Error(typeof detail === "string" ? detail
            : response.status >= 500 ? "No se pudo completar la operación en el servidor. Intenta nuevamente."
            : response.status === 401 ? "Tu sesión terminó. Inicia sesión nuevamente."
            : response.status === 403 ? "Tu cuenta no tiene permiso para esta operación."
            : "No se pudo completar la operación.");
        failure.status = response.status;
        throw failure;
    }
    return response.json();
}

async function liveOperation(action, isPlay = false) {
    if (liveBusy || liveQueue?.working || liveQueue?.rows.length) { liveMessage.textContent = "Primero confirma las jugadas pendientes antes de corregir o finalizar."; return; }
    liveBusy = true;
    for (const id of ["#live-start","#live-finish","#live-save-play"]) document.querySelector(id).disabled = true;
    liveMessage.textContent = "Guardando…";
    try { await action(); await refreshLive(true); }
    catch (error) { liveMessage.textContent = `${error.message}${isPlay ? " Revisa la cronología antes de reenviar la jugada." : ""}`; }
    finally { liveBusy = false; for (const id of ["#live-start","#live-finish","#live-save-play"]) document.querySelector(id).disabled = false; if (liveQueue) renderLiveOutbox(liveQueue.rows); }
}

liveForm.elements.team_id.addEventListener("change", liveOptions);
liveForm.elements.kind.addEventListener("change", () => liveSelectKind(liveForm.elements.kind.value));
liveForm.elements.player_id.addEventListener("change", liveRememberPlayer);
liveForm.elements.receiver_id.addEventListener("change", renderLiveQuickControls);
liveForm.addEventListener("submit", event => { event.preventDefault(); liveCapturePlay(); });
document.querySelector("#live-capture-panel").addEventListener("click", event => {
    const team = event.target.closest("[data-live-team]");
    const kind = event.target.closest("[data-live-kind]");
    const player = event.target.closest("[data-live-player]");
    if (team) liveSelectTeam(team.dataset.liveTeam);
    if (kind) liveSelectKind(kind.dataset.liveKind);
    if (player && !player.disabled) {
        const field = player.dataset.liveField;
        liveForm.elements[field].value = player.dataset.livePlayer;
        if (field === "player_id") liveRememberPlayer();
        else renderLiveQuickControls();
        const quick = document.querySelector("#live-one-tap").checked;
        const receiverRequired = !liveForm.elements.receiver_id.disabled;
        if (quick && (field === "receiver_id" || !receiverRequired)) liveCapturePlay();
    }
});
document.querySelector("#live-retry").addEventListener("click", () => liveQueue?.retry().catch(liveQueueError));
document.querySelector("#live-outbox-list").addEventListener("click", event => {
    const button = event.target.closest("[data-live-edit]");
    if (!button || !liveQueue || liveBusy) return;
    const row = liveQueue.rows.find(row => row.id === button.dataset.liveEdit);
    if (!row || row.status !== "blocked" || row.httpStatus !== 422) return;
    liveSelectTeam(row.payload.team_id);
    liveSelectKind(row.payload.kind);
    for (const [field,value] of Object.entries(row.payload)) if (liveForm.elements[field]) liveForm.elements[field].value = value ?? "";
    liveRememberPlayer(); liveKindControls();
    liveEditing = row.id;
    document.querySelector("#live-one-tap").checked = false;
    document.querySelector("#live-save-play").textContent = "Guardar corrección";
    document.querySelector("#live-capture-panel").open = true;
    liveMessage.textContent = "Corrige la selección y guarda. La captura original se conserva hasta guardar la corrección.";
});
document.querySelector("#live-start").addEventListener("click", () => liveOperation(async () => {
    await liveWrite("start");
    document.querySelector("#live-capture-panel").open = true;
    liveMessage.textContent = "Captura en vivo iniciada.";
}));
document.querySelector("#live-finish").addEventListener("click", async () => {
    if (!liveQueue || liveCaptureSaving) return;
    try { await liveQueue.reload(); } catch (error) { liveQueueError(error); return; }
    if (liveQueue.rows.length || liveQueue.working) { liveMessage.textContent = "Hay jugadas sin confirmar. Envíalas antes de finalizar."; return; }
    if (!liveData || !window.confirm(`¿Finalizar ${liveData.home_team.name} ${liveData.home_score} – ${liveData.away_score} ${liveData.away_team.name}? Se publicarán las estadísticas y solo un administrador podrá corregirlas.`)) return;
    liveOperation(async () => {
        await liveWrite("finish", {expected_version:liveData.version});
        liveMessage.textContent = "Partido finalizado. Marcador y estadísticas publicados.";
        if (typeof loadGameDetail === "function") await loadGameDetail();
    });
});
document.querySelector("#live-timeline").addEventListener("click", event => {
    const button = event.target.closest("[data-void-event]");
    if (!button) return;
    const reason = window.prompt("Motivo de la anulación (mínimo 3 caracteres). La jugada quedará en el historial.");
    if (!reason || reason.trim().length < 3) return;
    liveOperation(async () => {
        await liveWrite(`events/${button.dataset.voidEvent}/void`, {reason:reason.trim(),expected_version:liveData.version});
        liveMessage.textContent = "Jugada anulada. Totales actualizados.";
    });
});
document.addEventListener("visibilitychange", () => { if (document.hidden) clearTimeout(liveTimer); else refreshLive(true); });
window.addEventListener("online", () => { refreshLive(true); liveQueue?.retry().catch(liveQueueError); });
window.addEventListener("beforeunload", event => { if (liveCaptureSaving || liveQueue?.rows.length) { event.preventDefault(); event.returnValue = ""; } });

(async () => {
    try { const response = await fetch("/api/auth/me", {cache:"no-store"}); if (response.ok) liveUser = await response.json(); } catch { /* Public feed remains available. */ }
    await initializeLiveQueue();
    await refreshLive();
})();
