document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector(".navbar__search");
    const input = form
        ? form.querySelector(".navbar__search-input")
        : null;
    const submitBtn = form
        ? form.querySelector(".navbar__search-btn")
        : null;
    if (!form || !input) {
        return;
    }

    const magnifierHtml = submitBtn ? submitBtn.innerHTML : "";
    const clearHtml = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="18" height="18"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>';

    const showMagnifier = () => {
        if (!submitBtn) {
            return;
        }
        submitBtn.innerHTML = magnifierHtml;
        submitBtn.setAttribute("aria-label", "Buscar");
    };

    const showClear = () => {
        if (!submitBtn) {
            return;
        }
        submitBtn.innerHTML = clearHtml;
        submitBtn.setAttribute("aria-label", "Limpar pesquisa");
    };

    const syncIcon = () => {
        if (input.value) {
            showClear();
        } else {
            showMagnifier();
        }
    };

    if (submitBtn) {
        submitBtn.addEventListener("click", (event) => {
            if (input.value) {
                event.preventDefault();
                input.value = "";
                showMagnifier();
                close();
                input.focus();
            }
        });
    }

    input.addEventListener("blur", showMagnifier);

    const box = document.createElement("div");
    box.className = "search-suggest";
    box.hidden = true;
    document.body.appendChild(box);

    let timer = null;
    let seq = 0;

    const formatPrice = (value) =>
        `R$ ${Number(value).toFixed(2).replace(".", ",")}`;

    const close = () => {
        box.hidden = true;
        box.innerHTML = "";
    };

    const place = () => {
        const rect = input.getBoundingClientRect();
        box.style.top = `${rect.bottom + window.scrollY + 6}px`;
        box.style.left = `${rect.left + window.scrollX}px`;
        box.style.width = `${rect.width}px`;
    };

    const render = (results) => {
        box.innerHTML = "";
        if (!results.length) {
            close();
            return;
        }
        results.forEach((item) => {
            const link = document.createElement("a");
            link.className = "search-suggest__item";
            link.href = item.url;
            if (item.image) {
                const img = document.createElement("img");
                img.className = "search-suggest__thumb";
                img.src = item.image;
                img.alt = "";
                img.loading = "lazy";
                link.appendChild(img);
            }
            const info = document.createElement("div");
            info.className = "search-suggest__info";
            const name = document.createElement("div");
            name.className = "search-suggest__name";
            name.textContent = item.name;
            const price = document.createElement("div");
            price.className = "search-suggest__price";
            price.textContent = formatPrice(item.price);
            info.appendChild(name);
            info.appendChild(price);
            link.appendChild(info);
            box.appendChild(link);
        });
        place();
        box.hidden = false;
    };

    input.addEventListener("input", () => {
        clearTimeout(timer);
        syncIcon();
        const query = input.value.trim();
        if (query.length < 2) {
            close();
            return;
        }
        timer = setTimeout(async () => {
            const mine = ++seq;
            try {
                const response = await fetch(
                    `/figures/suggest/?q=${encodeURIComponent(query)}`
                );
                const data = await response.json();
                if (mine !== seq) {
                    return;
                }
                render(data.results || []);
            } catch (err) {
                if (mine === seq) {
                    close();
                }
            }
        }, 250);
    });

    input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            close();
        }
    });

    document.addEventListener("click", (event) => {
        if (!form.contains(event.target)) {
            close();
        }
    });

    document.addEventListener("scroll", () => {
        if (!box.hidden) {
            place();
        }
    }, { passive: true });

    window.addEventListener("resize", () => {
        if (!box.hidden) {
            close();
        }
    });

    form.addEventListener("submit", close);

    syncIcon();
});
