document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".profile__tab");
    const panels = document.querySelectorAll(".profile__panel");
    if (!tabs.length || !panels.length) return;

    const showTab = (name) => {
        tabs.forEach((tab) => {
            const active = tab.dataset.tab === name;
            tab.classList.toggle("is-active", active);
            tab.setAttribute("aria-selected", String(active));
        });
        panels.forEach((panel) => {
            const active = panel.dataset.panel === name;
            panel.classList.toggle("is-active", active);
            panel.hidden = !active;
        });
        const url = new URL(window.location);
        url.searchParams.set("tab", name);
        history.replaceState(null, "", url);
    };

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => showTab(tab.dataset.tab));
    });
});
