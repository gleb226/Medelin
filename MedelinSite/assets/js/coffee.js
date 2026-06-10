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

        art.innerHTML = `
            <div class="product-card__image" style="background-image: url('${item.image_url || defImg}');"></div>
            <div class="product-card__content">
                <h3 class="product-card__title">${displayName}</h3>
                
                <div class="product-card__info-brief" style="margin-bottom: 1.5rem; font-size: 0.9rem; color: #6b4f3a;">
                    ${item.processing ? `<div style="margin-bottom: 4px;"><strong>Обробка:</strong> ${item.processing}</div>` : ''}
                    ${item.descriptors || item.taste ? `<div style="margin-bottom: 4px;"><strong>Дескриптори:</strong> ${item.descriptors || item.taste}</div>` : ''}
                    ${item.roast ? `<div style="margin-bottom: 4px;"><strong>Обсмаження:</strong> ${item.roast}</div>` : ''}
                    ${item.quality_score ? `<div><strong>Оцінка якості:</strong> ${item.quality_score}</div>` : ''}
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
        const score = parseFloat(item.quality_score);
        const roast = (item.roast || '').toLowerCase();

        if (!item.quality_score || score < 80) {
            commercialRoot.appendChild(art);
        } else if (roast === 'espresso') {
            specialtyEspressoRoot.appendChild(art);
        } else if (roast === 'filter') {
            specialtyFilterRoot.appendChild(art);
        } else {
            commercialRoot.appendChild(art); // Default to commercial
        }
    });

    // Hide sections if empty
    if (!commercialRoot.children.length && commercialSection) commercialSection.style.display = 'none';
    if (!specialtyEspressoRoot.children.length && specialtyEspressoSection) specialtyEspressoSection.style.display = 'none';
    if (!specialtyFilterRoot.children.length && specialtyFilterSection) specialtyFilterSection.style.display = 'none';
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
    const scoreVal = parseFloat(item.quality_score);
    const roast = (item.roast || '').toLowerCase();
    let detailBgColor = '#D5DEDA'; // Default commercial

    if (item.quality_score && scoreVal >= 80) {
        if (roast === 'espresso') detailBgColor = '#FFF4D1';
        else if (roast === 'filter') detailBgColor = '#FFEFE0';
    }
    
    // Set background color AND remove any gradient artifacts under header
    const mainElement = document.querySelector('main');
    if (mainElement) {
        mainElement.style.backgroundColor = detailBgColor;
    }
    detailSection.style.backgroundColor = detailBgColor;
    detailSection.style.backgroundImage = 'none';
    detailSection.style.marginTop = '0';
    detailSection.style.paddingTop = '3rem';

    detailContent.innerHTML = `
        <div class="bean-full-view">
            <div class="bean-full-view__container" style="display: grid; grid-template-columns: 1.1fr 1fr; gap: 4rem; align-items: stretch; margin-bottom: 3rem;">
                <div class="bean-full-view__left-col" style="display: flex; flex-direction: column;">
                    <img src="${item.image_url || defImg}" alt="${displayName}" style="width: 100%; height: 600px; border-radius: 32px; box-shadow: 0 25px 50px rgba(0,0,0,0.15); object-fit: cover; margin-bottom: 1.2rem;">
                    
                    <div style="background: var(--color-dark-brown); color: white; padding: 2.2rem; border-radius: 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 15px 35px rgba(0,0,0,0.2); margin-top: auto;">
                        <div>
                            <span style="display: block; font-size: 0.85rem; opacity: 0.8; margin-bottom: 0.2rem;">Ціна</span>
                            <span style="font-size: 2.5rem; font-weight: 800; font-family: var(--font-accent);">${item.price_250} ₴ / 250г</span>
                        </div>
                        <button class="btn btn--primary" style="background: white; color: var(--color-dark-brown); border: none; padding: 1.2rem 2.5rem; font-size: 1.1rem; border-radius: 16px; font-weight: 800; cursor: pointer; transition: all 0.2s;" type="button" data-action="add-bean-to-cart" data-bean-id="${item.id || item._id}" data-bean-name="${String(item.name || '').replace(/[\"']/g, '')}" data-weight-name="bean_weight_${item.id || item._id}" onclick="this.style.transform='scale(0.95)'; setTimeout(()=>this.style.transform='scale(1)', 100)">
                            <i class="fas fa-shopping-basket" style="margin-right: 12px;"></i> У кошик
                        </button>
                    </div>
                </div>

                <div class="bean-full-view__right-col" style="display: flex; flex-direction: column;">
                    <h1 style="font-family: var(--font-accent); font-size: 3.5rem; line-height: 1.1; margin-bottom: 1.5rem; color: var(--color-dark-brown);">${displayName}</h1>
                    <p style="font-size: 1.2rem; line-height: 1.6; color: #4a3728; margin-bottom: 2rem; font-weight: 400; opacity: 0.9;">${item.description || 'Преміальна свіжообсмажена кава Medelin, створена для справжніх поціновувачів.'}</p>
                    
                    <div class="bean-full-view__primary-stats" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; background: var(--color-coffee); padding: 2.5rem; border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.1); flex-grow: 1; align-content: start; color: #fff; box-shadow: var(--shadow-md);">
                        ${item.species ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Склад</label><p style="font-size: 1.1rem; font-weight: 700; color: #fff;">${item.species}</p></div>` : ''}
                        ${item.roast ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Обсмаження</label><p style="font-size: 1.1rem; font-weight: 700; color: #fff;">${item.roast}</p></div>` : ''}
                        ${score ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Оцінка якості</label><p style="font-size: 1.1rem; font-weight: 700; color: #fff;">${score}</p></div>` : ''}
                        ${item.harvest ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Врожай</label><p style="font-size: 1.1rem; font-weight: 700; color: #fff;">${item.harvest}</p></div>` : ''}
                        
                        ${item.descriptors || item.taste ? `<div style="grid-column: span 2; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 1.5rem;"><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Дескриптори</label><p style="font-size: 1.2rem; font-weight: 700; color: #fff;">${item.descriptors || item.taste}</p></div>` : ''}
                        
                        ${item.variety ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Різновид</label><p style="font-size: 1.1rem; font-weight: 700; color: #fff;">${item.variety}</p></div>` : ''}
                        ${item.altitude ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Висота</label><p style="font-size: 1.1rem; font-weight: 700; color: #fff;">${item.altitude}</p></div>` : ''}
                        ${item.processing ? `<div style="grid-column: span 2;"><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: rgba(255, 255, 255, 0.6); margin-bottom: 0.5rem;">Метод обробки</label><p style="font-size: 1.1rem; font-weight: 700; color: #fff;">${item.processing}</p></div>` : ''}
                    </div>

                    <div style="display:none;">
                        <input type="radio" name="bean_weight_${item.id || item._id}" value="250" data-price="${item.price_250}" checked>
                    </div>
                </div>
            </div>
        </div>
    `;


    gridSection.style.display = 'none';
    detailSection.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'instant' });
}

window.closeBeanDetail = function() {
    const gridSection = document.getElementById('beans-grid-section');
    const detailSection = document.getElementById('bean-detail-section');
    const mainElement = document.querySelector('main');
    
    if (mainElement) {
        mainElement.style.backgroundColor = '';
    }
    
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
    document.addEventListener('DOMContentLoaded', fetchCoffee);
} else {
    fetchCoffee();
}
