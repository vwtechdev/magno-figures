(function () {
    function isHex(value) {
        return /^#[0-9a-fA-F]{6}$/.test(value || "");
    }

    document.querySelectorAll('input[data-color-field="true"]').forEach(function (text) {
        var picker = document.createElement("input");
        picker.type = "color";
        picker.value = isHex(text.value) ? text.value : "#0C0A09";
        picker.title = "Escolher cor";
        picker.style.cssText = "width: 40px; height: 30px; padding: 0; border: none; margin-left: 8px; vertical-align: middle; cursor: pointer;";
        picker.addEventListener("input", function () {
            text.value = picker.value.toUpperCase();
        });
        text.addEventListener("input", function () {
            if (isHex(text.value)) {
                picker.value = text.value;
            }
        });
        text.after(picker);
    });
})();
