document.addEventListener("DOMContentLoaded", () => {
    const openBtn = document.getElementById("deleteAccountBtn");
    const modal = document.getElementById("deleteAccountModal");
    if (!openBtn || !modal) return;

    const open = () => {
        modal.hidden = false;
        const input = modal.querySelector('input[name="password"]');
        if (input) input.focus();
    };
    const close = () => {
        modal.hidden = true;
    };

    openBtn.addEventListener("click", open);
    modal.querySelectorAll("[data-close-modal]").forEach((el) => {
        el.addEventListener("click", close);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !modal.hidden) close();
    });
});
