(function () {
    function getCookie(name) {
        var cookies = document.cookie ? document.cookie.split(";") : [];
        for (var i = 0; i < cookies.length; i++) {
            var parts = cookies[i].trim().split("=");
            if (parts[0] === name) {
                return decodeURIComponent(parts.slice(1).join("="));
            }
        }
        return "";
    }

    document.querySelectorAll("[data-order-action]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var tab = window.open("", "_blank");
            fetch(btn.getAttribute("data-order-action"), {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "X-Requested-With": "XMLHttpRequest",
                },
            })
                .then(function (resp) {
                    return resp.json().then(function (data) {
                        return { status: resp.status, data: data };
                    });
                })
                .then(function (result) {
                    if (result.status === 200 && result.data.url) {
                        tab.location.href = result.data.url;
                    } else {
                        tab.close();
                        window.location.reload();
                    }
                })
                .catch(function () {
                    if (tab) tab.close();
                    window.location.reload();
                });
        });
    });
})();
