(function () {
    var form = document.getElementById("filtersForm");
    var results = document.getElementById("catalog-results");
    var toggle = document.getElementById("filtersToggle");
    var aside = document.getElementById("catalogFilters");
    if (!form || !results) {
        return;
    }

    function buildUrl() {
        var params = new URLSearchParams();
        var q = form.querySelector('input[name="q"]');
        if (q && q.value.trim()) {
            params.set("q", q.value.trim());
        }
        form.querySelectorAll('input[type="checkbox"]:checked').forEach(function (box) {
            params.append(box.name, box.value);
        });
        ["min_price", "max_price"].forEach(function (name) {
            var input = form.querySelector('input[name="' + name + '"]');
            if (input && input.value.trim()) {
                params.set(name, input.value.trim());
            }
        });
        var query = params.toString();
        var base = form.action.split("?")[0];
        return query ? base + "?" + query : base;
    }

    function closeDrawer() {
        if (aside) {
            aside.classList.remove("filters--open");
        }
        if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
        }
    }

    function load(url, scroll) {
        fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}})
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("request failed");
                }
                return response.json();
            })
            .then(function (data) {
                results.innerHTML = data.html;
                if (window.history && window.history.replaceState) {
                    window.history.replaceState(null, "", url);
                }
                closeDrawer();
                if (scroll) {
                    results.scrollIntoView({behavior: "smooth", block: "start"});
                }
            })
            .catch(function () {
                window.location.href = url;
            });
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        load(buildUrl(), false);
    });

    form.querySelectorAll('input[type="checkbox"]').forEach(function (box) {
        box.addEventListener("change", function () {
            load(buildUrl(), false);
        });
    });

    form.querySelectorAll(".filters__node-toggle").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var node = btn.closest(".filters__node");
            var open = node.classList.toggle("is-open");
            btn.setAttribute("aria-expanded", open ? "true" : "false");
        });
    });

    form.querySelectorAll('input[name="cat"]:checked').forEach(function (box) {
        var el = box;
        while (el) {
            var node = el.closest ? el.closest(".filters__node") : null;
            if (!node) {
                break;
            }
            node.classList.add("is-open");
            var btn = node.querySelector(":scope > .filters__node-row > .filters__node-toggle");
            if (btn) {
                btn.setAttribute("aria-expanded", "true");
            }
            el = node.parentElement;
        }
    });

    var debounceTimer = null;
    ["min_price", "max_price"].forEach(function (name) {
        var input = form.querySelector('input[name="' + name + '"]');
        if (!input) {
            return;
        }
        input.addEventListener("input", function () {
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }
            debounceTimer = setTimeout(function () {
                load(buildUrl(), false);
            }, 500);
        });
    });

    results.addEventListener("click", function (event) {
        var link = event.target.closest(".pagination a");
        if (!link) {
            return;
        }
        event.preventDefault();
        load(link.href, true);
    });

    if (toggle && aside) {
        toggle.addEventListener("click", function () {
            var open = aside.classList.toggle("filters--open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeDrawer();
            }
        });
    }
})();
