document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("navbarToggle");
    const nav = document.getElementById("navbarNav");
    const backToTop = document.getElementById("backToTop");

    if (toggle && nav) {
        toggle.addEventListener("click", () => {
            const isOpen = nav.classList.toggle("is-open");
            toggle.classList.toggle("is-open", isOpen);
            toggle.setAttribute("aria-expanded", String(isOpen));
        });

        nav.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                nav.classList.remove("is-open");
                toggle.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
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