const ICONS_MAP = {
    Кава: 'fa-mug-hot',
    Декаф: 'fa-leaf',
    Десерти: 'fa-cookie-bite',
    Напої: 'fa-glass-martini-alt',
    Масала: 'fa-pepper-hot',
    Фреш: 'fa-apple-alt',
    Чай: 'fa-leaf',
    Мілк: 'fa-blender',
    Какао: 'fa-mug-saucer',
};

const CAT_ORDER = ['Кава', 'Декаф', 'Десерти', 'Напої', 'Масала', 'Фреш', 'Чай', 'Мілк', 'Какао'];

function getCleanCatName(cat) {
    if (!cat) return '';
    return cat.replace(/[^\u0400-\u04FF\u0406\u0407\u0404\u0456\u0457\u0454\w\s]/g, '').replace(/\s+/g, ' ').trim();
}

function getCatIcon(cat) {
    const cleanCat = getCleanCatName(cat);
    return `<i class="fas ${ICONS_MAP[cleanCat] || 'fa-utensils'}"></i>`;
}

function getSiteBasePath() {
    const path = window.location.pathname || '/';
    const idx = path.indexOf('/pages/');
    if (idx !== -1) return path.slice(0, idx + 1);
    const lastSlash = path.lastIndexOf('/');
    if (lastSlash !== -1) return path.slice(0, lastSlash + 1);
    return '/';
}

