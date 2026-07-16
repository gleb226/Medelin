let currentFilterType = 'all'; // all, premium, specialty
let currentFilterRoast = 'all'; // all, espresso, filter
let allCoffeeData = [];
let lastScrollPosition = 0;

async function fetchCoffee() {
    const root = document.getElementById('coffee-root');
    if (!root) return;

    root.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Завантаження кави...</div>';

    try {
        const data = await window.loadMedelinData('coffee', (fresh) => {
            if (Array.isArray(fresh)) {
                allCoffeeData = fresh;
                renderCoffeeData(fresh);
                checkUrlForBean();
            }
        });
        if (data && Array.isArray(data)) {
            allCoffeeData = data;
            renderCoffeeData(data);
            checkUrlForBean();
        } else {
            console.error('fetchCoffee: Data is not an array or null', data);
            root.innerHTML = `<div class="error-msg">Помилка формату даних. <br><button type="button" data-action="reload-page" class="btn btn--sm btn--mt-md">Оновити</button></div>`;
        }
    } catch (err) {
        console.error('fetchCoffee critical error:', err);
        window.reportClientError('fetchCoffee critical error', err.stack || err.message);
        root.innerHTML = '<div class="error-msg">Критична помилка завантаження даних.</div>';
    }
}

function renderCoffeeData(coffeeData) {
    const commercialRoot = document.getElementById('commercial-root');
    const specialtyEspressoRoot = document.getElementById('specialty-espresso-root');
    const specialtyFilterRoot = document.getElementById('specialty-filter-root');
    const coffeeRoot = document.getElementById('coffee-root');

    if (!commercialRoot || !specialtyEspressoRoot || !specialtyFilterRoot) return;

    commercialRoot.innerHTML = '';
    specialtyEspressoRoot.innerHTML = '';
    specialtyFilterRoot.innerHTML = '';
    if (coffeeRoot) coffeeRoot.innerHTML = '';

    if (!coffeeData || !coffeeData.length) {
        if (coffeeRoot) coffeeRoot.innerHTML = '<div class="no-data">Наразі кава в зернах відсутня в базі</div>';
        return;
    }

    // Apply background colors to sections - using EXACT hex colors provided, NO transparency
    const commercialSection = document.getElementById('commercial-section');
    const specialtyEspressoSection = document.getElementById('specialty-espresso-section');
    const specialtyFilterSection = document.getElementById('specialty-filter-section');

    const colorCommercial = '#D5DEDA';
    const colorSpecialtyEspresso = '#FFF4D1';
    const colorSpecialtyFilter = '#FFEFE0';
    const colorWhite = '#ffffff';

    // Sharper, more elegant gradients (only 80px transition)
    if (commercialSection) {
        commercialSection.style.backgroundColor = colorCommercial;
        commercialSection.style.backgroundImage = `linear-gradient(to bottom, ${colorWhite} 0%, ${colorCommercial} 80px)`;
    }
    if (specialtyEspressoSection) {
        specialtyEspressoSection.style.backgroundColor = colorSpecialtyEspresso;
        specialtyEspressoSection.style.backgroundImage = `linear-gradient(to bottom, ${colorCommercial} 0%, ${colorSpecialtyEspresso} 80px)`;
    }
    if (specialtyFilterSection) {
        specialtyFilterSection.style.backgroundColor = colorSpecialtyFilter;
        specialtyFilterSection.style.backgroundImage = `linear-gradient(to bottom, ${colorSpecialtyEspresso} 0%, ${colorSpecialtyFilter} 80px)`;
    }

    const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';

    coffeeData.forEach((item) => {
        const art = document.createElement('article');
        art.className = 'product-card';
        let displayName = item.name.replace(/Blend Mixed/gi, '').trim();
        // Remove ANY emojis from name
        displayName = displayName.replace(/[\u{1F300}-\u{1F9FF}]/gu, '').trim();

        // Stock logic for specialty
        const qScore = (item.quality_score || '').trim();
        const isCommercial = !qScore || qScore === '—' || qScore === '-' || qScore === '0';
        const packs = (item.stock_packs !== undefined && item.stock_packs !== null) ? parseInt(item.stock_packs) : 999;
        
        if (!isCommercial && (packs <= 0 || isNaN(packs))) {
            return; // Hide out-of-stock specialty
        }

        let stockLabel = '';
        if (!isCommercial && packs <= 5) {
            stockLabel = `<div class="stock-badge"><i class="fas fa-hourglass-half"></i> Лишилося: ${packs}</div>`;
        }

        art.innerHTML = `
            <div class="product-card__image product-card__image--bean" style="background-image: url('${window.fixImageUrl(item.image_url) || defImg}');">
                ${stockLabel}
            </div>
            <div class="product-card__content">
                <h3 class="product-card__title">${displayName}</h3>
                
                <div class="product-card__info-brief" style="margin-bottom: 1.5rem; font-size: 0.9rem; color: #6b4f3a;">
                    ${item.processing ? `<div style="margin-bottom: 4px;"><strong>Обробка:</strong> ${item.processing}</div>` : ''}
                    ${item.descriptors || item.taste ? `<div style="margin-bottom: 4px;"><strong>Дескриптори:</strong> ${item.descriptors || item.taste}</div>` : ''}
                    ${item.roast ? `<div style="margin-bottom: 4px;"><strong>Обсмаження:</strong> ${item.roast}</div>` : ''}
                    ${!isCommercial && item.quality_score ? `<div><strong>Оцінка якості:</strong> ${item.quality_score}</div>` : ''}
                </div>

                <div class="product-card__price-row">
                    <span class="product-card__price">${item.price_250} ₴ / 250г</span>
                    <button class="btn-add-plus" type="button" onclick="event.stopPropagation(); if(typeof window.addBeanToCart === 'function') window.addBeanToCart('${item.id || item._id}', '${String(item.name || '').replace(/[\"']/g, '')}', 'bean_weight_hidden_${item.id || item._id}');">
                        <i class="fas fa-plus"></i>
                    </button>
                </div>
                <div style="display:none;">
                    <input type="radio" name="bean_weight_hidden_${item.id || item._id}" value="250" data-price="${item.price_250}" checked>
                </div>
            </div>`;
        art.onclick = () => openBeanDetail(item);

        // Categorization logic
        const roast = (item.roast || '').toLowerCase();

        if (isCommercial) {
            commercialRoot.appendChild(art);
        } else if (roast.includes('espresso')) {
            specialtyEspressoRoot.appendChild(art);
        } else if (roast.includes('filter')) {
            specialtyFilterRoot.appendChild(art);
        } else {
            specialtyEspressoRoot.appendChild(art); // Default specialty
        }
    });

    // Apply filters and hide empty sections
    applyCoffeeFilters();
}

