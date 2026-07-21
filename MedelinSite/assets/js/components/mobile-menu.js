window.setupMobileMenu = function () {
    const toggle = document.querySelector('[data-mobile-menu-toggle]');
    const panel  = document.querySelector('[data-mobile-menu-panel]');
    if (!toggle || !panel) return;

    const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';

    const open = () => {
        toggle.setAttribute('aria-expanded', 'true');
        panel.classList.add('mobile-menu__panel--open');
        document.body.classList.add('body--scroll-locked');

        toggle.style.zIndex = '9100';
    };

    const close = () => {
        toggle.setAttribute('aria-expanded', 'false');
        panel.classList.remove('mobile-menu__panel--open');
        document.body.classList.remove('body--scroll-locked');
        toggle.style.zIndex = '';
    };

    toggle.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        isOpen() ? close() : open();
    });

    panel.addEventListener('click', (e) => {
        const link = e.target && e.target.closest ? e.target.closest('a') : null;
        if (link) close();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isOpen()) close();
    });

    panel.addEventListener('click', (e) => {
        if (e.target === panel) close();
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 992 && isOpen()) close();
    });
};
