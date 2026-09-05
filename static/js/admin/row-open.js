(function () {
    document.addEventListener("click", function (event) {
        const row = event.target.closest("tr");
        if (!row || !row.closest("#result_list")) return;
        if (window.getSelection().toString().length > 0) return;
        if (
            event.target.closest(
                "a, input, button, select, th, .object-tools, .paginator, .actions"
            )
        ) {
            return;
        }
        const link = row.querySelector("th a[href$='/change/']");
        if (!link) return;
        window.location.href = link.href;
    });
})();