// Shared page enhancements, loaded by base.html before page scripts.
//
// 1. A <select data-segmented> renders as pill buttons (the games page
//    branch control). The select stays in the page as the source of truth:
//    buttons set it and fire "change", and they follow it back when a page
//    script changes it, hides its field (unified youth divisions) or fills
//    its options later.
// 2. A <form data-auto-submit> submits itself when one of its selects
//    changes, so a division filter needs no "Consultar" button.
// 3. setPageHero() fills a page band's tags and stats (see games.js).

function segmentedLabel(option) {
    if (option.dataset.short) return option.dataset.short;
    if (option.value === "") return "Todas";
    return option.textContent.trim();
}

function enhanceSegmentedSelect(select) {
    if (select.dataset.segmentedReady) return;
    select.dataset.segmentedReady = "true";
    const field = select.closest("label") || select;
    const group = document.createElement("div");
    group.className = "segmented";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", select.dataset.segmented || "Rama");
    // The buttons are the control people use; the select stays for the form.
    field.classList.add("segmented-source");
    field.setAttribute("aria-hidden", "true");
    select.tabIndex = -1;
    field.before(group);

    function build() {
        // A required select's empty option is a prompt ("Selecciona..."), not a choice.
        const choices = [...select.options].filter((option) => !(select.required && option.value === ""));
        group.replaceChildren(...choices.map((option) => {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.value = option.value;
            button.textContent = segmentedLabel(option);
            return button;
        }));
        sync();
    }

    function sync() {
        group.hidden = field.classList.contains("hidden") || select.disabled;
        group.querySelectorAll("button").forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.value === select.value));
        });
    }

    group.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-value]");
        if (!button || button.dataset.value === select.value) return;
        select.value = button.dataset.value;
        select.dispatchEvent(new Event("change", {bubbles: true}));
    });
    select.addEventListener("change", sync);
    new MutationObserver(build).observe(select, {childList: true});
    new MutationObserver(sync).observe(field, {attributes: true, attributeFilter: ["class"]});
    new MutationObserver(sync).observe(select, {attributes: true, attributeFilter: ["disabled"]});
    // Page scripts may set the value without an event (for example "Limpiar filtros").
    document.addEventListener("click", () => requestAnimationFrame(sync));
    build();
}

function enhanceAutoSubmitForm(form) {
    if (form.dataset.autoSubmitReady) return;
    form.dataset.autoSubmitReady = "true";
    form.addEventListener("change", (event) => {
        if (event.target.tagName !== "SELECT") return;
        // Wait for page listeners on the same event (division rules) first.
        requestAnimationFrame(() => {
            if (form.checkValidity()) form.requestSubmit();
        });
    });
}

function setPageHero({tags = [], stats = []} = {}) {
    const tagList = document.querySelector("#page-hero-tags");
    const statList = document.querySelector("#page-hero-stats");
    if (tagList) {
        tagList.replaceChildren(...tags.map(({label, tone}) => {
            const tag = document.createElement("span");
            tag.className = `hero-tag${tone ? ` hero-tag-${tone}` : ""}`;
            tag.textContent = label;
            return tag;
        }));
    }
    if (statList) {
        statList.replaceChildren(...stats.map(([value, label]) => {
            const item = document.createElement("li");
            const number = document.createElement("strong");
            const caption = document.createElement("span");
            number.textContent = String(value);
            caption.textContent = label;
            item.append(number, caption);
            return item;
        }));
        statList.hidden = stats.length === 0;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("select[data-segmented]").forEach(enhanceSegmentedSelect);
    document.querySelectorAll("form[data-auto-submit]").forEach(enhanceAutoSubmitForm);
});
