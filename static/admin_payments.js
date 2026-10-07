// Administrator-only inscription ledger and manual payment capture.

const paymentsSummary = document.querySelector("#payments-summary");
const paymentsTeams = document.querySelector("#payments-teams");
const paymentsMessage = document.querySelector("#payments-message");
const teamFilter = document.querySelector("#payments-team-filter");
const statusFilter = document.querySelector("#payments-status-filter");
const paymentsCount = document.querySelector("#payments-count");

let paymentTeamsState = [];

const methodLabels = {
    cash: "Efectivo",
    transfer: "Transferencia"
};


function money(value) {
    return Number(value || 0).toLocaleString("es-MX", {
        style: "currency",
        currency: "MXN"
    });
}


function shortDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString("es-MX", {
        dateStyle: "medium",
        timeStyle: "short"
    });
}


function normalizedSearchText(value) {
    return String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase("es-MX")
        .trim();
}


function summaryMetric(label, value) {
    return `<div class="stat-item"><span>${label}</span><strong>${value}</strong></div>`;
}


function renderSummary(teams) {
    const totalFee = teams.reduce((total, team) => total + team.finance.registration_fee, 0);
    const totalPaid = teams.reduce((total, team) => total + team.finance.paid_amount, 0);
    const totalDue = teams.reduce((total, team) => total + team.finance.balance_due, 0);
    const teamsWithDebt = teams.filter((team) => team.finance.balance_due > 0).length;
    paymentsSummary.innerHTML = [
        summaryMetric("Equipos", teams.length),
        summaryMetric("Inscripción total", money(totalFee)),
        summaryMetric("Pagado", money(totalPaid)),
        summaryMetric("Adeudo", money(totalDue)),
        summaryMetric("Equipos con adeudo", teamsWithDebt)
    ].join("");
}


function paymentRows(payments) {
    if (payments.length === 0) {
        return `<tr><td colspan="6" class="table-empty-state">Sin pagos registrados.</td></tr>`;
    }
    return payments.map((payment) => `
        <tr>
            <td>${shortDate(payment.received_at)}</td>
            <td>${money(payment.amount)}</td>
            <td>${methodLabels[payment.method] || payment.method}</td>
            <td>${escapeHtml(payment.receiver_name || payment.recorded_by_name || "-")}</td>
            <td>${escapeHtml(payment.reference || "-")}</td>
            <td>${payment.has_proof
                ? `<a href="/api/admin/payments/${payment.id}/proof" target="_blank" rel="noopener">Ver</a>`
                : "-"}${payment.notes ? `<small>${escapeHtml(payment.notes)}</small>` : ""}</td>
        </tr>
    `).join("");
}


function renderTeamPaymentPanel(team) {
    const finance = team.finance;
    const status = finance.registration_fee <= 0
        ? "Sin monto"
        : finance.balance_due > 0 ? "Con adeudo" : "Liquidado";
    return `
        <section class="payment-team-panel" data-team-id="${team.id}">
            <header class="payment-team-header">
                <div>
                    <h3>${escapeHtml(team.name)}</h3>
                    <p>${escapeHtml(divisionBranchLabel(team.branch, team.category))} / ${escapeHtml(team.category)} · ${status}</p>
                </div>
                <strong class="${finance.balance_due > 0 ? "debt" : "paid"}">${money(finance.balance_due)}</strong>
            </header>

            <div class="stat-grid payment-team-metrics">
                ${summaryMetric("Inscripción", money(finance.registration_fee))}
                ${summaryMetric("Pagado", money(finance.paid_amount))}
                ${summaryMetric("Adeudo", money(finance.balance_due))}
                ${summaryMetric("Pagos", finance.payments.length)}
            </div>

            <details class="ui-disclosure"><summary>Registrar movimiento<span class="ui-disclosure-hint">Opciones</span></summary><div class="ui-disclosure-body payment-admin-forms">
                <form class="fee-form">
                    <label>Monto de inscripción<input name="amount" type="number" min="0" step="0.01" value="${finance.registration_fee}" required></label>
                    <button type="submit">Guardar monto</button>
                </form>
                <form class="payment-form">
                    <label>Monto recibido<input name="amount" type="number" min="0.01" step="0.01" required></label>
                    <label>Forma de pago<select name="method" required><option value="cash">Efectivo</option><option value="transfer">Transferencia</option></select></label>
                    <label>Quién recibió<input name="receiver_name" maxlength="120" placeholder="Nombre de quien recibió"></label>
                    <label>Referencia<input name="reference" maxlength="120" placeholder="Folio, banco o nota breve"></label>
                    <label>Comprobante<input name="proof" type="file" accept="image/png,image/jpeg,application/pdf"></label>
                    <label>Notas<textarea name="notes" rows="2" maxlength="500"></textarea></label>
                    <button type="submit">Registrar pago</button>
                </form>
            </div></details>

            ${finance.payments.length ? `<div class="table-scroll">
                <table class="standings-data-table payments-history-table">
                    <thead><tr><th>Fecha</th><th>Monto</th><th>Forma</th><th>Recibió</th><th>Referencia</th><th>Comprobante</th></tr></thead>
                    <tbody>${paymentRows(finance.payments)}</tbody>
                </table>
            </div>` : `<p class="payments-empty">Sin pagos registrados.</p>`}
        </section>
    `;
}


