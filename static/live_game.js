// Live sporting feed; refresh only while visible and never overlap requests.
const liveRoot = document.querySelector("#live-match");
const liveGameId = document.querySelector(".game-detail-page").dataset.gameId;
const liveForm = document.querySelector("#live-event-form");
const liveMessage = document.querySelector("#live-operation-message");
const liveStatus = document.querySelector("#live-update-status");
const liveLabels = {
    pass_complete: "Pase completo", pass_incomplete: "Pase incompleto", passing_touchdown: "Pase de touchdown · +6",
    touchdown: "Touchdown · +6", extra_one: "Extra · +1", extra_two: "Extra · +2", safety: "Safety · +2",
    sack: "Sack", flag: "Flag retirado", interception: "Intercepción", attendance: "Asistencia", note: "Observación",
};
let liveData = null;
let liveUser = null;
let liveBusy = false;
let liveFetching = false;
let liveForcePending = false;
let liveTimer;
let liveFailures = 0;
let livePending = null;

function liveHasRole(role) { return Boolean(liveUser && (liveUser.roles || [liveUser.role]).includes(role)); }
function liveOptions() {
    if (!liveData) return;
    const teamId = Number(liveForm.elements.team_id.value);
    const players = liveData.roster.filter(player => player.team_id === teamId);
    for (const field of ["player_id", "receiver_id"]) {
        const selected = liveForm.elements[field].value;
        liveForm.elements[field].innerHTML = '<option value="">Selecciona jugador</option>' + players.map(player =>
            `<option value="${player.player_id}">#${player.jersey_number} ${escapeHtml(player.display_name)}</option>`
        ).join("");
        if (players.some(player => String(player.player_id) === selected)) liveForm.elements[field].value = selected;
    }
    liveKindControls();
}

function liveKindControls() {
    const kind = liveForm.elements.kind.value;
    const hasReceiver = ["pass_complete", "passing_touchdown"].includes(kind);
    document.querySelector("#live-receiver-field").classList.toggle("hidden", !hasReceiver);
    liveForm.elements.receiver_id.disabled = !hasReceiver;
    liveForm.elements.receiver_id.required = hasReceiver;
    liveForm.elements.player_id.required = kind !== "note";
    liveForm.elements.note.required = kind === "note";
    document.querySelector("#live-player-label").textContent = kind.startsWith("pass") ? "Pasador" : "Jugador";
}

function renderLive(data) {
    if (liveData && data.version < liveData.version) return;
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
                <div><h4>${liveLabels[event.kind]}${event.voided_at ? " · Anulada" : ""}</h4><p>${escapeHtml(team.name)}</p>
                ${event.player_label ? `<p>${escapeHtml(event.player_label)}${event.receiver_label ? ` → ${escapeHtml(event.receiver_label)}` : ""}</p>` : ""}
                ${event.note ? `<p>${escapeHtml(event.note)}</p>` : ""}
                ${canCorrect ? `<button type="button" class="secondary-button" data-void-event="${event.id}">Anular jugada</button>` : ""}</div></article>`;
        }).join("") : '<div class="empty-state"><h4>Aún no hay jugadas</h4><p>La cobertura aparecerá cuando el árbitro inicie la captura.</p></div>';
    }
    document.querySelector("#live-statistics").innerHTML = data.statistics.length ? `<table><thead><tr><th>Jugador / Equipo</th><th>PTS</th><th>REC</th><th>INT</th><th>SAC</th><th>FLG</th><th>PC/PI</th><th>PP</th><th>ASIS</th></tr></thead><tbody>${data.statistics.map(row => `<tr><td>#${row.jersey_number ?? "—"} ${escapeHtml(row.display_name)}<br><small>${escapeHtml(row.team_id === data.home_team.id ? data.home_team.name : data.away_team.name)}</small></td><td>${row.points}</td><td>${row.receptions}</td><td>${row.interceptions}</td><td>${row.sacks}</td><td>${row.tackles}</td><td>${row.passes_completed}/${row.passes_attempted}</td><td>${row.passing_points}</td><td>${row.attendance ? "Sí" : "—"}</td></tr>`).join("")}</tbody></table>` : '<div class="empty-state"><p>Sin estadísticas capturadas todavía.</p></div>';
    const updated = new Date().toLocaleTimeString("es-MX", {hour:"2-digit",minute:"2-digit",second:"2-digit"});
    liveStatus.textContent = data.state === "live" ? `Última actualización ${updated} · se actualiza automáticamente` : data.state === "completed" ? "Resultado final. La captura arbitral está cerrada." : "La cobertura se actualiza cuando el árbitro registra una jugada.";
    document.querySelector("#game-score").classList.add("hidden");
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
    const response = await fetch(`/api/games/${liveGameId}/live/${path}`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        const detail = Array.isArray(error.detail)
            ? error.detail.map(item => item.msg || "Dato inválido").join(". ")
            : error.detail;
        throw new Error(typeof detail === "string" ? detail
            : response.status >= 500 ? "No se pudo completar la operación en el servidor. Intenta nuevamente."
            : response.status === 401 ? "Tu sesión terminó. Inicia sesión nuevamente."
            : response.status === 403 ? "Tu cuenta no tiene permiso para esta operación."
            : "No se pudo completar la operación.");
    }
    return response.json();
}

async function liveOperation(action, isPlay = false) {
    if (liveBusy) return;
    liveBusy = true;
    liveRoot.querySelectorAll("button").forEach(button => { button.disabled = true; });
    liveMessage.textContent = "Guardando…";
    try { await action(); await refreshLive(true); }
    catch (error) { liveMessage.textContent = `${error.message}${isPlay ? " Revisa la cronología antes de reenviar la jugada." : ""}`; }
    finally { liveBusy = false; liveRoot.querySelectorAll("button").forEach(button => {button.disabled = false;}); }
}

liveForm.elements.team_id.addEventListener("change", liveOptions);
liveForm.elements.kind.addEventListener("change", liveKindControls);
liveForm.addEventListener("submit", event => {
    event.preventDefault();
    const fields = new FormData(liveForm);
    const payload = {kind:fields.get("kind"),team_id:Number(fields.get("team_id")),player_id:fields.get("player_id") ? Number(fields.get("player_id")) : null,receiver_id:fields.get("receiver_id") ? Number(fields.get("receiver_id")) : null,period:Number(fields.get("period")),minute:Number(fields.get("minute")),second:Number(fields.get("second")),note:String(fields.get("note") || "").trim()};
    if (!livePending || livePending.signature !== JSON.stringify(payload)) livePending = {signature:JSON.stringify(payload),client_id:crypto.randomUUID()};
    const request = {...payload,client_id:livePending.client_id};
    liveOperation(async () => {
        await liveWrite("events", request);
        livePending = null;
        liveForm.elements.note.value = "";
        liveMessage.textContent = "Jugada registrada.";
    }, true);
});
document.querySelector("#live-start").addEventListener("click", () => liveOperation(async () => {
    await liveWrite("start");
    document.querySelector("#live-capture-panel").open = true;
    liveMessage.textContent = "Captura en vivo iniciada.";
}));
document.querySelector("#live-finish").addEventListener("click", () => {
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
window.addEventListener("online", () => refreshLive(true));

(async () => {
    try { const response = await fetch("/api/auth/me", {cache:"no-store"}); if (response.ok) liveUser = await response.json(); } catch { /* Public feed remains available. */ }
    await refreshLive();
})();
