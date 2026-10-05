// Shared identity controls for account registration and managed rosters.
function calendarAgeFromBirthDate(value, today = new Date()) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return null;
    const [year, month, day] = value.split("-").map(Number);
    const birth = new Date(year, month - 1, day);
    if (birth.getFullYear() !== year || birth.getMonth() !== month - 1 || birth.getDate() !== day) return null;
    if (birth > today) return null;
    return today.getFullYear() - year - (
        today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day) ? 1 : 0
    );
}

function updatePlayerIdentityFields(form) {
    const provisional = form.elements.identity_type.value === "provisional";
    const documentInput = form.elements.curp;
    const birthInput = form.elements.birth_date;
    const today = new Date();
    birthInput.max = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    documentInput.minLength = provisional ? 1 : 18;
    documentInput.maxLength = provisional ? 17 : 18;
    form.querySelector("[data-identity-label]").textContent = provisional ? "Identificador del documento escolar o provisional" : "CURP";
    form.querySelector("[data-birth-date-field]").classList.toggle("hidden", !provisional);
    birthInput.required = provisional;
    birthInput.disabled = !provisional;
    updatePlayerIdentityAge(form);
}

function updatePlayerIdentityAge(form) {
    const age = form.elements.identity_type.value === "provisional"
        ? calendarAgeFromBirthDate(form.elements.birth_date.value)
        : calendarAgeFromCurp(form.elements.curp.value);
    form.elements.age.value = age ?? "";
}

function bindPlayerIdentityFields(form) {
    form.elements.identity_type.addEventListener("change", () => updatePlayerIdentityFields(form));
    form.elements.curp.addEventListener("input", () => updatePlayerIdentityAge(form));
    form.elements.birth_date.addEventListener("input", () => updatePlayerIdentityAge(form));
    updatePlayerIdentityFields(form);
}
