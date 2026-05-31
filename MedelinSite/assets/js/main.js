const _host = window.location.hostname;
const _port = window.location.port;
const _proto = window.location.protocol;
const isFileProto = _proto === 'file:';
const isLocal = _host === 'localhost' || _host === '127.0.0.1' || _host === '';

window.API_BASE_URL = '';

if (isLocal && _port === '8000') {
    window.API_BASE_URL = 'http://localhost:8000';
}

window.fetchMedelinData = async function (key) {
    const fileName = `${key}.json`;
    const endpoints = [
        `${window.API_BASE_URL}/api/${key}`,
        `${window.API_BASE_URL}/assets/data/${fileName}`
    ];
    
    const isRoot = !window.location.pathname.includes('/pages/');
    if (isRoot) {
        endpoints.push(`./assets/data/${fileName}`);
    } else {
        endpoints.push(`../assets/data/${fileName}`);
    }
    
    endpoints.push(`/assets/data/${fileName}`);

    for (const url of endpoints) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            
            const finalUrl = url.includes('?') ? `${url}&t=${Date.now()}` : `${url}?t=${Date.now()}`;
            const response = await fetch(finalUrl, { signal: controller.signal });
            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                if (Array.isArray(data) && data.length > 0) {
                    return data;
                }
            }
        } catch (e) {
        }
    }
    
    return null;
};

window.onerror = function(msg, url, lineNo, columnNo, error) {
    if (window.showToast) {
        window.showToast('Сталася помилка в роботі сайту.', 'error');
    }
    return false;
};

