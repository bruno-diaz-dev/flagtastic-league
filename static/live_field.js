// Lightweight, illustrative coverage. Coordinates are never inferred as real tracking.
(function (root) {
    "use strict";
    const LABELS = {pass_complete:"Pase completo",pass_incomplete:"Pase incompleto",passing_touchdown:"Touchdown por pase",touchdown:"Touchdown por carrera / retorno",extra_one:"Extra de 1 punto",extra_two:"Extra de 2 puntos",safety:"Safety",sack:"Sack",flag:"Flag retirado",interception:"Intercepción",halftime:"Medio tiempo",two_minute_warning:"Pausa de los 2 minutos"};
    const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    function eligibleEvents(data) { return (data.events || []).filter(event => !event.voided_at && Object.hasOwn(LABELS, event.kind)); }
    function fieldMarkup(event, animated) {
        const located = root.fieldLocationMarkup?.(event, animated);
        if (located) return located;
        const kind = event?.kind;
        const moment = kind === "halftime" || kind === "two_minute_warning";
        const pass = ["pass_complete","pass_incomplete","passing_touchdown","interception"].includes(kind);
        const touchdown = kind === "touchdown" || kind === "passing_touchdown";
        const endX = touchdown ? 540 : kind === "safety" ? 60 : pass ? 440 : 340;
        const endY = pass ? 125 : 205;
        const path = pass ? `M 145 205 Q 285 35 ${endX} ${endY}` : `M 145 205 L ${endX} ${endY}`;
        const jersey = label => label?.match(/^#(\d+)/)?.[1] || "•";
        const marker = (x,y,label) => `<g class="live-field-player"><circle cx="${x}" cy="${y}" r="19"/><text x="${x}" y="${y+5}">${esc(jersey(label))}</text></g>`;
        let drawing = "";
        if (event && !moment) {
            drawing = `<path class="live-field-route ${animated ? "live-field-draw" : ""} ${kind === "pass_incomplete" ? "live-field-incomplete" : ""}" d="${path}" pathLength="1"/>${marker(145,205,event.player_label)}`;
            if (pass && event.receiver_label) drawing += marker(endX,endY,event.receiver_label);
            if (kind === "pass_incomplete") drawing += `<path d="M ${endX-10} ${endY-10} l 20 20 m 0 -20 l -20 20" class="live-field-miss"/>`;
            drawing += `<g class="live-field-ball" ${animated ? "" : `transform="translate(${endX} ${endY})"`}><ellipse rx="12" ry="7"/><path d="M -5 0 H 5 M -3 -3 V 3 M 0 -3 V 3 M 3 -3 V 3"/>${animated ? `<animateMotion dur="1.3s" repeatCount="1" fill="freeze" path="${path}"/>` : ""}</g>`;
        }
        return `<svg viewBox="0 0 600 300" role="img" aria-label="${esc(event ? LABELS[kind] + '. Recorrido ilustrativo.' : 'Campo de flag. Esperando capturas confirmadas.')}" xmlns="http://www.w3.org/2000/svg"><rect class="live-field-turf" x="10" y="10" width="580" height="280" rx="12"/><rect class="live-field-endzone" x="11" y="11" width="69" height="278" rx="10"/><rect class="live-field-endzone" x="520" y="11" width="69" height="278" rx="10"/>${[80,135,190,245,300,355,410,465,520].map(x=>`<path class="live-field-lines" d="M ${x} 12 V 288"/>`).join("")}<path class="live-field-boundary" d="M 80 12 H 520 V 288 H 80 Z"/><text class="live-field-zone-label" transform="translate(45 150) rotate(-90)">ZONA DE ANOTACIÓN</text><text class="live-field-zone-label" transform="translate(555 150) rotate(90)">ZONA DE ANOTACIÓN</text><text class="live-field-brand" x="300" y="160">FLAGTASTIC</text>${drawing}</svg>${moment || touchdown || ["sack","flag","interception","safety","extra_one","extra_two"].includes(kind) ? `<div class="live-field-banner ${touchdown ? "live-field-td" : ""} ${animated ? "live-field-celebrate" : ""}"><strong>${touchdown ? "¡TOUCHDOWN!" : esc(LABELS[kind])}</strong>${touchdown ? "<span>+6 puntos confirmados</span>" : ""}</div>` : ""}`;
    }
    class LiveFieldView {
        constructor(element, options = {}) {
            this.root = element;
            this.reducedMotion = options.reducedMotion || (() => Boolean(root.matchMedia?.("(prefers-reduced-motion: reduce)").matches));
            this.hidden = options.hidden || (() => Boolean(root.document?.hidden));
            this.chart = typeof root.LivePassChart !== "undefined" ? new root.LivePassChart(element, id => this.show(id)) : null;
            this.data = null;
            this.latestId = null;
            this.selectedId = null;
            this.initialized = false;
            this.root.querySelector("#live-field-replay").addEventListener("click", () => this.show(this.selectedId, true));
        }
        update(data) {
            this.chart?.update(data);
            const events = eligibleEvents(data);
            const latest = events.at(-1);
            const newPlay = this.initialized && latest && latest.id !== this.latestId && latest.id > (this.latestId ?? 0);
            const selectedStillValid = events.some(event => event.id === this.selectedId);
            this.data = data;
            if (!this.initialized || newPlay || !selectedStillValid) this.show(latest?.id ?? null, Boolean(newPlay));
            this.latestId = latest?.id ?? null;
            this.initialized = true;
        }
        show(id, animate = true) {
            const event = eligibleEvents(this.data || {}).find(event => event.id === id);
            this.selectedId = event?.id ?? null;
            this.root.dataset.eventId = event ? String(event.id) : "";
            const animated = Boolean(event && animate && !this.reducedMotion() && !this.hidden());
            const team = event?.team_id === this.data?.home_team?.id ? this.data.home_team : event?.team_id === this.data?.away_team?.id ? this.data.away_team : null;
            this.root.dataset.team = team?.id === this.data?.away_team?.id ? "away" : "home";
            this.root.querySelector("#live-field-stage").innerHTML = fieldMarkup(event, animated);
            this.root.querySelector("#live-field-title").textContent = event ? LABELS[event.kind] : "La cancha, jugada a jugada";
            this.root.querySelector("#live-field-caption").textContent = event ? [team?.name,event.player_label,event.receiver_label ? "→ " + event.receiver_label : null,`P${event.period} ${String(event.minute).padStart(2,"0")}:${String(event.second).padStart(2,"0")}`].filter(Boolean).join(" · ") : "El campo se actualizará cuando haya una captura confirmada.";
            this.root.querySelector("#live-field-replay").disabled = !event;
        }
    }
    root.LiveFieldView = LiveFieldView;
    if (typeof module !== "undefined" && module.exports) module.exports = {LiveFieldView,fieldMarkup,eligibleEvents};
})(typeof globalThis !== "undefined" ? globalThis : window);

