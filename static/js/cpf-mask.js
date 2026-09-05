const CPFMask = (() => {
    function onlyDigits(value) {
        return (value || "").replace(/\D/g, "").slice(0, 11);
    }

    function format(value) {
        const d = onlyDigits(value);
        if (d.length <= 3) return d;
        if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
        if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
        return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
    }

    function init(input) {
        if (!input) return;
        input.addEventListener("input", () => {
            input.value = format(input.value);
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("[data-cpf-mask]").forEach((input) => {
            init(input);
        });
    });

    return { init, format, onlyDigits };
})();