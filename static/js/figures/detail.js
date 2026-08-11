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
    const formatPrice = (value) =>
        `R$ ${value.toFixed(2).replace(".", ",")}`;

    const renderOptions = (options) => {
        results.innerHTML = "";
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
                renderOptions(data.options);
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
});