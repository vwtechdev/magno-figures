document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("navbarToggle");
    const nav = document.getElementById("navbarNav");
    const backToTop = document.getElementById("backToTop");

    if (toggle && nav) {
        const backdrop = document.createElement("div");
        backdrop.className = "navbar__backdrop";
        backdrop.setAttribute("aria-hidden", "true");
        document.body.appendChild(backdrop);

        const setOpen = (isOpen) => {
            nav.classList.toggle("is-open", isOpen);
            toggle.classList.toggle("is-open", isOpen);
            toggle.setAttribute("aria-expanded", String(isOpen));
            toggle.setAttribute(
                "aria-label",
                isOpen ? "Fechar menu" : "Abrir menu"
            );
            backdrop.classList.toggle("is-visible", isOpen);
            document.body.classList.toggle("nav-open", isOpen);
        };

        toggle.addEventListener("click", () => {
            setOpen(!nav.classList.contains("is-open"));
        });

        backdrop.addEventListener("click", () => setOpen(false));

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") setOpen(false);
        });

        nav.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                setOpen(false);
                nav.querySelectorAll(".navbar__item--dropdown.is-open").forEach((item) => {
                    item.classList.remove("is-open");
                });
            });
        });

        nav.querySelectorAll(".navbar__sub-toggle").forEach((btn) => {
            btn.addEventListener("click", (event) => {
                event.stopPropagation();
                const item = btn.closest(".navbar__item--dropdown");
                const isOpen = item.classList.toggle("is-open");
                btn.setAttribute("aria-expanded", String(isOpen));
            });
        });
    }

    const userDropdown = document.getElementById("userDropdown");
    const userToggle = document.getElementById("userDropdownToggle");
    if (userDropdown && userToggle) {
        const openDropdown = (isOpen) => {
            userDropdown.classList.toggle("is-open", isOpen);
            userToggle.setAttribute("aria-expanded", String(isOpen));
        };
        userToggle.addEventListener("click", (event) => {
            event.stopPropagation();
            openDropdown(!userDropdown.classList.contains("is-open"));
        });
        document.addEventListener("click", () => openDropdown(false));
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") openDropdown(false);
        });
    }

    if (backToTop) {
        const onScroll = () => {
            if (window.scrollY > 400) {
                backToTop.classList.add("is-visible");
            } else {
                backToTop.classList.remove("is-visible");
            }
        };

        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
        backToTop.addEventListener("click", () => {
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }
});