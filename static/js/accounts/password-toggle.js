document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".auth__password").forEach((wrapper) => {
        const input = wrapper.querySelector("input[type='password']");
        const button = wrapper.querySelector(".auth__toggle");
        if (!input || !button) return;

        button.addEventListener("click", () => {
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            button.classList.toggle("is-visible", show);
            button.setAttribute(
                "aria-label",
                show ? "Ocultar senha" : "Mostrar senha"
            );
            input.focus();
        });
    });
});
