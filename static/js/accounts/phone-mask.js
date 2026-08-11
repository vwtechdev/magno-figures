function applyPhoneMask(input) {
    const digits = input.value.replace(/\D/g, "").slice(0, 11);
    if (!digits) {
        input.value = "";
        return;
    }

    let result = `(${digits.slice(0, 2)}`;
    if (digits.length <= 2) {
        input.value = result;
        return;
    }

    result += `) ${digits.slice(2)}`;

    const local = digits.slice(2);
    const split = digits.length > 10 ? 5 : 4;
    if (local.length > split) {
        result = `(${digits.slice(0, 2)}) ${local.slice(0, split)}-${local.slice(split)}`;
    }

    input.value = result;
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("input[data-phone-mask]").forEach((input) => {
        input.addEventListener("input", () => applyPhoneMask(input));
    });
});
