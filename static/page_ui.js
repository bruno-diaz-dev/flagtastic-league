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
// 4-5. skeletonMarkup() and emptyStateMarkup() (below).

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

// 4. skeletonMarkup() is a loading placeholder shaped like the content
//    ("games", "table" or "cards"); screen readers hear the label.
const SKELETON_SHAPES = {
    games: '<div class="skeleton-item skeleton-game"><span class="skeleton-bar skeleton-short"></span><span class="skeleton-bar"></span><span class="skeleton-bar skeleton-score"></span><span class="skeleton-bar"></span></div>',
    table: '<div class="skeleton-item skeleton-row"><span class="skeleton-bar skeleton-dot"></span><span class="skeleton-bar"></span><span class="skeleton-bar skeleton-short"></span><span class="skeleton-bar skeleton-short"></span></div>',
    cards: '<div class="skeleton-item skeleton-card"><span class="skeleton-bar skeleton-avatar"></span><span class="skeleton-bar"></span><span class="skeleton-bar skeleton-short"></span></div>',
};

function skeletonMarkup(shape = "games", count = 5, label = "Cargando") {
    const item = SKELETON_SHAPES[shape] || SKELETON_SHAPES.games;
    return `<div class="skeleton skeleton-${shape}" role="status" aria-busy="true"><span class="sr-only">${uiText(label)}…</span>${item.repeat(count)}</div>`;
}

// 5. emptyStateMarkup() is the shared empty state: an icon, a title, a line
//    of text and, where there is a next step, one action link or button.
const EMPTY_STATE_ICONS = {
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    trophy: '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4ZM7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4"/>',
    chart: '<path d="M4 20h16M7 16v-5M12 16V4M17 16V8"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    team: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6"/>',
    ball: '<ellipse cx="12" cy="12" rx="9.5" ry="5.5" transform="rotate(-35 12 12)"/><path d="m9 15 6-6M11 11l2 2M9.5 12.5l2 2M12.5 9.5l2 2"/>',
    alert: '<path d="M12 4 2.5 20h19L12 4Z"/><path d="M12 10v4M12 17h.01"/>',
};

function uiText(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
}

function emptyStateMarkup({icon = "ball", title, text = "", action = null, heading = "h3"} = {}) {
    const path = EMPTY_STATE_ICONS[icon] || EMPTY_STATE_ICONS.ball;
    let actionMarkup = "";
    if (action?.href) actionMarkup = `<a class="empty-state-action" href="${uiText(action.href)}">${uiText(action.label)}</a>`;
    else if (action?.id) actionMarkup = `<button type="button" id="${uiText(action.id)}" class="empty-state-action">${uiText(action.label)}</button>`;
    return `<div class="empty-state empty-state-rich">
        <span class="empty-state-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${path}</svg></span>
        <${heading}>${uiText(title)}</${heading}>
        ${text ? `<p>${uiText(text)}</p>` : ""}
        ${actionMarkup}
    </div>`;
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("select[data-segmented]").forEach(enhanceSegmentedSelect);
    document.querySelectorAll("form[data-auto-submit]").forEach(enhanceAutoSubmitForm);
});