function initCoffeeFilters() {
    const toggleBtn = document.getElementById('filter-toggle-btn');
    const panel = document.getElementById('coffee-filters-panel');
    const typeBtns = document.querySelectorAll('[data-filter-type]');
    const roastBtns = document.querySelectorAll('[data-filter-roast]');
    const roastGroup = document.getElementById('roast-filter-group');

    if (toggleBtn && panel) {
        toggleBtn.addEventListener('click', () => {
            panel.classList.toggle('active');
            toggleBtn.classList.toggle('active');
        });
    }

    typeBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            typeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilterType = btn.getAttribute('data-filter-type');
            
            if (currentFilterType === 'specialty') {
                if (roastGroup) roastGroup.style.display = 'flex';
            } else {
                if (roastGroup) roastGroup.style.display = 'none';
                // Reset roast filter when switching away from specialty
                currentFilterRoast = 'all';
                roastBtns.forEach(b => {
                    b.classList.remove('active');
                    if(b.getAttribute('data-filter-roast') === 'all') {
                        b.classList.add('active');
                    }
                });
            }
            
            applyCoffeeFilters();
        });
    });

    roastBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            roastBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilterRoast = btn.getAttribute('data-filter-roast');
            applyCoffeeFilters();
        });
    });
}

function applyCoffeeFilters() {
    const commercialSection = document.getElementById('commercial-section');
    const specialtyEspressoSection = document.getElementById('specialty-espresso-section');
    const specialtyFilterSection = document.getElementById('specialty-filter-section');

    const commercialRoot = document.getElementById('commercial-root');
    const specialtyEspressoRoot = document.getElementById('specialty-espresso-root');
    const specialtyFilterRoot = document.getElementById('specialty-filter-root');

    let showCommercial = false;
    let showSpecialtyEspresso = false;
    let showSpecialtyFilter = false;

    if (currentFilterType === 'all') {
        showCommercial = true;
        showSpecialtyEspresso = true;
        showSpecialtyFilter = true;
    } else if (currentFilterType === 'premium') {
        showCommercial = true;
    } else if (currentFilterType === 'specialty') {
        if (currentFilterRoast === 'all') {
            showSpecialtyEspresso = true;
            showSpecialtyFilter = true;
        } else if (currentFilterRoast === 'espresso') {
            showSpecialtyEspresso = true;
        } else if (currentFilterRoast === 'filter') {
            showSpecialtyFilter = true;
        }
    }

    if (commercialSection) commercialSection.style.display = (showCommercial && commercialRoot && commercialRoot.children.length > 0) ? '' : 'none';
    if (specialtyEspressoSection) specialtyEspressoSection.style.display = (showSpecialtyEspresso && specialtyEspressoRoot && specialtyEspressoRoot.children.length > 0) ? '' : 'none';
    if (specialtyFilterSection) specialtyFilterSection.style.display = (showSpecialtyFilter && specialtyFilterRoot && specialtyFilterRoot.children.length > 0) ? '' : 'none';
}

