document.addEventListener("DOMContentLoaded", () => {
    const code = document.getElementById("trackingCode");
    const button = document.getElementById("copyTracking");
    const feedback = document.getElementById("trackingCopied");
    if (!code || !button) {
        return;
    }

    const showFeedback = () => {
        if (!feedback) return;
        feedback.hidden = false;
        setTimeout(() => {
            feedback.hidden = true;
        }, 2000);
    };

    const fallbackCopy = () => {
        const area = document.createElement("textarea");
        area.value = code.textContent.trim();
        document.body.appendChild(area);
        area.select();
        try {
            document.execCommand("copy");
            showFeedback();
        } catch {
            /* clipboard indisponível */
        }
        document.body.removeChild(area);
    };

    button.addEventListener("click", () => {
        const text = code.textContent.trim();
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(showFeedback, fallbackCopy);
        } else {
            fallbackCopy();
        }
    });
});
