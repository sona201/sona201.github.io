// Keep article anchors visible beneath the site's sticky navigation.
function setupSmoothAnchors(): void {
    document.querySelectorAll<HTMLAnchorElement>("a[href]").forEach(link => {
        const href = link.getAttribute("href");
        if (!href || !href.startsWith("#")) return;

        link.addEventListener("click", event => {
            const target = document.getElementById(decodeURI(href.substring(1)));
            if (!target) return;

            event.preventDefault();
            const navigation = document.querySelector<HTMLElement>(".top-navigation");
            const navigationOffset = navigation ? navigation.getBoundingClientRect().height + 16 : 0;
            const targetTop = target.getBoundingClientRect().top + window.scrollY;

            window.history.pushState({}, "", href);
            window.scrollTo({
                top: Math.max(0, targetTop - navigationOffset),
                behavior: "smooth"
            });
        });
    });
}

export { setupSmoothAnchors };
