window.setupMobileMenu = function () {
    const toggle = document.querySelector('[data-mobile-menu-toggle]');
    const panel = document.querySelector('[data-mobile-menu-panel]');
    const closeBtn = document.querySelector('[data-mobile-menu-close]');
    if (!toggle || !panel) return;

    const close = () => {
        toggle.setAttribute('aria-expanded', 'false');
        panel.classList.remove('is-open');
        document.body.classList.remove('is-scroll-locked');
    };

    const open = () => {
        toggle.setAttribute('aria-expanded', 'true');
        panel.classList.add('is-open');
        document.body.classList.add('is-scroll-locked');
    };

    const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';

    toggle.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (isOpen()) close();
        else open();
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', (event) => {
            event.preventDefault();
            close();
        });
    }

    panel.addEventListener('click', (event) => {
        if (event.target === panel) {
            close();
            return;
        }

        const target = event.target;
        const link = target && target.closest ? target.closest('a') : null;
        if (link) close();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') close();
    });

    document.addEventListener('pointerdown', (event) => {
        if (!isOpen()) return;
        if (panel.contains(event.target) || toggle.contains(event.target)) return;
        close();
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 992) close();
    });
};
