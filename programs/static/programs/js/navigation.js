/* Progressive enhancement: navigation stays available if JavaScript is off. */
(() => {
    "use strict";
    const sidebar = document.getElementById("app-sidebar");
    const toggle = document.getElementById("navigation-toggle");
    const close = document.getElementById("navigation-close");
    const backdrop = document.getElementById("navigation-backdrop");
    const shell = document.querySelector(".app-shell");
    if (!sidebar || !toggle || !close || !backdrop || !shell) return;

    const mobile = window.matchMedia("(max-width: 960px)");
    let open = false;

    function render() {
        const expanded = mobile.matches && open;
        toggle.hidden = !mobile.matches;
        close.hidden = !mobile.matches;
        toggle.setAttribute("aria-expanded", String(expanded));
        toggle.setAttribute("aria-label", expanded ? "Close navigation" : "Open navigation");
        sidebar.inert = mobile.matches && !open;
        if (mobile.matches) sidebar.setAttribute("aria-hidden", String(!open));
        else sidebar.removeAttribute("aria-hidden");
        shell.inert = expanded;
        backdrop.hidden = !expanded;
        document.body.classList.toggle("navigation-open", expanded);
    }

    function dismiss() {
        open = false;
        render();
        toggle.focus();
    }

    toggle.addEventListener("click", () => {
        open = !open;
        render();
        if (open) close.focus();
    });
    close.addEventListener("click", dismiss);
    backdrop.addEventListener("click", dismiss);
    sidebar.addEventListener("click", (event) => {
        if (mobile.matches && open && event.target.closest("a")) dismiss();
    });
    document.addEventListener("keydown", (event) => {
        if (!mobile.matches || !open) return;
        if (event.key === "Escape") {
            event.preventDefault();
            dismiss();
        } else if (event.key === "Tab") {
            const controls = [...sidebar.querySelectorAll("a[href], button:not([hidden])")];
            const first = controls[0];
            const last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });
    mobile.addEventListener("change", () => {
        const focusWasInSidebar = sidebar.contains(document.activeElement);
        const focusWasOnHiddenControl = document.activeElement === toggle || document.activeElement === close;
        open = false;
        render();
        if (mobile.matches && focusWasInSidebar) toggle.focus();
        else if (!mobile.matches && focusWasOnHiddenControl) sidebar.querySelector("a").focus();
    });
    document.body.classList.add("navigation-ready");
    render();
})();
