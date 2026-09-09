document.addEventListener("DOMContentLoaded", () => {
    const track = document.getElementById("heroTrack");

    if (track) {
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
    }

    // ============ SCROLL CAROUSELS (catalog, releases, promos) ============
    document.querySelectorAll("[data-scroll-carousel]").forEach((carousel) => {
        const section = carousel.closest("section");
        const arrows = section
            ? section.querySelectorAll(".catalog__arrow")
            : [];
        const prevBtn = arrows[0];
        const nextBtn = arrows[1];
        if (!prevBtn || !nextBtn) return;

        const step = () => {
            const card = carousel.querySelector(".card");
            if (!card) return 0;
            const gap = parseInt(getComputedStyle(carousel).columnGap, 10) || 24;
            return card.offsetWidth + gap;
        };

        const updateArrows = () => {
            prevBtn.disabled = carousel.scrollLeft <= 5;
            nextBtn.disabled =
                carousel.scrollLeft + carousel.clientWidth >=
                carousel.scrollWidth - 5;
        };

        prevBtn.addEventListener("click", () =>
            carousel.scrollBy({ left: -step(), behavior: "smooth" })
        );
        nextBtn.addEventListener("click", () =>
            carousel.scrollBy({ left: step(), behavior: "smooth" })
        );

        carousel.addEventListener("scroll", updateArrows, { passive: true });
        window.addEventListener("resize", updateArrows);
        updateArrows();
    });
});