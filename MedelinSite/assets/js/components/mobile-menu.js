window.setupMobileMenu = function () {
    const toggle = document.querySelector('[data-mobile-menu-toggle]');
    const panel = document.querySelector('[data-mobile-menu-panel]');
    if (!toggle || !panel) return;

    const close = () => {
        toggle.setAttribute('aria-expanded', 'false');
        panel.classList.remove('mobile-menu__panel--open');
        document.body.classList.remove('body--scroll-locked');
    };

    const open = () => {
        toggle.setAttribute('aria-expanded', 'true');
        panel.classList.add('mobile-menu__panel--open');
        document.body.classList.add('body--scroll-locked');
    };

    const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';

    toggle.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (isOpen()) close();
        else open();
    });

    panel.addEventListener('click', (event) => {
        const target = event.target;
        const link = target && target.closest ? target.closest('a') : null;
        if (link) {
            close();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && isOpen()) close();
    });

    // Close when clicking outside panel
    document.addEventListener('click', (event) => {
        if (isOpen() && !panel.contains(event.target) && !toggle.contains(event.target)) {
            close();
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 992 && isOpen()) close();
    });
};
