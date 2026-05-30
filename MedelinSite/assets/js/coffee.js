async function fetchCoffee() {
    const root = document.getElementById('coffee-root');
    if (!root) return;

    root.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Завантаження кави...</div>';

    const cached = typeof window.getCachedData === 'function' ? window.getCachedData('coffee') : null;
    if (cached) {
        renderCoffeeData(cached);
    }

    try {
        const data = await window.fetchMedelinData('coffee');
        if (data) {
            window.setCachedData('coffee', data);
            renderCoffeeData(data);
        } else if (!cached) {
            root.innerHTML = `<div class="error-msg">Помилка завантаження даних про каву. <br><button type="button" data-action="reload-page" class="btn btn--sm btn--mt-md">Оновити сторінку</button></div>`;
        }
    } catch (err) {
        console.error('fetchCoffee error:', err);
        if (!cached) root.innerHTML = '<div class="error-msg">Критична помилка завантаження.</div>';
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
                    <span class="product-card__price">${item.price_250} ₴</span>
                    <button class="btn-add-plus"><i class="fas fa-plus"></i></button>
                </div>
            </div>`;
        art.onclick = () => openCoffeePopup(item);
        grid.appendChild(art);
    });
    root.appendChild(grid);
}

function openCoffeePopup(item) {
    const popupBody = document.getElementById('popup-body');
    const popupImg = document.getElementById('popup-img');
    const popupTitle = document.getElementById('popup-title');
    const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';

    let displayName = item.name.replace(/Blend Mixed/gi, '').trim();
    if (popupImg) popupImg.src = item.image_url || defImg;
    if (popupTitle) popupTitle.textContent = displayName;

    const renderScale = (val, iconClass) => {
        let n = Math.min(Math.round(parseFloat(val || 0)), 5);
        if (n <= 0) return null;
        let html = '';
        for (let i = 0; i < 5; i++) {
            const opacity = i < n ? 1 : 0.2;
            html += `<i class="fas ${iconClass}" style="opacity: ${opacity}; margin-right: 2px; font-size: 0.8rem; color: var(--color-coffee);"></i>`;
        }
        return html;
    };

    const acidity = renderScale(item.acidity, 'fa-lemon');
    const bitterness = renderScale(item.bitterness, 'fa-mug-hot');
    const body = renderScale(item.body, 'fa-seedling');

    const price250 = item && item.price_250 != null ? item.price_250 : '';
    const price500 = item && item.price_500 != null ? item.price_500 : '';
    const price1000 = item && item.price_1000 != null ? item.price_1000 : '';

    let html = `
    <div class="popup__body-inner">
        <p class="popup__description">${item.description || 'Преміальна свіжообсмажена кава Medelin.'}</p>
        <div class="popup__info-list" style="display: grid; grid-template-columns: 1fr; gap: 12px; margin-bottom: 20px;">
            ${item.sort ? `<div class="popup__info-chip"><strong><i class="fas fa-layer-group"></i> Склад</strong><span>${item.sort}</span></div>` : ''}
            ${item.taste ? `<div class="popup__info-chip"><strong><i class="fas fa-utensils"></i> Смак</strong><span>${item.taste}</span></div>` : ''}
            ${item.roast ? `<div class="popup__info-chip"><strong><i class="fas fa-fire"></i> Обсмаження</strong><span>${item.roast}</span></div>` : ''}
        </div>
        <div class="scales-block">
            ${acidity ? `<div class="scale-row"><span>Кислинка</span> <span>${acidity}</span></div>` : ''}
            ${bitterness ? `<div class="scale-row"><span>Гірчинка</span> <span>${bitterness}</span></div>` : ''}
            ${body ? `<div class="scale-row"><span>Тіло (Насиченість)</span> <span>${body}</span></div>` : ''}
        </div>
        <div class="popup__weights-selection">
            <label class="weight-label weight-label--active" data-action="select-weight">
                <input type="radio" name="bean_weight_${item.id}" value="250" data-price="${item.price_250}" checked style="display:none;">
                <div class="weight-label__size">250г</div>
                <div class="weight-label__price">${price250}₴</div>
            </label>
            <label class="weight-label" data-action="select-weight">
                <input type="radio" name="bean_weight_${item.id}" value="500" data-price="${item.price_500}" style="display:none;">
                <div class="weight-label__size">500г</div>
                <div class="weight-label__price">${price500}₴</div>
            </label>
            <label class="weight-label" data-action="select-weight">
                <input type="radio" name="bean_weight_${item.id}" value="1000" data-price="${item.price_1000}" style="display:none;">
                <div class="weight-label__size">1кг</div>
                <div class="weight-label__price">${price1000}₴</div>
            </label>
        </div>
        <button class="btn btn--full-width" type="button" data-action="add-bean-to-cart" data-bean-id="${item.id}" data-bean-name="${String(item.name || '').replace(/[\"']/g, '')}" data-weight-name="bean_weight_${item.id}"><i class="fas fa-shopping-cart" style="margin-right:10px;"></i> Додати до кошика</button>
    </div>`;
    if (popupBody) popupBody.innerHTML = html;
    window.openPopup('item-popup');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fetchCoffee);
} else {
    fetchCoffee();
}
