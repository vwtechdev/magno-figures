document.addEventListener("DOMContentLoaded", () => {
    const mainImage = document.getElementById("productMainImage");
    const lightbox = document.getElementById("productLightbox");
    if (!mainImage || !lightbox) return;

    const thumbs = Array.from(document.querySelectorAll(".product__thumb"));
    const lightboxImage = document.getElementById("lightboxImage");
    const lightboxCount = document.getElementById("lightboxCount");
    const sources = [
        mainImage.src,
        ...thumbs.map((thumb) => thumb.querySelector("img").src),
    ];
    let current = 0;

    function sync(index) {
        current = (index + sources.length) % sources.length;
        mainImage.src = sources[current];
        mainImage.srcset = "";
        lightboxImage.src = sources[current];
        if (lightboxCount) {
            lightboxCount.textContent = `${current + 1} / ${sources.length}`;
        }
        thumbs.forEach((thumb, i) => {
            thumb.classList.toggle("is-active", i + 1 === current);
        });
    }

    function open(index) {
        sync(index);
        lightbox.classList.add("is-open");
        lightbox.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
    }

    function close() {
        lightbox.classList.remove("is-open");
        lightbox.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    mainImage.addEventListener("click", () => open(current));
    thumbs.forEach((thumb, i) => {
        thumb.addEventListener("click", () => sync(i + 1));
    });

    document.getElementById("lightboxClose").addEventListener("click", close);
    document.getElementById("lightboxPrev").addEventListener("click", () => sync(current - 1));
    document.getElementById("lightboxNext").addEventListener("click", () => sync(current + 1));

    lightbox.addEventListener("click", (event) => {
        if (event.target === lightbox) close();
    });

    document.addEventListener("keydown", (event) => {
        if (!lightbox.classList.contains("is-open")) return;
        if (event.key === "Escape") {
            close();
        } else if (event.key === "ArrowLeft") {
            sync(current - 1);
        } else if (event.key === "ArrowRight") {
            sync(current + 1);
        }
    });

    // ============ SHIPPING ============
    const zipInput = document.getElementById("zipCodeInput");
    const calcBtn = document.getElementById("btnCalcShipping");
    const results = document.getElementById("shippingResults");
    if (!zipInput || !calcBtn || !results) return;

    const product = document.querySelector("[data-figure-slug]");
    const figureSlug = product ? product.dataset.figureSlug : "";
    const shippingCard = document.getElementById("shipping");
    const figurePackage = shippingCard
        ? shippingCard.dataset.package || ""
        : "";
    const formatPrice = (value) =>
        `R$ ${value.toFixed(2).replace(".", ",")}`;

    // ============ CEP persistence (cookie + localStorage cache) ============
    const ZIP_COOKIE = "shipping_zip";
    const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

    const getCookie = (name) => {
        const match = document.cookie.match(
            new RegExp(`(?:^|; )${name}=([^;]*)`)
        );
        return match ? decodeURIComponent(match[1]) : "";
    };

    const setCookie = (name, value, days) => {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
    };

    const cacheKey = (zipcode) => `frete:${zipcode}:${figurePackage}`;

    const dropLegacyCache = () => {
        try {
            const stale = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (
                    key &&
                    key.startsWith("frete:") &&
                    !/^frete:\d{8}:/.test(key)
                ) {
                    stale.push(key);
                }
            }
            stale.forEach((key) => localStorage.removeItem(key));
        } catch (err) {
            // storage bloqueado: segue sem cache
        }
    };

    const readCache = (zipcode) => {
        try {
            const raw = localStorage.getItem(cacheKey(zipcode));
            if (!raw) return null;
            const entry = JSON.parse(raw);
            if (
                !entry ||
                !Array.isArray(entry.options) ||
                Date.now() - entry.ts > CACHE_TTL_MS
            ) {
                return null;
            }
            return entry;
        } catch (err) {
            return null;
        }
    };

    const writeCache = (zipcode, options, city) => {
        try {
            localStorage.setItem(
                cacheKey(zipcode),
                JSON.stringify({
                    ts: Date.now(),
                    options,
                    city: city || "",
                })
            );
        } catch (err) {
            // storage cheio/bloqueado: segue sem cache
        }
    };

    const renderOptions = (zipcode, options, city) => {
        results.innerHTML = "";
        const dest = document.createElement("div");
        dest.className = "shipping__dest";
        dest.textContent = `Destino: ${zipcode.slice(0, 5)}-${zipcode.slice(5)}${city ? ` — ${city}` : ""}`;
        results.appendChild(dest);
        options.forEach((option) => {
            const div = document.createElement("div");
            div.className = "shipping__option";
            div.innerHTML = `
                <div>
                    <div class="shipping__option-name">${option.name}</div>
                    <div class="shipping__option-meta">${option.delivery_time} dia(s) útil(is)</div>
                </div>
                <div class="shipping__option-price">${formatPrice(option.price)}</div>`;
            results.appendChild(div);
        });
    };

    const enrichDestination = async (zipcode, options) => {
        const dest = results.querySelector(".shipping__dest");
        if (!dest) return;
        const base = `Destino: ${zipcode.slice(0, 5)}-${zipcode.slice(5)}`;
        try {
            const response = await fetch(`https://viacep.com.br/ws/${zipcode}/json/`);
            const data = await response.json();
            if (data && !data.erro && data.localidade) {
                const city = `${data.localidade}/${data.uf}`;
                dest.textContent = `${base} — ${city}`;
                writeCache(zipcode, options, city);
            }
        } catch (err) {
            // mantém apenas o CEP
        }
    };

    const showMessage = (message, isError) => {
        results.innerHTML = "";
        const div = document.createElement("div");
        div.className = `shipping__msg${isError ? " shipping__msg--error" : ""}`;
        div.textContent = message;
        results.appendChild(div);
    };

    const calculate = async () => {
        const zipcode = zipInput.value.replace(/\D/g, "");
        if (!/^\d{8}$/.test(zipcode)) {
            showMessage("Informe um CEP válido (8 dígitos).", true);
            return;
        }
        calcBtn.disabled = true;
        calcBtn.textContent = "Calculando...";
        showMessage("Consultando fretes...");

        try {
            const response = await fetch(`/figures/${figureSlug}/shipping/?zipcode=${zipcode}`);
            const data = await response.json();
            if (!response.ok || data.error) {
                showMessage(data.error || "Não foi possível calcular o frete.", true);
            } else if (!data.options || data.options.length === 0) {
                showMessage("Nenhuma opção de frete disponível para este CEP.");
            } else {
                setCookie(ZIP_COOKIE, zipcode, 30);
                writeCache(zipcode, data.options, "");
                renderOptions(zipcode, data.options, "");
                enrichDestination(zipcode, data.options);
            }
        } catch (err) {
            showMessage("Erro de conexão. Tente novamente.", true);
        } finally {
            calcBtn.disabled = false;
            calcBtn.textContent = "Calcular";
        }
    };

    const maskZipCode = (value) => {
        const digits = value.replace(/\D/g, "").slice(0, 8);
        if (digits.length > 5) {
            return `${digits.slice(0, 5)}-${digits.slice(5)}`;
        }
        return digits;
    };

    zipInput.addEventListener("input", () => {
        zipInput.value = maskZipCode(zipInput.value);
    });

    calcBtn.addEventListener("click", calculate);
    zipInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") calculate();
    });

    // Prefill saved ZIP; render cached options without API calls.
    dropLegacyCache();
    const savedZip = getCookie(ZIP_COOKIE).replace(/\D/g, "");
    if (/^\d{8}$/.test(savedZip)) {
        zipInput.value = maskZipCode(savedZip);
        const cached = readCache(savedZip);
        if (cached) {
            renderOptions(savedZip, cached.options, cached.city);
            if (!cached.city) {
                enrichDestination(savedZip, cached.options);
            }
        }
    }
});