function resolveAssetUrl(raw) {
    const value = raw != null ? String(raw).trim() : '';
    if (!value) return '';
    if (/^https?:\/\//i.test(value)) return value;
    if (value.startsWith('/uploads/')) return `${getSiteBasePath()}uploads/${value.slice('/uploads/'.length)}`;
    if (value.startsWith('/')) return `${getSiteBasePath()}${value.slice(1)}`;
    return value;
}

window.openItemPopup = function (item, category) {
    const popupImg = document.getElementById('popup-img');
    const popupTitle = document.getElementById('popup-title');
    const popupPrice = document.getElementById('popup-price');
    const popupBody = document.getElementById('popup-body');

    const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';

    const basePrice = Number((item && item.price) || 0);
    const safeBasePrice = Number.isFinite(basePrice) ? basePrice : 0;
    const safeCategory = category ? String(category) : '';
    const safeName = item && item.name ? String(item.name) : 'Item';

    const renderScale = (val, iconClass) => {
        const n = Math.min(Math.max(parseInt(val == null ? 0 : val, 10) || 0, 0), 5);
        if (n <= 0) return null;
        let html = '';
        for (let i = 0; i < 5; i++) {
            const opacity = i < n ? 1 : 0.2;
            html += `<i class="fas ${iconClass}" style="opacity:${opacity}; margin-right:2px; font-size:0.8rem; color:var(--color-coffee);"></i>`;
        }
        return html;
    };

    const formatMoney = (n) => `${Math.round(Number(n) || 0)} ₴`;

    try {
        const imgUrlSafe = resolveAssetUrl(item && item.image_url);

        if (popupImg) {
            popupImg.src = imgUrlSafe || defImg;
            popupImg.alt = safeName;
        }
        if (popupTitle) popupTitle.textContent = safeName;

        const strength = renderScale(item && item.strength, 'fa-fire');
        const sweetness = renderScale(item && item.sweetness, 'fa-cubes');

        const options = item && Array.isArray(item.options) ? item.options : [];
        const caffeineOpts = options.filter((o) => o && o.type === 'caffeine');
        const milkOpts = options.filter((o) => o && o.type === 'milk');
        const addonOpts = options.filter((o) => o && o.type === 'addon');

        const infoChips = [
            item && item.composition ? `<div class="popup__info-chip"><strong><i class="fas fa-layer-group"></i> Склад</strong><span>${item.composition}</span></div>` : '',
            item && item.volume ? `<div class="popup__info-chip"><strong><i class="fas fa-wine-glass"></i> Обʼєм</strong><span>${item.volume}</span></div>` : '',
            item && item.calories ? `<div class="popup__info-chip"><strong><i class="fas fa-bolt"></i> Калорійність</strong><span>${item.calories}</span></div>` : '',
        ]
            .filter(Boolean)
            .join('');

        const makeOptionChip = (o, type, active) => {
            const add = Number((o && o.add_price) || 0);
            const addText = add > 0 ? ` +${add}` : add < 0 ? ` ${add}` : '';
            const cls = active ? 'choice-chip is-active' : 'choice-chip';
            const name = (o && o.name) || '';
            return `<button type="button" class="${cls}" data-opt-type="${type}" data-add="${Number.isFinite(add) ? add : 0}" data-name="${String(name).replace(/\"/g, '&quot;')}">${name}${addText ? `<span style="margin-left:8px; opacity:.8;">${addText}₴</span>` : ''}</button>`;
        };

        const optionsHtml = (() => {
            if (!caffeineOpts.length && !milkOpts.length && !addonOpts.length) return '';
            const caffeineBlock = caffeineOpts.length
                ? `
                    <div class="popup__info-chip popup__info-chip--grid-1">
                        <strong><i class="fas fa-mug-hot"></i> Кофеїн</strong>
                        <div class="choice-grid" style="margin-top:10px;">
                            ${caffeineOpts.map((o, i) => makeOptionChip(o, 'caffeine', i === 0)).join('')}
                        </div>
                    </div>`
                : '';
            const milkBlock = milkOpts.length
                ? `
                    <div class="popup__info-chip popup__info-chip--grid-1">
                        <strong><i class="fas fa-filter"></i> Молоко</strong>
                        <div class="choice-grid" style="margin-top:10px;">
                            ${milkOpts.map((o, i) => makeOptionChip(o, 'milk', i === 0)).join('')}
                        </div>
                    </div>`
                : '';
            const addonsBlock = addonOpts.length
                ? `
                    <div class="popup__info-chip popup__info-chip--grid-1">
                        <strong><i class="fas fa-plus-circle"></i> Додатки</strong>
                        <div class="choice-grid" style="margin-top:10px;">
                            ${addonOpts.map((o) => makeOptionChip(o, 'addon', false)).join('')}
                        </div>
                    </div>`
                : '';
            return `<div class="popup__info-list" style="display:grid; grid-template-columns:1fr; gap:12px; margin-bottom:18px;">${caffeineBlock}${milkBlock}${addonsBlock}</div>`;
        })();

        const desc = item && item.description ? String(item.description) : '';

        if (popupBody) {
            popupBody.innerHTML = `
                <div class="popup__body-inner">
                    ${desc ? `<p class="popup__description">${desc}</p>` : ''}
                    ${infoChips ? `<div class="popup__info-list" style="display:grid; grid-template-columns:1fr; gap:12px; margin-bottom:18px;">${infoChips}</div>` : ''}
                    ${(strength || sweetness) ? `<div class="scales-block">
                        ${strength ? `<div class="scale-row"><span>Міцність</span><span>${strength}</span></div>` : ''}
                        ${sweetness ? `<div class="scale-row"><span>Солодкість</span><span>${sweetness}</span></div>` : ''}
                    </div>` : ''}
                    ${optionsHtml}
                    <button class="btn btn--full-width" type="button" id="popup-add-btn">
                        <i class="fas fa-shopping-cart" style="margin-right:10px;"></i> Додати до кошика
                    </button>
                </div>
            `;
        }

        const computeTotal = () => {
            if (!popupBody) return safeBasePrice;
            let total = safeBasePrice;
            const active = popupBody.querySelectorAll('.choice-chip.is-active');
            active.forEach((el) => {
                const add = Number(el.getAttribute('data-add') || 0);
                if (Number.isFinite(add)) total += add;
            });
            return total;
        };

        const updatePrice = () => {
            const total = computeTotal();
            if (popupPrice) popupPrice.textContent = formatMoney(total);
        };

        if (popupBody) {
            const optionButtons = popupBody.querySelectorAll('.choice-chip');
            optionButtons.forEach((btn) => {
                btn.addEventListener('click', () => {
                    const t = btn.getAttribute('data-opt-type');
                    if (t === 'caffeine' || t === 'milk') {
                        popupBody.querySelectorAll(`.choice-chip[data-opt-type="${t}"]`).forEach((x) => x.classList.remove('is-active'));
                        btn.classList.add('is-active');
                    } else {
                        btn.classList.toggle('is-active');
                    }
                    updatePrice();
                });
            });
        }

        updatePrice();

        const addBtn = document.getElementById('popup-add-btn');
        if (addBtn) {
            addBtn.onclick = () => {
                const total = computeTotal();
                if (typeof window.addMenuToCart !== 'function') return;

                let selected = [];
                if (popupBody) {
                    popupBody.querySelectorAll('.choice-chip.is-active').forEach((el) => {
                        const name = el.getAttribute('data-name');
                        if (name) selected.push(name);
                    });
                }
                const suffix = selected.length ? ` (${selected.join(', ')})` : '';
                const idBase = item && item.id != null && String(item.id).trim() ? String(item.id) : `${safeCategory || 'menu'}:${safeName}`;
                const id = selected.length ? `${idBase}|${selected.join('|')}` : idBase;
                window.addMenuToCart(id, `${safeName}${suffix}`, Math.round(total));
            };
        }

        if (typeof window.openPopup === 'function') window.openPopup('item-popup');
    } catch (e) {
        console.error('[Medelin Error] openItemPopup failed:', e);
        if (typeof window.showToast === 'function') window.showToast('Something went wrong. Check console (F12).', 'error');
    }
};

async function fetchMenu() {
    const root = document.getElementById('menu-root');
    const subnav = document.getElementById('subnav-list');
    if (!root) return;

    console.log('[Medelin] Запуск fetchMenu...');
    root.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Завантаження меню...</div>';

    const cached = typeof window.getCachedData === 'function' ? window.getCachedData('menu') : null;
    if (cached && Array.isArray(cached) && cached.length > 0) {
        console.log('[Medelin] Використовуємо кеш браузера (localStorage)');
        renderMenuData(cached);
    }

    try {
        const data = await window.fetchMedelinData('menu');
        if (data && Array.isArray(data) && data.length > 0) {
            data.sort((a, b) => {
                let idxA = CAT_ORDER.indexOf(getCleanCatName(a.category));
                let idxB = CAT_ORDER.indexOf(getCleanCatName(b.category));
                if (idxA === -1) idxA = 99;
                if (idxB === -1) idxB = 99;
                return idxA - idxB;
            });
            window.setCachedData('menu', data);
            renderMenuData(data);
            console.log('[Medelin] Меню оновлено з сервера/файлу');
        } else if (!cached) {
            root.innerHTML = `<div class="error-msg">Не вдалося знайти файл з меню. Перевірте папку MedelinSite/cache/</div>`;
        }
    } catch (err) {
        console.error('[Medelin] Помилка у fetchMenu:', err);
        if (!cached) root.innerHTML = '<div class="error-msg">Критична помилка завантаження. Дивіться консоль.</div>';
    }
}

function renderMenuData(menuData) {
    const root = document.getElementById('menu-root');
    const subnav = document.getElementById('subnav-list');
    if (!root) return;

    console.log('[Medelin] Рендеринг меню, кількість категорій:', menuData.length);
    root.innerHTML = '';
    if (subnav) subnav.innerHTML = '';
    
    const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';

    menuData.forEach((section, idx) => {
        try {
            const cleanName = getCleanCatName(section.category);
            
            if (subnav) {
                const li = document.createElement('li');
                li.innerHTML = `<a href="#cat-${idx}" class="menu-subnav__link">${getCatIcon(section.category)} <span>${cleanName}</span></a>`;
                li.querySelector('a').onclick = (e) => {
                    e.preventDefault();
                    const t = document.getElementById('cat-' + idx);
                    if (t) window.scrollTo({ top: t.offsetTop - 120, behavior: 'smooth' });
                };
                subnav.appendChild(li);
            }

            const art = document.createElement('article');
            art.className = 'category';
            art.id = 'cat-' + idx;
            art.innerHTML = `<h3 class="category__title">${getCatIcon(section.category)} ${cleanName}</h3>`;

            if (section.simple) {
                const list = document.createElement('ul');
                list.className = 'menu-list';
                section.items.forEach((item) => {
                    const li = document.createElement('li');
                    li.className = 'menu-list__item';
                    li.innerHTML = `<span class="menu-list__name">${item.name}</span><span class="menu-list__price">${item.price} ₴</span>`;
                    list.appendChild(li);
                });
                art.appendChild(list);
            } else {
                const grid = document.createElement('div');
                grid.className = 'products-grid';
                section.items.forEach((item) => {
                    const div = document.createElement('div');
                    div.className = 'menu-item';
                    const imgUrlSafe = resolveAssetUrl(item && item.image_url);
                    div.innerHTML = `
                        <div class="menu-item__image" style="background-image:url('${imgUrlSafe || defImg}')"></div>
                        <div class="menu-item__info">
                            <h4 class="menu-item__title">${item.name}</h4>
                            <div class="menu-item__price-group">
                                <span class="menu-item__price">${item.price} ₴</span>
                                <button class="btn-add-plus"><i class="fas fa-plus"></i></button>
                            </div>
                        </div>`;
                    const plusBtn = div.querySelector('.btn-add-plus');
                    if (plusBtn) {
                        plusBtn.addEventListener('click', (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            const id =
                                item && item.id != null && String(item.id).trim()
                                    ? String(item.id)
                                    : `${getCleanCatName(section.category) || 'menu'}:${(item && item.name) || 'item'}`;
                            const priceNum = Number((item && item.price) || 0);
                            if (typeof window.addMenuToCart === 'function') {
                                window.addMenuToCart(id, (item && item.name) || 'Item', Number.isFinite(priceNum) ? priceNum : 0);
                            }
                        });
                    }

                    div.addEventListener('click', () => window.openItemPopup(item, section.category));
                    grid.appendChild(div);
                });
                art.appendChild(grid);
            }
            root.appendChild(art);
        } catch (e) {
            console.error('[Medelin] Помилка рендерингу секції:', e);
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fetchMenu);
} else {
    fetchMenu();
}
