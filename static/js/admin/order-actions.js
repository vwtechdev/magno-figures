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

    function setStatusBadge(display, badgeClass) {
        var badge = document.getElementById("order-status");
        if (!badge) return;
        badge.textContent = display;
        badge.className = "mf-status-badge " + badgeClass;
        badge.classList.add("status-flash");
        setTimeout(function () {
            badge.classList.remove("status-flash");
        }, 900);
    }

    document.querySelectorAll("[data-order-action]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var isWhatsApp = btn.hasAttribute("data-whatsapp");
            var tab = isWhatsApp ? window.open("", "_blank") : null;
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
                        setStatusBadge(
                            result.data.status_display,
                            result.data.badge_class
                        );
                        tab.location.href = result.data.url;
                    } else if (result.status === 200 && result.data.ok) {
                        setStatusBadge(
                            result.data.status_display,
                            result.data.badge_class
                        );
                        if (tab) tab.close();
                    } else {
                        if (tab) tab.close();
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