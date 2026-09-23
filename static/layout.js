// Shared sidebar behavior applies consistently across every operations page.

const sidebarToggle = document.querySelector("#sidebar-toggle");

if (sidebarToggle !== null) {
    sidebarToggle.addEventListener("click", () => {
        const isCollapsed = document.body.classList.toggle("sidebar-collapsed");

        sidebarToggle.setAttribute("aria-expanded", String(!isCollapsed));
        sidebarToggle.setAttribute(
            "aria-label",
            isCollapsed ? "Expandir menu" : "Contraer menu"
        );
    });
}