window.showToast = function (message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    const icon = type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';
    toast.innerHTML = `
        <i class="fas ${icon} toast__icon"></i>
        <span class="toast__message">${message}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('toast--closing');
        setTimeout(() => toast.remove(), 400);
    }, 4000);
};

window.getUserData = function () {
    return JSON.parse(localStorage.getItem('medelin_user_data') || '{}');
};

window.setUserData = function (data) {
    const existing = window.getUserData();
    localStorage.setItem('medelin_user_data', JSON.stringify({ ...existing, ...data }));
};

window.getPastOrders = function () {
    return JSON.parse(localStorage.getItem('medelin_past_orders') || '[]');
};

window.syncPastOrders = async function(force = false) {
    const userData = window.getUserData();
    if (!userData || !userData.phone) return;
    
    // Якщо вже синхронізували нещодавно і не force, пропускаємо
    const lastSync = localStorage.getItem('last_sync_time');
    if (!force && lastSync && (Date.now() - parseInt(lastSync) < 300000)) { // 5 хв
        return window.getPastOrders();
    }
    
    try {
        const resp = await fetch(`${window.API_BASE_URL}/api/past-orders?phone=${encodeURIComponent(userData.phone)}`);
        if (resp.ok) {
            const serverOrders = await resp.json();
            if (Array.isArray(serverOrders)) {
                // Мапимо серверний формат на локальний
                const localOrders = serverOrders.map(o => ({
                    items: [], 
                    items_text: o.items_text,
                    total: o.total,
                    timestamp: new Date(o.timestamp).getTime(),
                    type: o.type,
                    id: o.order_id
                }));
                localStorage.setItem('medelin_past_orders', JSON.stringify(localOrders.slice(0, 10)));
                localStorage.setItem('last_sync_time', Date.now().toString());
                
                // Якщо кошик відкритий — оновлюємо його
                const modal = document.getElementById('cart-modal-container');
                if (modal && modal.classList.contains('cart-modal--active')) {
                    window.openCartModal();
                }
                return localOrders;
            }
        }
    } catch (e) {
        console.error('Failed to sync orders:', e);
    }
    return window.getPastOrders();
};

window.addPastOrder = function (order) {
    const orders = window.getPastOrders();
    orders.unshift({ ...order, timestamp: Date.now() });
    localStorage.setItem('medelin_past_orders', JSON.stringify(orders.slice(0, 10)));
};

window.getCachedData = function (key) {
    try {
        const data = localStorage.getItem('cache_' + key);
        if (!data) return null;
        const parsed = JSON.parse(data);
        if (Date.now() - parsed.timestamp > 3600000) {
            localStorage.removeItem('cache_' + key);
            return null;
        }
        if (Array.isArray(parsed.data) && parsed.data.length === 0) {
            localStorage.removeItem('cache_' + key);
            return null;
        }
        return parsed.data;
    } catch (e) {
        return null;
    }
};

window.setCachedData = function (key, data) {
    if (!data) return;
    if (Array.isArray(data) && data.length === 0) return;

    try {
        const cacheObj = {
            timestamp: Date.now(),
            data: data,
        };
        localStorage.setItem('cache_' + key, JSON.stringify(cacheObj));
    } catch (e) {}
};

window.loadMedelinData = async function (key, onUpdate = null) {
    const cached = typeof window.getCachedData === 'function' ? window.getCachedData(key) : null;
    
    // Якщо є кеш, повертаємо його відразу для швидкої ініціалізації
    if (cached && Array.isArray(cached) && cached.length > 0) {
        // Запускаємо фонове оновлення
        setTimeout(async () => {
            try {
                const fresh = await window.fetchMedelinData(key);
                if (fresh && Array.isArray(fresh) && fresh.length > 0) {
                    const isDifferent = JSON.stringify(fresh) !== JSON.stringify(cached);
                    if (isDifferent) {
                        window.setCachedData(key, fresh);
                        if (typeof onUpdate === 'function') onUpdate(fresh);
                    }
                }
            } catch (e) {}
        }, 100);
        
        return cached;
    }

    try {
        const data = await window.fetchMedelinData(key);
        if (data && Array.isArray(data) && data.length > 0) {
            window.setCachedData(key, data);
            return data;
        }
    } catch (e) {}

    return [];
};

function openPopup(id) {
    const p = document.getElementById(id);
    if (p) p.classList.add('popup--active');
    document.body.classList.add('body--scroll-locked');
}
function closePopup(id) {
    const p = document.getElementById(id);
    if (p) p.classList.remove('popup--active');
    document.body.classList.remove('body--scroll-locked');
}
window.openPopup = openPopup;
window.closePopup = closePopup;



(function setupMedelinActionDelegation() {
    if (window.__MEDELIN_ACTIONS_READY) return;
    window.__MEDELIN_ACTIONS_READY = true;

    document.addEventListener('click', (event) => {
        const target = event.target;
        if (!target || !target.closest) return;

        const el = target.closest('[data-action]');
        if (!el) return;

        const action = el.getAttribute('data-action') || '';
        if (!action) return;

        const stop = () => {
            if (event && event.preventDefault) event.preventDefault();
            if (event && event.stopPropagation) event.stopPropagation();
        };

        if (action === 'open-cart-modal') {
            stop();
            if (typeof window.openCartModal === 'function') window.openCartModal();
            return;
        }
        if (action === 'close-cart-modal') {
            stop();
            if (typeof window.closeCartModal === 'function') window.closeCartModal();
            return;
        }
        if (action === 'open-checkout-modal') {
            stop();
            if (typeof window.openCheckoutModal === 'function') window.openCheckoutModal();
            return;
        }
        if (action === 'close-checkout-modal') {
            stop();
            if (typeof window.closeCheckoutModal === 'function') window.closeCheckoutModal();
            return;
        }
        if (action === 'close-booking-modal') {
            stop();
            if (typeof window.closeBookingModal === 'function') window.closeBookingModal();
            return;
        }
        if (action === 'open-booking-wizard') {
            stop();
            if (typeof window.openBookingWizard === 'function') window.openBookingWizard(event);
            return;
        }
        if (action === 'close-popup') {
            stop();
            const popupId = el.getAttribute('data-popup-id') || '';
            if (popupId && typeof window.closePopup === 'function') window.closePopup(popupId);
            return;
        }
        if (action === 'reload-page') {
            stop();
            window.location.reload();
            return;
        }
        if (action === 'repeat-order') {
            stop();
            const idx = parseInt(el.getAttribute('data-order-index') || '', 10);
            if (Number.isFinite(idx) && typeof window.repeatOrder === 'function') window.repeatOrder(idx);
            return;
        }
        if (action === 'remove-from-cart') {
            stop();
            const cartType = el.getAttribute('data-cart-type') || '';
            const idx = parseInt(el.getAttribute('data-cart-index') || '', 10);
            if (cartType && Number.isFinite(idx) && typeof window.removeFromCart === 'function') {
                window.removeFromCart(cartType, idx);
            }
            return;
        }
        if (action === 'go-to-payment-step') {
            stop();
            if (typeof window.goToPaymentStep === 'function') window.goToPaymentStep();
            return;
        }
        if (action === 'back-to-details') {
            stop();
            if (typeof window.backToDetails === 'function') window.backToDetails();
            return;
        }
        if (action === 'submit-checkout') {
            stop();
            const method = el.getAttribute('data-method') || '';
            if (method && typeof window.submitCheckout === 'function') window.submitCheckout(method);
            return;
        }
        if (action === 'select-weight') {
            stop();
            if (typeof window.selectWeight === 'function') window.selectWeight(el);
            return;
        }
        if (action === 'add-bean-to-cart') {
            stop();
            const id = el.getAttribute('data-bean-id') || '';
            const name = el.getAttribute('data-bean-name') || '';
            const weightName = el.getAttribute('data-weight-name') || '';
            if (id && weightName && typeof window.addBeanToCart === 'function') {
                window.addBeanToCart(id, name || 'Item', weightName);
            }
            return;
        }
    });

    document.addEventListener('change', (event) => {
        const target = event.target;
        if (!target || !target.closest) return;

        const el = target.closest('[data-action]');
        if (!el) return;
        const action = el.getAttribute('data-action') || '';
        if (!action) return;

        if (action === 'toggle-bean-delivery') {
            if (typeof window.toggleBeanDelivery === 'function') window.toggleBeanDelivery(el.value);
            return;
        }
        if (action === 'toggle-table-input') {
            if (typeof window.toggleTableInput === 'function') window.toggleTableInput(el.value);
            return;
        }
    });
})();

if (typeof window.openItemPopup !== 'function') {
    window.openItemPopup = function (item) {
        const popupImg = document.getElementById('popup-img');
        const popupTitle = document.getElementById('popup-title');
        const popupPrice = document.getElementById('popup-price');
        const popupBody = document.getElementById('popup-body');

        const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';
        const safeName = item && item.name ? String(item.name) : 'Item';
        const priceNum = Number((item && item.price) || 0);
        const safePrice = Number.isFinite(priceNum) ? priceNum : 0;

        if (popupImg) {
            popupImg.src = (item && item.image_url) || defImg;
            popupImg.alt = safeName;
        }
        if (popupTitle) popupTitle.textContent = safeName;
        if (popupPrice) popupPrice.textContent = `${Math.round(safePrice)} ₴`;
        if (popupBody) popupBody.innerHTML = item && item.description ? `<p>${String(item.description)}</p>` : '';

        if (window.openPopup) window.openPopup('item-popup');
    };
}

let cart_menu = JSON.parse(localStorage.getItem('cart_menu') || '[]');
let cart_beans = JSON.parse(localStorage.getItem('cart_beans') || '[]');

function saveCart() {
    localStorage.setItem('cart_menu', JSON.stringify(cart_menu));
    localStorage.setItem('cart_beans', JSON.stringify(cart_beans));
}

function updateCartBadge() {
    const badge = document.getElementById('cart-badge');
    if (!badge) return;
    const path = window.location.pathname;
    const isBeans = path.includes('beans.html');
    const isMenu = path.includes('menu.html');
    let count = isBeans ? cart_beans.length : isMenu ? cart_menu.length : cart_menu.length + cart_beans.length;
    badge.textContent = count;
    badge.classList.toggle('cart-badge--active', count > 0);
    const fab = document.getElementById('cart-fab');
    if (fab) fab.style.display = count > 0 && (isBeans || isMenu) ? 'flex' : 'none';
}

window.addMenuToCart = function (id, name, price) {
    cart_menu.push({ id, name, price });
    saveCart();
    updateCartBadge();
    window.openCartModal();
};

window.addBeanToCart = function (id, name, weightName) {
    const r = document.querySelector(`input[name="${weightName}"]:checked`);
    if (!r) {
        alert('Будь ласка, оберіть вагу');
        return;
    }
    const w = r.value;
    const p = parseInt(r.dataset.price);
    const fullName = `${name} (${w}г)`;
    cart_beans.push({ id, name: fullName, price: p, weight: w });
    saveCart();
    updateCartBadge();
    window.openCartModal();
};

window.openCartModal = function () {
    const container = document.getElementById('cart-modal-container');
    if (!container) return;
    const path = window.location.pathname;
    const isBeans = path.includes('beans.html');
    const activeCart = isBeans ? cart_beans : cart_menu;
    const typeLabel = isBeans ? 'beans' : 'menu';

    let html = `
    <div class="cart-modal__overlay" data-action="close-cart-modal"></div>
    <div class="cart-modal__content">
        <button class="cart-modal__close" type="button" data-action="close-cart-modal"><i class="fas fa-times"></i></button>
        <h3 class="cart-modal__title">Кошик</h3>
        <div class="cart-modal__body">
            <ul class="cart-modal__list">`;

    if (activeCart.length === 0) {
        html += `<li class="cart-modal__empty">Кошик порожній</li>`;
    } else {
        activeCart.forEach((item, index) => {
            html += `<li><div><strong>${item.name}</strong><div class="cart-modal__item-price">${item.price} ₴</div></div>
            <div class="cart-item-end"><button class="cart-modal__remove-btn" type="button" data-action="remove-from-cart" data-cart-type="${typeLabel}" data-cart-index="${index}"><i class="fas fa-trash"></i></button></div></li>`;
        });
    }

    const pastOrders = window.getPastOrders();
    const userData = window.getUserData();
    let pastOrdersHtml = '';
    if (pastOrders.length > 0 || (userData && userData.phone)) {
        pastOrdersHtml += `<div class="cart-modal__past-orders">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h4 class="cart-modal__past-orders-title" style="margin: 0;">Минулі замовлення</h4>
                ${userData.phone ? `<button type="button" class="btn btn--sm btn--outline" onclick="window.syncPastOrders(true)" style="padding: 4px 10px; font-size: 0.7rem; border-radius: 8px;"><i class="fas fa-sync-alt"></i></button>` : ''}
            </div>
            <div class="cart-modal__past-orders-list">`;

        if (pastOrders.length > 0) {
            pastOrders.slice(0, 3).forEach((order, idx) => {
                const date = new Date(order.timestamp).toLocaleDateString('uk-UA');
                const itemCount = order.items && order.items.length ? `${order.items.length} тов.` : 'Замовлення';
                pastOrdersHtml += `<div class="past-order">
                    <div class="past-order__meta">
                        <strong>${itemCount} — ${order.total} ₴</strong>
                        <div class="past-order__date">${date}</div>
                    </div>
                    ${order.items && order.items.length > 0 ? `<button class="btn past-order__btn" type="button" data-action="repeat-order" data-order-index="${idx}">Повторити</button>` : ''}
                </div>`;
            });
        } else {
            pastOrdersHtml += `<div class="cart-modal__empty" style="padding: 10px 0;">Натисніть 🔄 щоб оновити історію</div>`;
        }

        pastOrdersHtml += `</div></div>`;
    }

    const total = activeCart.reduce((s, i) => s + i.price, 0);
    html += `</ul>
    ${pastOrdersHtml}
    <div class="cart-modal__footer-fixed">
        <div class="cart-modal__total"><span>Разом:</span><span>${total} ₴</span></div>
        <div class="cart-modal__btn-container">
            ${
                total > 0
                    ? `
                <button class="btn btn--checkout" id="btn-open-checkout"><i class="fas fa-check cart-modal__checkout-btn-icon"></i> Замовити</button>
            `
                    : ''
            }
            <button class="btn btn--outline btn--full-width" type="button" data-action="close-cart-modal"><i class="fas fa-shopping-bag cart-modal__continue-btn-icon"></i> Продовжити замовлення</button>
        </div>
    </div>`;
    html += `</div></div>`;

    container.innerHTML = html;
    container.classList.add('cart-modal--active');
    document.body.classList.add('body--scroll-locked');

    const btn = document.getElementById('btn-open-checkout');
    if (btn) btn.setAttribute('data-action', 'open-checkout-modal');
};

window.repeatOrder = function (idx) {
    const pastOrders = window.getPastOrders();
    const order = pastOrders[idx];
    if (!order) return;

    if (order.type === 'beans') {
        cart_beans = [...cart_beans, ...order.items];
    } else {
        cart_menu = [...cart_menu, ...order.items];
    }
    saveCart();
    updateCartBadge();
    window.openCartModal();
    window.showToast('Замовлення додано до кошика', 'success');
};

window.closeCartModal = function () {
    const c = document.getElementById('cart-modal-container');
    if (c) c.classList.remove('cart-modal--active');
    document.body.classList.remove('body--scroll-locked');
};

window.removeFromCart = function (t, i) {
    if (t === 'menu') cart_menu.splice(i, 1);
    else cart_beans.splice(i, 1);
    saveCart();
    updateCartBadge();
    window.openCartModal();
};

window.closeCheckoutModal = function () {
    const c = document.getElementById('checkout-modal-container');
    if (c) c.classList.remove('cart-modal--active');
    document.body.classList.remove('body--scroll-locked');
};

window.getURLParameter = function (name) {
    return new URLSearchParams(window.location.search).get(name);
};

window.openCheckoutModal = function () {
    window.closeCartModal();
    const container = document.getElementById('checkout-modal-container');
    if (!container) return;

    const isBeans = window.location.pathname.includes('beans.html');
    const activeCart = isBeans ? cart_beans : cart_menu;
    const total = activeCart.reduce((s, i) => s + i.price, 0);

    container.innerHTML = `
        <div class="cart-modal__overlay"></div>
        <div class="cart-modal__content checkout-modal checkout-modal-container--large">
            <div class="checkout-modal__loading">
                <h3 class="checkout-modal__title">Оформлення замовлення</h3>
                <p class="checkout-modal__loading-text">Завантажуємо дані…</p>
            </div>
        </div>
    `;
    container.classList.add('cart-modal--active');

    const qrZaklad = window.getURLParameter('zaklad');
    const qrStolyk = window.getURLParameter('stolyk');

    (async () => {
        const locations = await window.loadMedelinData('locations');
        const hasLocationMatch = locations.some((l) => qrZaklad === l._id);
        const locOpts =
            locations.length > 0
                ? `<option value="" disabled ${qrZaklad && hasLocationMatch ? '' : 'selected'}>Оберіть кав'ярню…</option>${locations
                      .map((l) => `<option value="${l.id || l._id}" ${qrZaklad === (l.id || l._id) ? 'selected' : ''}>${l.name}</option>`)
                      .join('')}`
                : '<option value="" disabled selected>Локації недоступні</option>';
        const userData = window.getUserData();

        container.innerHTML = `
            <div class="cart-modal__overlay" data-action="close-checkout-modal"></div>
            <div class="cart-modal__content checkout-modal checkout-modal-container--large">
                <button class="cart-modal__close" type="button" data-action="close-checkout-modal"><i class="fas fa-times"></i></button>

                <h3 class="checkout-modal__title">Оформлення замовлення</h3>

                <div id="checkout-details-step">
                    <form id="checkout-details-form" class="checkout-modal__form">
                        <div class="form-group">
                            <label class="form-label">Ваше ім'я</label>
                            <input type="text" name="name" placeholder="Ваше ім'я" value="${userData.name || ''}" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Телефон</label>
                            <input type="tel" name="phone" placeholder="Телефон (+380...)" value="${userData.phone || ''}" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Telegram (@username) — опційно</label>
                            <input type="text" name="tg" placeholder="Telegram (@username) — опційно" value="${userData.tg || ''}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Побажання чи уточнення — опційно</label>
                            <textarea name="comment" placeholder="Ваші побажання до замовлення..." rows="2"></textarea>
                        </div>

                        ${
                            isBeans
                                ? `
                            <div class="delivery-section">
                                <p class="form-label">Спосіб отримання:</p>
                                <select name="delivery_type" id="delivery_type" data-action="toggle-bean-delivery" required>
                                    <option value="" disabled selected>Оберіть спосіб...</option>
                                    <option value="pickup">Самовивіз з кав'ярні</option>
                                    <option value="nova_poshta">Нова Пошта (по Україні)</option>
                                </select>
                            </div>

                            <div id="pickup_location_wrap" class="delivery-section--pickup" style="display:none; margin-top: 1.5rem;">
                                <p class="form-label">Оберіть кав'ярню:</p>
                                <select name="location">${locOpts}</select>
                            </div>

                            <div id="np_details_wrap" class="np-container" style="display:none; margin-top: 1.5rem;">
                                <p class="form-label">Місто:</p>
                                <div class="search-wrapper">
                                    <input type="text" id="np_city_search" placeholder="Введіть назву міста...">
                                    <div id="np_city_results" class="np-search-results"></div>
                                </div>
                                <input type="hidden" name="np_city_ref" id="np_city_ref">
                                <input type="hidden" name="np_city_name" id="np_city_name">

                                <div id="np_warehouse_search_wrap" class="np-warehouse-search" style="display:none; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(0,0,0,0.05);">
                                    <p class="form-label">Відділення або поштомат (№ або вул):</p>
                                    <div class="search-wrapper">
                                        <input type="text" id="np_wh_input" placeholder="Наприклад: 1 або Головна">
                                        <div id="np_wh_results" class="np-search-results"></div>
                                    </div>
                                    <input type="hidden" name="np_warehouse" id="np_warehouse_final">
                                    <div id="np_selected_wh_display" class="np-selected-display"></div>
                                </div>
                            </div>
                        `
                                : `
                            <div class="delivery-section" ${qrZaklad && hasLocationMatch ? 'style="display:none;"' : ''}>
                                <p class="form-label">Оберіть кав'ярню:</p>
                                <select name="location" required>${locOpts}</select>
                            </div>
                            <div class="delivery-section" ${qrStolyk && hasLocationMatch ? 'style="display:none;"' : ''}>
                                <p class="form-label">Як ви будете забирати?</p>
                                <select name="type" data-action="toggle-table-input">
                                    <option value="takeaway" ${qrStolyk && hasLocationMatch ? '' : 'selected'}>З собою</option>
                                    <option value="in_house" ${qrStolyk && hasLocationMatch ? 'selected' : ''}>В закладі</option>
                                </select>
                            </div>
                            <div id="chk_table_wrap" style="${qrStolyk && hasLocationMatch ? 'display:none;' : 'display:none;'} margin-top: 20px;">
                                <p class="form-label">Номер столика:</p>
                                <input type="text" name="table_number" id="chk_table" placeholder="Наприклад: 5" value="${qrStolyk || ''}">
                            </div>
                            <div id="payment-mode-section" style="${qrStolyk && hasLocationMatch ? 'display:block;' : 'display:none;'} margin-top: 20px;">
                                <p class="form-label">Оплата:</p>
                                <select name="payment_mode" id="payment_mode">
                                    <option value="pay_now">Оплатити зараз</option>
                                    <option value="pay_at_checkout">На касі</option>
                                </select>
                            </div>
                        `
                        }
                    </form>
                    <div class="checkout-modal__footer">
                        <div class="checkout-modal__total">
                            <span>Всього:</span><span>${total} ₴</span>
                        </div>
                        <button type="button" class="btn--checkout" data-action="go-to-payment-step">Продовжити</button>
                    </div>
                </div>

                <div id="checkout-payment-step" style="display:none;">
                    <p class="payment-title">Оберіть метод оплати:</p>
                    <div class="payment-methods-grid">
                        <button class="payment-btn" type="button" data-action="submit-checkout" data-method="card">
                            <i class="fas fa-credit-card"></i> <span>Оплата картою</span>
                        </button>
                        <button class="payment-btn" type="button" data-action="submit-checkout" data-method="applepay">
                            <i class="fab fa-apple-pay"></i> <span>Apple Pay</span>
                        </button>
                        <button class="payment-btn" type="button" data-action="submit-checkout" data-method="googlepay">
                            <i class="fab fa-google-pay"></i> <span>Google Pay</span>
                        </button>
                        <button class="payment-btn" type="button" data-action="submit-checkout" data-method="privatpay">
                            <i class="fas fa-university"></i> <span>PrivatPay</span>
                        </button>
                        <button class="payment-btn" type="button" data-action="submit-checkout" data-method="monobank">
                            <i class="fas fa-wallet"></i> <span>MonoPay</span>
                        </button>
                    </div>
                    <div style="padding: 0 1.5rem 1.5rem;">
                        <button class="btn-back" type="button" data-action="back-to-details"><i class="fas fa-arrow-left btn__icon--left"></i> Назад до деталей</button>
                    </div>
                </div>
            </div>`;
        if (isBeans) initNovaPoshtaSearch();

        if (locations.length === 0) {
            container.querySelectorAll('select[name="location"]').forEach((select) => (select.disabled = true));
            const btn = container.querySelector('.btn--checkout');
            if (btn) btn.disabled = true;
            if (window.showToast) window.showToast('Не вдалося завантажити список кавʼярень.', 'error');
        }
    })();
};

window.toggleBeanDelivery = function (val) {
    const npWrap = document.getElementById('np_details_wrap');
    const pickupWrap = document.getElementById('pickup_location_wrap');
    if (val === 'nova_poshta') {
        if (npWrap) npWrap.style.display = 'block';
        if (pickupWrap) pickupWrap.style.display = 'none';
    } else {
        if (npWrap) npWrap.style.display = 'none';
        if (pickupWrap) pickupWrap.style.display = 'block';
    }
};

function debounce(func, timeout = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
            func.apply(this, args);
        }, timeout);
    };
}

function initNovaPoshtaSearch() {
    const inp = document.getElementById('np_city_search');
    const res = document.getElementById('np_city_results');
    const whWrap = document.getElementById('np_warehouse_search_wrap');
    if (!inp) return;

    const searchWh = debounce((val) => {
        const ref = document.getElementById('np_city_ref').value;
        const whRes = document.getElementById('np_wh_results');
        if (!ref || !whRes) return;
        whRes.innerHTML = '<div class="np-result-item" style="opacity:0.5;">Шукаємо...</div>';
        whRes.style.display = 'block';
        fetch(`${window.API_BASE_URL}/api/nova-poshta/warehouses?cityRef=${ref}&search=${encodeURIComponent(val)}`)
            .then((r) => r.json())
            .then((data) => {
                whRes.innerHTML = '';
                if (!data || data.length === 0) {
                    whRes.innerHTML = '<div class="np-result-item">Нічого не знайдено</div>';
                } else {
                    if (val && val.length > 0) {
                        const lowVal = val.toLowerCase();
                        data.sort((a, b) => {
                            const descA = a.Description.toLowerCase();
                            const descB = b.Description.toLowerCase();
                            const numRegex = new RegExp(`№\\s*${val}(\\D|$)`);
                            const matchA = numRegex.test(a.Description);
                            const matchB = numRegex.test(b.Description);
                            if (matchA && !matchB) return -1;
                            if (!matchA && matchB) return 1;
                            const startsA = descA.includes(`№${lowVal}`) || descA.includes(`№ ${lowVal}`);
                            const startsB = descB.includes(`№${lowVal}`) || descB.includes(`№ ${lowVal}`);
                            if (startsA && !startsB) return -1;
                            if (!startsA && startsB) return 1;
                            return 0;
                        });
                    }
                    data.forEach((w) => {
                        const item = document.createElement('div');
                        item.className = 'np-result-item';
                        const icon = w.CategoryOfWarehouse === 'Postomat' ? 'fa-box' : 'fa-house-chimney';
                        item.innerHTML = `<i class="fas ${icon}" style="margin-right:8px; opacity:0.6;"></i> ${w.Description}`;
                        item.onclick = () => {
                            document.getElementById('np_wh_input').value = w.Description;
                            document.getElementById('np_warehouse_final').value = w.Description;
                            document.getElementById('np_selected_wh_display').textContent = 'Вибрано: ' + w.Description;
                            whRes.style.display = 'none';
                        };
                        whRes.appendChild(item);
                    });
                }
            });
    }, 350);

    const searchCities = debounce((val) => {
        if (val.length < 2) {
            res.style.display = 'none';
            return;
        }
        res.innerHTML = '<div class="np-result-item" style="opacity:0.5;">Шукаємо...</div>';
        res.style.display = 'block';
        fetch(`${window.API_BASE_URL}/api/nova-poshta/cities?search=${encodeURIComponent(val)}`)
            .then((r) => r.json())
            .then((cities) => {
                res.innerHTML = '';
                if (!cities || cities.length === 0) {
                    res.innerHTML = '<div class="np-result-item">Не знайдено</div>';
                } else {
                    cities.forEach((c) => {
                        const item = document.createElement('div');
                        item.className = 'np-result-item';
                        item.textContent = c.Present;
                        item.onclick = () => {
                            inp.value = c.Present;
                            document.getElementById('np_city_ref').value = c.Ref;
                            document.getElementById('np_city_name').value = c.Present;
                            res.style.display = 'none';
                            whWrap.style.display = 'block';
                            document.getElementById('np_wh_input').value = '';
                            searchWh('');
                        };
                        res.appendChild(item);
                    });
                }
            });
    }, 400);

    inp.oninput = (e) => searchCities(e.target.value.trim());
    const whInp = document.getElementById('np_wh_input');
    if (whInp) whInp.oninput = (e) => searchWh(e.target.value.trim());
}

window.goToPaymentStep = function () {
    const f = document.getElementById('checkout-details-form');
    if (!f || !f.reportValidity()) return;
    const isBeans = window.location.pathname.includes('beans.html');
    if (isBeans && f.elements['delivery_type'].value === 'nova_poshta') {
        if (!document.getElementById('np_warehouse_final').value) {
            window.showToast('Будь ласка, оберіть відділення Нової Пошти', 'error');
            return;
        }
    }
    if (!isBeans && f.elements['type'] && f.elements['type'].value === 'in_house') {
        const tableNum =
            f.elements['table_number'] && typeof f.elements['table_number'].value === 'string'
                ? f.elements['table_number'].value.trim()
                : '';
        if (!tableNum) {
            window.showToast('Будь ласка, вкажіть номер столика', 'error');
            f.elements['table_number'].focus();
            return;
        }
    }
    const orderType = f.elements['type'] ? f.elements['type'].value : '';
    const paymentMode = f.elements['payment_mode'] ? f.elements['payment_mode'].value : '';
    if (!isBeans && orderType === 'takeaway') {
        document.getElementById('checkout-details-step').style.display = 'none';
        document.getElementById('checkout-payment-step').style.display = 'block';
    } else if (paymentMode === 'pay_at_checkout') {
        window.submitCheckout('cash');
    } else {
        document.getElementById('checkout-details-step').style.display = 'none';
        document.getElementById('checkout-payment-step').style.display = 'block';
    }
};

window.backToDetails = function () {
    document.getElementById('checkout-details-step').style.display = 'block';
    document.getElementById('checkout-payment-step').style.display = 'none';
};

window.submitCheckout = function (method) {
    const btn = window.event ? window.event.target.closest('button') : null;
    
    if (window.CURRENT_ORDER_ID) {
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обробка...';
        }
        const data = { order_id: window.CURRENT_ORDER_ID, payment_method: method };
        fetch(`${window.API_BASE_URL}/api/repay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        })
        .then(r => r.json())
        .then(res => {
            if (res.status === 'ok') {
                cart_menu.length = 0;
                cart_beans.length = 0;
                localStorage.removeItem('cart_menu');
                localStorage.removeItem('cart_beans');
                updateCartBadge();

                if (res.url) window.location.href = res.url;
                else if (res.data && res.signature) {
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'https://www.liqpay.ua/api/3/checkout';
                    form.innerHTML = `<input type="hidden" name="data" value="${res.data}"><input type="hidden" name="signature" value="${res.signature}">`;
                    document.body.appendChild(form);
                    form.submit();
                }
            } else {
                window.showToast('Помилка: ' + (res.detail || 'невідома помилка'), 'error');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Спробувати ще раз';
                }
            }
        });
        return;
    }

    const f = document.getElementById('checkout-details-form');
    const fd = new FormData(f);
    const isBeans = window.location.pathname.includes('beans.html');
    const activeCart = isBeans ? cart_beans : cart_menu;
    window.setUserData({
        name: fd.get('name'),
        phone: fd.get('phone'),
        tg: fd.get('tg'),
    });
    const data = {
        user_details: {
            name: fd.get('name'),
            phone: fd.get('phone'),
            tg: fd.get('tg'),
            comment: fd.get('comment'),
            location: fd.get('location'),
            type: fd.get('type'),
            table_number: fd.get('table_number'),
            payment_mode: method === 'cash' ? 'pay_at_checkout' : 'pay_now',
            delivery_type: fd.get('delivery_type'),
            np_city_ref: fd.get('np_city_ref'),
            np_city_name: fd.get('np_city_name'),
            np_warehouse: fd.get('np_warehouse'),
        },
        cart_menu: activeCart,
        payment_method: method === 'cash' ? 'card' : method,
    };
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обробка...';
    }
    fetch(`${window.API_BASE_URL}/api/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
        .then((r) => r.json())
        .then((res) => {
            if (res.status === 'ok') {
                window.addPastOrder({
                    items: [...activeCart],
                    total: activeCart.reduce((s, i) => s + i.price, 0),
                    type: isBeans ? 'beans' : 'menu',
                });
                if (res.url) {
                    cart_menu.length = 0;
                    cart_beans.length = 0;
                    localStorage.removeItem('cart_menu');
                    localStorage.removeItem('cart_beans');
                    updateCartBadge();
                    window.location.href = res.url;
                }
                else if (res.data && res.signature) {
                    cart_menu.length = 0;
                    cart_beans.length = 0;
                    localStorage.removeItem('cart_menu');
                    localStorage.removeItem('cart_beans');
                    updateCartBadge();

                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'https://www.liqpay.ua/api/3/checkout';
                    form.innerHTML = `<input type="hidden" name="data" value="${res.data}"><input type="hidden" name="signature" value="${res.signature}">`;
                    document.body.appendChild(form);
                    form.submit();
                } else {
                    window.showToast('Замовлення прийнято!', 'success');
                    cart_menu.length = 0;
                    cart_beans.length = 0;
                    localStorage.removeItem('cart_menu');
                    localStorage.removeItem('cart_beans');
                    updateCartBadge();
                    window.closeCheckoutModal();
                }
            } else {
                let errorMsg = res.detail;
                if (typeof errorMsg === 'object') {
                    errorMsg = JSON.stringify(errorMsg);
                }
                window.showToast('Помилка: ' + (errorMsg || 'невідома помилка'), 'error');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Продовжити';
                }
            }
        })
        .catch((err) => {
            window.showToast("Помилка відправки.", 'error');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Спробувати ще раз';
            }
        });
};

window.openBookingWizard = function (e) {
    if (e) e.preventDefault();
    let container = document.getElementById('booking-modal-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'booking-modal-container';
        document.body.appendChild(container);
    }
    const userData = window.getUserData();
    container.innerHTML = `
    <div class="booking-modal__overlay" data-action="close-booking-modal"></div>
    <div class="booking-modal__content checkout-modal">
        <button class="booking-modal__close" type="button" data-action="close-booking-modal"><i class="fas fa-times"></i></button>
        <h3 class="checkout-modal__title">Бронювання столика</h3>
        <form id="booking-form" class="booking-modal__form">
            <div class="form-group">
                <label class="form-label">Ваше ім'я</label>
                <input type="text" name="name" placeholder="Як до вас звертатися?" value="${userData.name || ''}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Телефон</label>
                <input type="tel" name="phone" placeholder="+380..." value="${userData.phone || ''}" required>
            </div>
            <div class="form-group">
                <label class="form-label">Telegram (@username) — опційно</label>
                <input type="text" name="tg" placeholder="Telegram (@username)" value="${userData.tg || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">Оберіть локацію</label>
                <select name="location_id" id="book_loc" required>
                    <option value="" disabled selected>Завантаження...</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Дата візиту</label>
                <input type="date" name="date" required min="${new Date().toISOString().split('T')[0]}">
            </div>
            <div class="form-group">
                <label class="form-label">Час</label>
                <input type="time" name="time" required>
            </div>
            <div class="form-group">
                <label class="form-label">Кількість гостей</label>
                <input type="number" name="guests" min="1" max="20" value="2" required>
            </div>
            <div class="form-group">
                <label class="form-label">Побажання (опційно)</label>
                <textarea name="wishes" placeholder="Наприклад: біля вікна" rows="2"></textarea>
            </div>
            <button type="submit" class="btn--checkout" style="margin-top: 1rem;">Забронювати</button>
        </form>
    </div>`;
    container.classList.add('booking-modal--active');
    document.body.classList.add('body--scroll-locked');
    (async () => {
        const locs = await window.loadMedelinData('locations');
        const sel = document.getElementById('book_loc');
        const submitBtn = document.querySelector('#booking-form button[type="submit"]');
        if (!sel) return;

        if (locs.length > 0) {
            sel.innerHTML = `<option value="" disabled selected>Оберіть кав'ярню…</option>${locs
                .map((l) => `<option value="${l._id}">${l.name}</option>`)
                .join('')}`;
            sel.disabled = false;
            if (submitBtn) submitBtn.disabled = false;
        } else {
            sel.innerHTML = '<option value="" disabled selected>Локації недоступні</option>';
            sel.disabled = true;
            if (submitBtn) submitBtn.disabled = true;
        }
    })();
    document.getElementById('booking-form').onsubmit = function (ev) {
        ev.preventDefault();
        const fd = new FormData(this);
        const btn = this.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обробка...';
        const data = {
            location: fd.get('location_id'),
            date: fd.get('date'),
            time: fd.get('time'),
            guests: String(fd.get('guests')),
            name: fd.get('name'),
            phone: fd.get('phone'),
            tg: fd.get('tg'),
            wishes: fd.get('wishes'),
        };
        window.setUserData({ name: data.name, phone: data.phone, tg: data.tg });
        fetch(`${window.API_BASE_URL}/api/booking`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        })
            .then((r) => r.json())
            .then((res) => {
                if (res.status === 'ok') {
                    window.showToast('Бронювання прийнято!', 'success');
                    window.closeBookingModal();
                } else {
                    let errorMsg = res.detail;
                    if (typeof errorMsg === 'object') {
                        errorMsg = JSON.stringify(errorMsg);
                    }
                    window.showToast('Помилка: ' + (errorMsg || 'невідома помилка'), 'error');
                    btn.disabled = false;
                    btn.textContent = 'Забронювати';
                }
            })
            .catch(() => {
                window.showToast("Помилка з'єднання", 'error');
                btn.disabled = false;
                btn.textContent = 'Забронювати';
            });
    };
};

window.closeBookingModal = function () {
    const c = document.getElementById('booking-modal-container');
    if (c) {
        c.classList.remove('booking-modal--active');
        document.body.classList.remove('body--scroll-locked');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Secret Admin Entry Logic
    const logo = document.querySelector('.header__logo');
    if (logo) {
        let logoClicks = 0;
        let logoTimer = null;
        let adminTimer = null;

        logo.addEventListener('click', (e) => {
            logoClicks++;
            
            // Завжди перериваємо стандартний перехід, бо ми самі вирішуємо куди йти
            e.preventDefault();
            
            if (logoTimer) clearTimeout(logoTimer);
            if (adminTimer) clearTimeout(adminTimer);

            if (logoClicks === 1) {
                // Якщо за 500мс більше не було кліків - йдемо на головну
                logoTimer = setTimeout(() => {
                    if (logoClicks === 1) window.location.href = 'index.html';
                    logoClicks = 0;
                }, 500);
            } else if (logoClicks === 7) {
                // Чітко 7 кліків - чекаємо 1 сек і в адмінку
                adminTimer = setTimeout(() => {
                    if (logoClicks === 7) {
                        // Для зручності додаємо auth якщо він є в пам'яті, 
                        // або просто перекидаємо на сторінку
                        const auth = localStorage.getItem('medelin_admin_auth') || 'medelin2026';
                        window.location.href = `admin-panel.html?auth=${auth}`;
                    }
                    logoClicks = 0;
                }, 1000);
            } else if (logoClicks >= 8) {
                // 8 і більше - скидаємо і на головну
                logoClicks = 0;
                window.location.href = 'index.html';
            }
        });
    }

    updateCartBadge();
    if (window.setupMobileMenu) window.setupMobileMenu();
    if (typeof window.syncPastOrders === 'function') window.syncPastOrders();
    
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealable--active');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.revealable, .product-card, .promo-card, .category').forEach(el => {
        if (!el.classList.contains('revealable')) el.classList.add('revealable');
        revealObserver.observe(el);
    });

    const orderId = window.getURLParameter('order_id');
    if (orderId) {
        window.CURRENT_ORDER_ID = orderId;
        const container = document.getElementById('checkout-modal-container');
        if (container) {
            container.innerHTML = `
                <div class="cart-modal__overlay"></div>
                <div class="cart-modal__content checkout-modal">
                    <div class="checkout-modal__loading" style="padding: 3rem; text-align: center;">
                        <i class="fas fa-spinner fa-spin fa-3x" style="color: var(--color-coffee); margin-bottom: 1rem;"></i>
                        <p>Завантажуємо деталі замовлення...</p>
                    </div>
                </div>`;
            container.classList.add('cart-modal--active');
            
            fetch(`${window.API_BASE_URL}/api/orders/${orderId}`)
                .then(r => {
                    if (!r.ok) {
                        return r.json().catch(() => ({ detail: 'Сервер повернув помилку' }));
                    }
                    return r.json();
                })
                .then(order => {
                    if (order && order.order_id) {
                        container.innerHTML = `
                        <div class="cart-modal__overlay" data-action="close-checkout-modal"></div>
                        <div class="cart-modal__content checkout-modal">
                            <button class="cart-modal__close" type="button" data-action="close-checkout-modal"><i class="fas fa-times"></i></button>
                            <h3 class="checkout-modal__title">Оплата замовлення</h3>
                            <div id="checkout-payment-step">
                                <div style="padding: 0 1.5rem 1rem; text-align: center;">
                                    <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">Сума до оплати:</p>
                                    <p style="font-size: 2.2rem; font-weight: 900; color: var(--color-coffee);">${order.total} ₴</p>
                                </div>
                                <p class="payment-title">Оберіть метод оплати:</p>
                                <div class="payment-methods-grid">
                                    <button class="payment-btn" type="button" data-action="submit-checkout" data-method="card">
                                        <i class="fas fa-credit-card"></i> <span>Оплата картою</span>
                                    </button>
                                    <button class="payment-btn" type="button" data-action="submit-checkout" data-method="applepay">
                                        <i class="fab fa-apple-pay"></i> <span>Apple Pay</span>
                                    </button>
                                    <button class="payment-btn" type="button" data-action="submit-checkout" data-method="googlepay">
                                        <i class="fab fa-google-pay"></i> <span>Google Pay</span>
                                    </button>
                                    <button class="payment-btn" type="button" data-action="submit-checkout" data-method="privatpay">
                                        <i class="fas fa-university"></i> <span>PrivatPay</span>
                                    </button>
                                    <button class="payment-btn" type="button" data-action="submit-checkout" data-method="monobank">
                                        <i class="fas fa-wallet"></i> <span>MonoPay</span>
                                    </button>
                                </div>
                            </div>
                        </div>`;
                    } else {
                        window.showToast('Замовлення не знайдено', 'error');
                        window.closeCheckoutModal();
                    }
                })
                .catch(() => {
                    window.showToast('Помилка завантаження замовлення', 'error');
                    window.closeCheckoutModal();
                });
        }
    }
});

window.selectWeight = function (el) {
    const parent = el.closest('.popup__weights-selection');
    if (!parent) return;
    parent.querySelectorAll('.weight-label').forEach((l) => l.classList.remove('weight-label--active'));
    el.classList.add('weight-label--active');
    const radio = el.querySelector('input');
    if (radio) radio.checked = true;
};

window.toggleChoice = function (el, baseP, type) {
    if (type !== 'addon') {
        const parent = el.parentElement;
        if (parent) {
            parent.querySelectorAll('.choice-chip').forEach((c) => c.classList.remove('choice-chip--active'));
        }
        el.classList.add('choice-chip--active');
    } else {
        el.classList.toggle('choice-chip--active');
    }
    if (window.updatePopupPrice) window.updatePopupPrice(baseP);
};

window.toggleTableInput = function (v) {
    const tableWrap = document.getElementById('chk_table_wrap');
    const paymentModeSection = document.getElementById('payment-mode-section');
    if (tableWrap) tableWrap.style.display = v === 'in_house' ? 'block' : 'none';
    if (paymentModeSection) paymentModeSection.style.display = v === 'in_house' ? 'block' : 'none';
};
