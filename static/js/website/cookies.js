document.addEventListener("DOMContentLoaded", () => {
    const bar = document.getElementById("cookieBar");
    const accept = document.getElementById("cookieAccept");
    const reject = document.getElementById("cookieReject");
    if (!bar || !accept || !reject) return;

    const KEY = "mf-cookie-consent";
    const hasChoice = () => {
        try {
            return ["granted", "denied"].includes(
                window.localStorage.getItem(KEY)
            );
        } catch (e) {
            return true;
        }
    };

    if (hasChoice()) return;

    const setChoice = (value) => {
        try {
            window.localStorage.setItem(KEY, value);
        } catch (e) {
            /* sem persistência local: registra só o cookie */
        }
        document.cookie =
            "mf_cookie_consent=" +
            value +
            "; max-age=31536000; path=/; SameSite=Lax";
    };

    const hide = () => {
        bar.classList.remove("is-visible");
        window.setTimeout(() => {
            bar.hidden = true;
        }, 300);
    };

    bar.hidden = false;
    requestAnimationFrame(() => bar.classList.add("is-visible"));

    accept.addEventListener("click", () => {
        setChoice("granted");
        hide();
        if (bar.dataset.ga === "1") {
            window.setTimeout(() => window.location.reload(), 320);
        }
    });

    reject.addEventListener("click", () => {
        setChoice("denied");
        hide();
    });
});
