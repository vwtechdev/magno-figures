document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-recaptcha-action]").forEach((form) => {
        const siteKey = form.dataset.recaptchaKey || "";
        const action = form.dataset.recaptchaAction || "";
        const tokenInput = form.querySelector(
            'input[name="g-recaptcha-response"]'
        );
        if (!siteKey || !action || !tokenInput) {
            return;
        }
        form.addEventListener("submit", (event) => {
            if (form.dataset.recaptchaDone === "1") {
                return;
            }
            if (typeof grecaptcha === "undefined") {
                return;
            }
            event.preventDefault();
            grecaptcha.ready(() => {
                grecaptcha
                    .execute(siteKey, { action })
                    .then((token) => {
                        tokenInput.value = token;
                        form.dataset.recaptchaDone = "1";
                        form.submit();
                    })
                    .catch(() => {
                        form.submit();
                    });
            });
        });
    });
});
