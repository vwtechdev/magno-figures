document.addEventListener("DOMContentLoaded", () => {
    const bar = document.getElementById("cookieBar");
    const accept = document.getElementById("cookieAccept");
    if (!bar || !accept) return;

    try {
        if (window.localStorage.getItem("mf-cookie-consent") === "1") return;
    } catch (e) {
        return;
    }

    bar.hidden = false;
    requestAnimationFrame(() => bar.classList.add("is-visible"));

    accept.addEventListener("click", () => {
        try {
            window.localStorage.setItem("mf-cookie-consent", "1");
        } catch (e) {
            /* sem persistência: apenas oculta */
        }
        bar.classList.remove("is-visible");
        window.setTimeout(() => {
            bar.hidden = true;
        }, 300);
    });
});