function filteredTeams() {
    const query = normalizedSearchText(teamFilter.value);
    const status = statusFilter.value;
    return paymentTeamsState.filter((team) => {
        const haystack = normalizedSearchText([
            team.name,
            divisionBranchLabel(team.branch, team.category),
            team.category
        ].join(" "));
        const matchesQuery = query === "" || haystack.includes(query);
        const matchesStatus = (
            status === "all"
            || (status === "debt" && team.finance.balance_due > 0)
            || (status === "paid" && team.finance.registration_fee > 0 && team.finance.balance_due === 0)
            || (status === "unset" && team.finance.registration_fee <= 0)
        );
        return matchesQuery && matchesStatus;
    });
}


function renderPayments() {
    const teams = filteredTeams();
    renderSummary(paymentTeamsState);
    paymentsCount.textContent = `${teams.length} equipo${teams.length === 1 ? "" : "s"}`;
    paymentsTeams.innerHTML = teams.length
        ? teams.map(renderTeamPaymentPanel).join("")
        : `<div class="empty-state"><h3>Sin resultados</h3><p>Ajusta los filtros para ver equipos.</p></div>`;
}


async function loadPayments() {
    const response = await getAdminTeamPayments();
    if (response.status === 401) return window.location.assign("/login");
    if (response.status === 403) return window.location.assign("/teams");
    if (!response.ok) throw new Error("Payments request failed");
    paymentTeamsState = await response.json();
    renderPayments();
}


paymentsTeams.addEventListener("submit", async (event) => {
    event.preventDefault();
    const panel = event.target.closest(".payment-team-panel");
    const submit = event.target.querySelector("button[type='submit']");
    submit.disabled = true;
    let response;
    if (event.target.classList.contains("fee-form")) {
        response = await updateTeamRegistrationFee(
            panel.dataset.teamId,
            event.target.elements.amount.value
        );
    } else if (event.target.classList.contains("payment-form")) {
        response = await createTeamPayment(panel.dataset.teamId, new FormData(event.target));
    }
    const body = await response?.json().catch(() => ({}));
    submit.disabled = false;
    if (!response?.ok) {
        paymentsMessage.textContent = body.detail || "No se pudo guardar el movimiento.";
        return;
    }
    paymentsMessage.textContent = "Movimiento guardado.";
    await loadPayments();
});


teamFilter.addEventListener("input", renderPayments);
statusFilter.addEventListener("change", renderPayments);


loadPayments().catch(() => {
    paymentsSummary.innerHTML = "";
    paymentsTeams.innerHTML = `<div class="empty-state"><h3>No se pudieron cargar los pagos</h3><p>Intenta recargar la página.</p></div>`;
});
