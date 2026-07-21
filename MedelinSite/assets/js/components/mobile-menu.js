window.setupMobileMenu = function () {
    const toggle = document.querySelector('[data-mobile-menu-toggle]');
    const panel  = document.querySelector('[data-mobile-menu-panel]');
    if (!toggle || !panel) return;

    /* ── helpers ── */
    const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';

    const open = () => {
        toggle.setAttribute('aria-expanded', 'true');
        panel.classList.add('mobile-menu__panel--open');
        document.body.classList.add('body--scroll-locked');
        // Make sure toggle stays on top of the overlay
        toggle.style.zIndex = '9100';
    };

    const close = () => {
        toggle.setAttribute('aria-expanded', 'false');
        panel.classList.remove('mobile-menu__panel--open');
        document.body.classList.remove('body--scroll-locked');
        toggle.style.zIndex = '';
    };

    /* ── Toggle on burger click ── */
    toggle.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        isOpen() ? close() : open();
    });

    /* ── Close on nav-link click ── */
    panel.addEventListener('click', (e) => {
        const link = e.target && e.target.closest ? e.target.closest('a') : null;
        if (link) close();
    });

    /* ── Close on Escape ── */
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isOpen()) close();
    });

    /* ── Close on backdrop click (outside inner content) ── */
    panel.addEventListener('click', (e) => {
        if (e.target === panel) close();
    });

    /* ── Auto-close on viewport resize to desktop ── */
    window.addEventListener('resize', () => {
        if (window.innerWidth > 992 && isOpen()) close();
    });
};