function checkUrlForBean() {
    const beanId = new URLSearchParams(window.location.search).get('id');
    if (beanId && allCoffeeData.length > 0) {
        const bean = allCoffeeData.find(b => b.id === beanId || b._id === beanId);
        if (bean) openBeanDetail(bean, false);
    }
}

function openBeanDetail(item, pushState = true) {
    const gridSection = document.getElementById('beans-grid-section');
    const detailSection = document.getElementById('bean-detail-section');
    const detailContent = document.getElementById('bean-detail-content');
    const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';

    if (!gridSection || !detailSection || !detailContent) return;

    // Save scroll position before switching views
    lastScrollPosition = window.scrollY;

    if (pushState) {
        const url = new URL(window.location);
        url.searchParams.set('id', item.id || item._id);
        window.history.pushState({}, '', url);
    }

    let displayName = item.name.replace(/Blend Mixed/gi, '').trim();
    const score = item.quality_score || item.cup_score;

    // Determine category color for detail background
    const qScore = (item.quality_score || '').trim();
    const roast = (item.roast || '').toLowerCase();
    const isCommercial = !qScore || qScore === '—' || qScore === '-' || qScore === '0';
    let detailBgColor = '#D5DEDA'; // Default commercial

    if (!isCommercial) {
        if (roast.includes('espresso')) detailBgColor = '#FFF4D1';
        else if (roast.includes('filter')) detailBgColor = '#FFEFE0';
        else detailBgColor = '#FFF4D1'; // Default specialty
    }
    
    // Set background color AND remove any gradient artifacts under header
    const mainElement = document.querySelector('main');
    if (mainElement) {
        mainElement.style.backgroundColor = detailBgColor;
    }
    document.body.style.backgroundColor = detailBgColor;
    detailSection.style.backgroundColor = detailBgColor;
    detailSection.style.backgroundImage = 'none';
    detailSection.style.marginTop = '0';
    detailSection.style.paddingTop = '0.5rem';

    detailContent.innerHTML = `
        <div class="bean-full-view">
            <div class="bean-full-view__container">
                <div class="bean-full-view__left-col">
                    <img src="${window.fixImageUrl(item.image_url) || defImg}" alt="${displayName}" class="bean-full-view__image">
                    
                    <div class="bean-full-view__price-card">
                        <div>
                            <span class="bean-full-view__price-label">Ціна</span>
                            <span class="bean-full-view__price-value">${item.price_250} ₴ / 250г</span>
                        </div>
                        <button class="btn btn--primary" type="button" 
                            data-action="add-bean-to-cart" 
                            data-bean-id="${item.id || item._id}" 
                            data-bean-name="${String(item.name || '').replace(/[\"']/g, '')}" 
                            data-weight-name="bean_weight_${item.id || item._id}">
                            <i class="fas fa-shopping-basket"></i> У кошик
                        </button>
                    </div>
                </div>

                <div class="bean-full-view__right-col">
                    <h1 class="bean-full-view__title">${displayName}</h1>
                    <p class="bean-full-view__description">${item.description || 'Преміальна свіжообсмажена кава Medelin, створена для справжніх поціновувачів.'}</p>
                    
                    <div class="bean-full-view__primary-stats">
                        ${item.roast ? `<div class="bean-full-view__stat-item"><label class="bean-full-view__stat-label">Обсмаження</label><p class="bean-full-view__stat-value">${item.roast}</p></div>` : ''}
                        ${!isCommercial && score ? `<div class="bean-full-view__stat-item"><label class="bean-full-view__stat-label">Оцінка якості</label><p class="bean-full-view__stat-value">${score}</p></div>` : ''}
                        ${item.harvest ? `<div class="bean-full-view__stat-item"><label class="bean-full-view__stat-label">Врожай</label><p class="bean-full-view__stat-value">${item.harvest}</p></div>` : ''}
                        ${item.processing ? `<div class="bean-full-view__stat-item"><label class="bean-full-view__stat-label">Метод обробки</label><p class="bean-full-view__stat-value">${item.processing}</p></div>` : ''}
                        
                        ${item.descriptors || item.taste ? `<div class="bean-full-view__stat-item bean-full-view__stat-item--span-2"><label class="bean-full-view__stat-label">Дескриптори</label><p class="bean-full-view__stat-value bean-full-view__stat-value--large">${item.descriptors || item.taste}</p></div>` : ''}
                        
                        ${item.variety ? `<div class="bean-full-view__stat-item"><label class="bean-full-view__stat-label">Різновид</label><p class="bean-full-view__stat-value">${item.variety}</p></div>` : ''}
                        ${item.altitude ? `<div class="bean-full-view__stat-item"><label class="bean-full-view__stat-label">Висота</label><p class="bean-full-view__stat-value">${item.altitude}</p></div>` : ''}
                    </div>

                    <div style="display:none;">
                        <input type="radio" name="bean_weight_${item.id || item._id}" value="250" data-price="${item.price_250}" checked>
                    </div>
                </div>
            </div>
        </div>
    `;

    // ── Inject mobile sticky add-to-cart bar ──
    const existingBar = document.getElementById('bean-sticky-bar');
    if (existingBar) existingBar.remove();

    const beanId   = item.id || item._id;
    const beanName = String(item.name || '').replace(/[\"']/g, '');
    const stickyBar = document.createElement('div');
    stickyBar.id = 'bean-sticky-bar';
    stickyBar.className = 'bean-detail-sticky-bar';
    stickyBar.innerHTML = `
        <div class="bean-detail-sticky-bar__price">
            <span class="bean-detail-sticky-bar__label">Ціна</span>
            <span class="bean-detail-sticky-bar__value">${item.price_250} ₴ <small style="font-size:0.65em;opacity:0.7;font-weight:600">/ 250г</small></span>
        </div>
        <button class="bean-detail-sticky-bar__btn" type="button"
            onclick="event.stopPropagation(); if(typeof window.addBeanToCart === 'function') window.addBeanToCart('${beanId}', '${beanName}', 'bean_weight_sticky_${beanId}');">
            <i class="fas fa-shopping-basket"></i>
            У кошик
        </button>
        <div style="display:none;">
            <input type="radio" name="bean_weight_sticky_${beanId}" value="250" data-price="${item.price_250}" checked>
        </div>
    `;
    document.body.appendChild(stickyBar);

    gridSection.style.display = 'none';
    detailSection.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'instant' });
}

window.closeBeanDetail = function() {
    const gridSection = document.getElementById('beans-grid-section');
    const detailSection = document.getElementById('bean-detail-section');
    const mainElement = document.querySelector('main');
    
    if (mainElement) mainElement.style.backgroundColor = '';
    document.body.style.backgroundColor = '';

    // Remove mobile sticky bar
    const stickyBar = document.getElementById('bean-sticky-bar');
    if (stickyBar) stickyBar.remove();
    
    if (!gridSection || !detailSection) return;

    const url = new URL(window.location);
    url.searchParams.delete('id');
    window.history.pushState({}, '', url);

    gridSection.style.display = 'block';
    detailSection.style.display = 'none';
    
    // Restore scroll position precisely
    window.scrollTo({ top: lastScrollPosition, behavior: 'instant' });
};

window.addEventListener('popstate', () => {
    const beanId = new URLSearchParams(window.location.search).get('id');
    if (beanId) {
        const bean = allCoffeeData.find(b => b.id === beanId || b._id === beanId);
        if (bean) openBeanDetail(bean, false);
    } else {
        window.closeBeanDetail();
    }
});

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        fetchCoffee();
        initCoffeeFilters();
    });
} else {
    fetchCoffee();
    initCoffeeFilters();
}
