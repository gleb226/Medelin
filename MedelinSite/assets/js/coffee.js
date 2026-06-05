let allCoffeeData = [];

async function fetchCoffee() {
    const root = document.getElementById('coffee-root');
    if (!root) return;

    root.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Завантаження кави...</div>';

    try {
        const data = await window.loadMedelinData('coffee', (fresh) => {
            allCoffeeData = fresh;
            renderCoffeeData(fresh);
            checkUrlForBean();
        });
        if (data) {
            allCoffeeData = data;
            renderCoffeeData(data);
            checkUrlForBean();
        } else {
            root.innerHTML = `<div class="error-msg">Помилка завантаження даних про каву. <br><button type="button" data-action="reload-page" class="btn btn--sm btn--mt-md">Оновити сторінку</button></div>`;
        }
    } catch (err) {
        console.error('fetchCoffee error:', err);
        root.innerHTML = '<div class="error-msg">Критична помилка завантаження.</div>';
    }
}

function renderCoffeeData(coffeeData) {
    const root = document.getElementById('coffee-root');
    if (!root) return;

    root.innerHTML = '';
    if (!coffeeData || !coffeeData.length) {
        root.innerHTML = '<div class="no-data">Наразі кава в зернах відсутня в базі</div>';
        return;
    }

    const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';
    const grid = document.createElement('div');
    grid.className = 'products-grid';

    coffeeData.forEach((item) => {
        const art = document.createElement('article');
        art.className = 'product-card';
        let displayName = item.name.replace(/Blend Mixed/gi, '').trim();

        // На картці має бути: Назва, Спосіб обробки, Дескриптори, Обсмаження, Оцінка якості
        art.innerHTML = `
            <div class="product-card__image" style="background-image: url('${item.image_url || defImg}');"></div>
            <div class="product-card__content">
                <h3 class="product-card__title">${displayName}</h3>
                
                <div class="product-card__info-brief" style="margin-bottom: 1.5rem; font-size: 0.9rem; color: #6b4f3a;">
                    ${item.processing ? `<div style="margin-bottom: 4px;"><strong>Обробка:</strong> ${item.processing}</div>` : ''}
                    ${item.descriptors || item.taste ? `<div style="margin-bottom: 4px;"><strong>Дескриптори:</strong> ${item.descriptors || item.taste}</div>` : ''}
                    ${item.roast ? `<div style="margin-bottom: 4px;"><strong>Обсмаження:</strong> ${item.roast}</div>` : ''}
                    ${item.quality_score || item.cup_score ? `<div><strong>Оцінка якості:</strong> ${item.quality_score || item.cup_score}</div>` : ''}
                </div>

                <div class="product-card__price-row">
                    <span class="product-card__price">${item.price_250} ₴ / 250г</span>
                    <button class="btn-add-plus"><i class="fas fa-plus"></i></button>
                </div>
            </div>`;
        art.onclick = () => openBeanDetail(item);
        grid.appendChild(art);
    });
    root.appendChild(grid);
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

    if (pushState) {
        const url = new URL(window.location);
        url.searchParams.set('id', item.id || item._id);
        window.history.pushState({}, '', url);
    }

    let displayName = item.name.replace(/Blend Mixed/gi, '').trim();

    detailContent.innerHTML = `
        <div class="bean-full-view">
            <div style="margin-bottom: 2rem;">
                <button class="btn btn--outline btn--sm" onclick="window.closeBeanDetail()">
                    <i class="fas fa-arrow-left" style="margin-right: 8px;"></i> Назад до списку
                </button>
            </div>
            <div class="bean-full-view__main" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 3rem; align-items: start; margin-bottom: 3rem;">
                <div class="bean-full-view__image-side">
                    <img src="${item.image_url || defImg}" alt="${displayName}" style="width: 100%; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.12); margin-bottom: 2rem;">
                </div>

                <div class="bean-full-view__info-side">
                    <h1 style="font-family: var(--font-accent); font-size: 3.5rem; line-height: 1.1; margin-bottom: 1rem; color: var(--color-dark-brown);">${displayName}</h1>
                    <div style="display: flex; gap: 1rem; margin-bottom: 2rem;">
                         ${item.quality_score || item.cup_score ? `<span class="tag" style="background: #ef4444; color: white; padding: 0.4rem 1rem; border-radius: 50px; font-weight: 700; font-size: 0.8rem;">Оцінка якості: ${item.quality_score || item.cup_score}</span>` : ''}
                    </div>

                    <p style="font-size: 1.25rem; line-height: 1.7; color: #4a3728; margin-bottom: 2.5rem; font-weight: 400;">${item.description || 'Преміальна свіжообсмажена кава Medelin, створена для справжніх поціновувачів.'}</p>
                    
                    <div class="bean-full-view__primary-stats" style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 3rem; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.04);">
                        ${item.species ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: var(--color-coffee); margin-bottom: 0.5rem; opacity: 0.7;">Склад</label><p style="font-size: 1.1rem; font-weight: 700;">${item.species}</p></div>` : ''}
                        ${item.roast ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: var(--color-coffee); margin-bottom: 0.5rem; opacity: 0.7;">Обсмаження</label><p style="font-size: 1.1rem; font-weight: 700;">${item.roast}</p></div>` : ''}
                        ${item.descriptors || item.taste ? `<div style="grid-column: span 2;"><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: var(--color-coffee); margin-bottom: 0.5rem; opacity: 0.7;">Дескриптори</label><p style="font-size: 1.2rem; font-weight: 700; color: var(--color-dark-brown);">${item.descriptors || item.taste}</p></div>` : ''}
                        
                        ${item.variety ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: var(--color-coffee); margin-bottom: 0.5rem; opacity: 0.7;">Різновид</label><p style="font-size: 1.1rem; font-weight: 700;">${item.variety}</p></div>` : ''}
                        ${item.altitude ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: var(--color-coffee); margin-bottom: 0.5rem; opacity: 0.7;">Висота зростання</label><p style="font-size: 1.1rem; font-weight: 700;">${item.altitude}</p></div>` : ''}
                        ${item.processing ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: var(--color-coffee); margin-bottom: 0.5rem; opacity: 0.7;">Метод обробки</label><p style="font-size: 1.1rem; font-weight: 700;">${item.processing}</p></div>` : ''}
                        ${item.harvest ? `<div><label style="display: block; font-weight: 800; font-size: 0.75rem; text-transform: uppercase; color: var(--color-coffee); margin-bottom: 0.5rem; opacity: 0.7;">Період врожаю</label><p style="font-size: 1.1rem; font-weight: 700;">${item.harvest}</p></div>` : ''}
                    </div>

                    <div style="background: var(--color-dark-brown); color: white; padding: 2.5rem; border-radius: 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 15px 35px rgba(0,0,0,0.2);">
                        <div>
                            <span style="display: block; font-size: 0.9rem; opacity: 0.8; margin-bottom: 0.2rem;">Ціна за 250г</span>
                            <span style="font-size: 2.5rem; font-weight: 800; font-family: var(--font-accent);">${item.price_250} ₴</span>
                        </div>
                        <button class="btn btn--primary" style="background: white; color: var(--color-dark-brown); border: none; padding: 1.2rem 2.5rem; font-size: 1.1rem; border-radius: 16px; font-weight: 800; cursor: pointer; transition: transform 0.2s;" type="button" data-action="add-bean-to-cart" data-bean-id="${item.id || item._id}" data-bean-name="${String(item.name || '').replace(/[\"']/g, '')}" data-weight-name="bean_weight_${item.id || item._id}" onclick="this.style.transform='scale(0.95)'; setTimeout(()=>this.style.transform='scale(1)', 100)">
                            <i class="fas fa-shopping-basket" style="margin-right: 12px;"></i> У кошик
                        </button>
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
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

window.closeBeanDetail = function() {
    const gridSection = document.getElementById('beans-grid-section');
    const detailSection = document.getElementById('bean-detail-section');
    if (!gridSection || !detailSection) return;

    const url = new URL(window.location);
    url.searchParams.delete('id');
    window.history.pushState({}, '', url);

    gridSection.style.display = 'block';
    detailSection.style.display = 'none';
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
