document.addEventListener("DOMContentLoaded", () => {
    const track = document.getElementById("heroTrack");
    if (!track) return;

    const prev = document.getElementById("heroPrev");
    const next = document.getElementById("heroNext");
    const dotsWrap = document.getElementById("heroDots");
    const slides = track.children.length;
    let current = 0;
    let timer;

    function goTo(index) {
        current = (index + slides) % slides;
        track.style.transform = `translateX(-${current * 100}%)`;
        updateDots();
        restart();
    }

    function updateDots() {
        if (!dotsWrap) return;
        dotsWrap.querySelectorAll(".hero__dot").forEach((dot, i) => {
            dot.classList.toggle("is-active", i === current);
        });
    }

    function buildDots() {
        if (!dotsWrap) return;
        dotsWrap.innerHTML = "";
        for (let i = 0; i < slides; i++) {
            const dot = document.createElement("button");
            dot.className = "hero__dot";
            dot.setAttribute("aria-label", `Ir para slide ${i + 1}`);
            dot.addEventListener("click", () => goTo(i));
            dotsWrap.appendChild(dot);
        }
        updateDots();
    }

    function restart() {
        clearInterval(timer);
        timer = setInterval(() => goTo(current + 1), 6000);
    }

    if (prev) prev.addEventListener("click", () => goTo(current - 1));
    if (next) next.addEventListener("click", () => goTo(current + 1));

    buildDots();
    restart();

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            clearInterval(timer);
        } else {
            restart();
        }
    });

    // ============ CATALOG CAROUSEL ============
    const catalog = document.getElementById("catalogScroll");
    const catalogPrev = document.getElementById("catalogPrev");
    const catalogNext = document.getElementById("catalogNext");

    if (catalog && catalogPrev && catalogNext) {
        const step = () => {
            const card = catalog.querySelector(".card");
            if (!card) return 0;
            const gap = parseInt(getComputedStyle(catalog).columnGap, 10) || 24;
            return card.offsetWidth + gap;
        };

        const updateArrows = () => {
            catalogPrev.disabled = catalog.scrollLeft <= 5;
            catalogNext.disabled =
                catalog.scrollLeft + catalog.clientWidth >= catalog.scrollWidth - 5;
        };

        catalogPrev.addEventListener("click", () =>
            catalog.scrollBy({ left: -step(), behavior: "smooth" })
        );
        catalogNext.addEventListener("click", () =>
            catalog.scrollBy({ left: step(), behavior: "smooth" })
        );

        catalog.addEventListener("scroll", updateArrows, { passive: true });
        window.addEventListener("resize", updateArrows);
        updateArrows();
    }
});