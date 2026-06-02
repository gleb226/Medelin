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

        art.innerHTML = `
            <div class="product-card__image" style="background-image: url('${item.image_url || defImg}');"></div>
            <div class="product-card__content">
                <h3 class="product-card__title">${displayName}</h3>
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

    const renderScale = (val, iconClass) => {
        let n = Math.min(Math.round(parseFloat(val || 0)), 5);
        if (n <= 0) return null;
        let html = '';
        for (let i = 0; i < 5; i++) {
            const opacity = i < n ? 1 : 0.2;
            html += `<i class="fas ${iconClass}" style="opacity: ${opacity}; margin-right: 4px; font-size: 1.1rem; color: var(--color-coffee);"></i>`;
        }
        return html;
    };

    const acidity = renderScale(item.acidity, 'fa-lemon');
    const bitterness = renderScale(item.bitterness, 'fa-mug-hot');
    const body = renderScale(item.body, 'fa-seedling');

    detailContent.innerHTML = `
        <div class="bean-full-view">
            <div class="bean-full-view__grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 3rem; align-items: start;">
                <div class="bean-full-view__image-wrap">
                    <img src="${item.image_url || defImg}" alt="${displayName}" style="width: 100%; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1);">
                </div>
                <div class="bean-full-view__info">
                    <h1 style="font-family: var(--font-accent); font-size: 3rem; margin-bottom: 1rem; color: var(--color-dark-brown);">${displayName}</h1>
                    <p style="font-size: 1.2rem; line-height: 1.6; color: var(--color-text-muted); margin-bottom: 2rem;">${item.description || 'Преміальна свіжообсмажена кава Medelin, створена для справжніх поціновувачів.'}</p>
                    
                    <div class="bean-full-view__stats" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2.5rem;">
                        ${item.sort ? `<div><p style="font-weight: 800; font-size: 0.85rem; text-transform: uppercase; color: var(--color-coffee); letter-spacing: 1px; margin-bottom: 0.4rem;">Склад</p><p style="font-size: 1.1rem; font-weight: 600;">${item.sort}</p></div>` : ''}
                        ${item.taste ? `<div><p style="font-weight: 800; font-size: 0.85rem; text-transform: uppercase; color: var(--color-coffee); letter-spacing: 1px; margin-bottom: 0.4rem;">Смак</p><p style="font-size: 1.1rem; font-weight: 600;">${item.taste}</p></div>` : ''}
                        ${item.roast ? `<div><p style="font-weight: 800; font-size: 0.85rem; text-transform: uppercase; color: var(--color-coffee); letter-spacing: 1px; margin-bottom: 0.4rem;">Обсмаження</p><p style="font-size: 1.1rem; font-weight: 600;">${item.roast}</p></div>` : ''}
                        <div><p style="font-weight: 800; font-size: 0.85rem; text-transform: uppercase; color: var(--color-coffee); letter-spacing: 1px; margin-bottom: 0.4rem;">Ціна</p><p style="font-size: 1.5rem; font-weight: 800;">${item.price_250} ₴ / 250г</p></div>
                    </div>

                    <div class="bean-full-view__scales" style="background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 3rem;">
                        ${acidity ? `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;"><span>Кислинка</span> <div>${acidity}</div></div>` : ''}
                        ${bitterness ? `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;"><span>Гірчинка</span> <div>${bitterness}</div></div>` : ''}
                        ${body ? `<div style="display: flex; justify-content: space-between; align-items: center;"><span>Насиченість</span> <div>${body}</div></div>` : ''}
                    </div>

                    <div style="display:none;">
                        <input type="radio" name="bean_weight_${item.id || item._id}" value="250" data-price="${item.price_250}" checked>
                    </div>

                    <button class="btn btn--primary btn--lg" style="width: 100%; padding: 1.2rem; font-size: 1.1rem; border-radius: 15px;" type="button" data-action="add-bean-to-cart" data-bean-id="${item.id || item._id}" data-bean-name="${String(item.name || '').replace(/[\"']/g, '')}" data-weight-name="bean_weight_${item.id || item._id}">
                        <i class="fas fa-shopping-cart" style="margin-right: 12px;"></i> Додати до кошика
                    </button>
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
