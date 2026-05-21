const _host = window.location.hostname;
const _port = window.location.port;
const _proto = window.location.protocol;
const isFileProto = _proto === 'file:';
const isLocal = _host === 'localhost' || _host === '127.0.0.1' || _host === '';

window.API_BASE_URL = '';
if (isFileProto) {
    window.API_BASE_URL = 'https://medelin.onrender.com';
} else if (isLocal && _port !== '8000' && _port !== '') {
    window.API_BASE_URL = 'http://localhost:8000';
}

window.fetchMedelinData = async function (key) {
    const endpoints = [];
    const fileName = `${key}.json`;
    
    // ПРІОРИТЕТ 1: Прямий API запит до сервера (завжди актуальні дані з пам'яті)
    if (window.API_BASE_URL) {
        endpoints.push(`${window.API_BASE_URL}/api/${key}`);
    } else {
        // Якщо ми на самому сервері, використовуємо відносний шлях
        endpoints.push(`/api/${key}`);
    }

    // ПРІОРИТЕТ 2: Статичні JSON файли (кеш на диску)
    if (window.API_BASE_URL) {
        endpoints.push(`${window.API_BASE_URL}/cache/${fileName}`);
    }
    
    const isRoot = !window.location.pathname.includes('/pages/');
    if (isRoot) {
        endpoints.push(`./cache/${fileName}`);
    } else {
        endpoints.push(`../../cache/${fileName}`);
        endpoints.push(`../cache/${fileName}`);
    }
    
    endpoints.push(`/cache/${fileName}`);

    console.log(`[Medelin] Пошук даних: ${key}`);

    for (const url of endpoints) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            
            // Додаємо cache-buster (timestamp)
            const finalUrl = url.includes('?') ? `${url}&t=${Date.now()}` : `${url}?t=${Date.now()}`;
            const response = await fetch(finalUrl, { signal: controller.signal });
            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                if (Array.isArray(data) && data.length > 0) {
                    console.log(`[Medelin] OK: ${key} завантажено з ${url}`);
                    return data;
                }
            }
        } catch (e) {
        }
    }
    
    console.error(`[Medelin] Помилка: не знайдено даних для ${key}`);
    return null;
};

window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error(`[Medelin Error] ${msg} at ${url}:${lineNo}:${columnNo}`, error);
    if (window.showToast) {
        window.showToast('Сталася помилка в роботі сайту. Дивіться консоль (F12).', 'error');
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

window.loadMedelinData = async function (key) {
    const cached = typeof window.getCachedData === 'function' ? window.getCachedData(key) : null;
    if (cached && Array.isArray(cached) && cached.length > 0) {
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
    document.body.style.overflow = 'hidden';
}
function closePopup(id) {
    const p = document.getElementById(id);
    if (p) p.classList.remove('popup--active');
    document.body.style.overflow = '';
}
window.openPopup = openPopup;
window.closePopup = closePopup;

if (typeof window.openItemPopup !== 'function') {
    window.openItemPopup = function (item) {
        const popupImg = document.getElementById('popup-img');
        const popupTitle = document.getElementById('popup-title');
        const popupPrice = document.getElementById('popup-price');
        const popupBody = document.getElementById('popup-body');

        const defImg = 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?q=80&w=1061&auto=format&fit=crop';
        const safeName = item?.name ? String(item.name) : 'Item';
        const priceNum = Number(item?.price || 0);
        const safePrice = Number.isFinite(priceNum) ? priceNum : 0;

        if (popupImg) {
            popupImg.src = item?.image_url || defImg;
            popupImg.alt = safeName;
        }
        if (popupTitle) popupTitle.textContent = safeName;
        if (popupPrice) popupPrice.textContent = `${Math.round(safePrice)} ₴`;
        if (popupBody) popupBody.innerHTML = item?.description ? `<p>${String(item.description)}</p>` : '';

        window.openPopup?.('item-popup');
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
    badge.classList.toggle('active', count > 0);
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
    <div class="cart-modal__overlay" onclick="window.closeCartModal()"></div>
    <div class="cart-modal__content">
        <button class="cart-modal__close" onclick="window.closeCartModal()"><i class="fas fa-times"></i></button>
        <h3 class="cart-modal__title">Кошик</h3>
        <div class="cart-modal__body">
            <ul class="cart-modal__list">`;

    if (activeCart.length === 0) {
        html += `<li class="cart-modal__empty">Кошик порожній</li>`;
    } else {
        activeCart.forEach((item, index) => {
            html += `<li><div><strong>${item.name}</strong><div class="item-price">${item.price} ₴</div></div>
            <div class="cart-item-end"><button class="btn-remove-item" onclick="window.removeFromCart('${typeLabel}', ${index})"><i class="fas fa-trash"></i></button></div></li>`;
        });
    }

    const pastOrders = window.getPastOrders();
    let pastOrdersHtml = '';
    if (pastOrders.length > 0) {
        pastOrdersHtml += `<div class="cart-modal__past-orders">
            <h4 class="cart-modal__past-orders-title">Минулі замовлення</h4>
            <div class="cart-modal__past-orders-list">`;

        pastOrders.slice(0, 3).forEach((order, idx) => {
            const date = new Date(order.timestamp).toLocaleDateString('uk-UA');
            pastOrdersHtml += `<div class="past-order">
                <div class="past-order__meta">
                    <strong>${order.items.length} тов. — ${order.total} ₴</strong>
                    <div class="past-order__date">${date}</div>
                </div>
                <button class="btn past-order__btn" onclick="window.repeatOrder(${idx})">Повторити</button>
            </div>`;
        });

        pastOrdersHtml += `</div></div>`;
    }

    const total = activeCart.reduce((s, i) => s + i.price, 0);
    html += `</ul>
    ${pastOrdersHtml}
    <div class="cart-modal__footer-fixed">
        <div class="cart-modal__total"><span>Разом:</span><span>${total} ₴</span></div>
        <div class="btn-container">
            ${
                total > 0
                    ? `
                <button class="btn btn-checkout-primary" id="btn-open-checkout"><i class="fas fa-check cart-modal__checkout-btn-icon"></i> Замовити</button>
            `
                    : ''
            }
            <button class="btn btn--outline btn--full-width" onclick="window.closeCartModal()"><i class="fas fa-shopping-bag cart-modal__continue-btn-icon"></i> Продовжити замовлення</button>
        </div>
    </div>`;
    html += `</div></div>`;

    container.innerHTML = html;
    container.classList.add('cart-modal--active');
    document.body.style.overflow = 'hidden';

    const btn = document.getElementById('btn-open-checkout');
    if (btn) btn.onclick = () => window.openCheckoutModal();
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
    document.body.style.overflow = '';
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
    document.body.style.overflow = '';
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
        <div class="cart-modal__content checkout-modal-modern checkout-modal-container--large">
            <div class="loading">
                <h3 class="checkout-title">Оформлення замовлення</h3>
                <p class="checkout-loading__text">Завантажуємо дані…</p>
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
            <div class="cart-modal__overlay" onclick="window.closeCheckoutModal()"></div>
            <div class="cart-modal__content checkout-modal-modern checkout-modal-container--large">
                <button class="cart-modal__close" onclick="window.closeCheckoutModal()"><i class="fas fa-times"></i></button>

                <h3 class="checkout-title">Оформлення замовлення</h3>

                <div id="checkout-details-step">
                    <form id="checkout-details-form" class="checkout-form">
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
                            <textarea name="comment" placeholder="Ваші побажання до замовлення..." rows="2" style="width: 100%; border: 1px solid var(--gray-border, #e2e8f0); border-radius: var(--radius-sm, 0.375rem); padding: 0.75rem; font-family: inherit; font-size: 1rem; resize: vertical;"></textarea>
                        </div>

                        ${
                            isBeans
                                ? `
                            <div class="delivery-section">
                                <p class="form-label">Спосіб отримання:</p>
                                <select name="delivery_type" id="delivery_type" onchange="window.toggleBeanDelivery(this.value)" required>
                                    <option value="" disabled selected>Оберіть спосіб...</option>
                                    <option value="pickup">Самовивіз з кав'ярні</option>
                                    <option value="nova_poshta">Нова Пошта (по Україні)</option>
                                </select>
                            </div>

                            <div id="pickup_location_wrap" class="u-mt-md" style="display:none;">
                                <p class="form-label">Оберіть кав'ярню:</p>
                                <select name="location">${locOpts}</select>
                            </div>

                            <div id="np_details_wrap" class="np-container u-mt-md" style="display:none;">
                                <p class="form-label">Місто:</p>
                                <div class="search-wrapper">
                                    <input type="text" id="np_city_search" placeholder="Введіть назву міста...">
                                    <div id="np_city_results" class="np-search-results"></div>
                                </div>
                                <input type="hidden" name="np_city_ref" id="np_city_ref">
                                <input type="hidden" name="np_city_name" id="np_city_name">

                                <div id="np_warehouse_search_wrap" class="u-mt-sm u-pt-sm" style="display:none; border-top: 1px solid rgba(0,0,0,0.05);">
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
                                <select name="type" onchange="window.toggleTableInput(this.value)">
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
                    <div class="checkout-footer">
                        <div class="total-row">
                            <span>Всього:</span><span>${total} ₴</span>
                        </div>
                        <button type="button" class="btn-checkout-primary" onclick="window.goToPaymentStep()">Продовжити</button>
                    </div>
                </div>

                <div id="checkout-payment-step" style="display:none;">
                    <p class="payment-title">Оберіть метод оплати:</p>
                    <div class="payment-methods-grid">
                        <button class="payment-btn" onclick="window.submitCheckout('card')">
                            <i class="fas fa-credit-card"></i> <span>Оплата картою</span>
                        </button>
                        <button class="payment-btn" onclick="window.submitCheckout('applepay')">
                            <i class="fab fa-apple-pay"></i> <span>Apple Pay</span>
                        </button>
                        <button class="payment-btn" onclick="window.submitCheckout('googlepay')">
                            <i class="fab fa-google-pay"></i> <span>Google Pay</span>
                        </button>
                        <button class="payment-btn" onclick="window.submitCheckout('privatpay')">
                            <i class="fas fa-university"></i> <span>PrivatPay</span>
                        </button>
                        <button class="payment-btn" onclick="window.submitCheckout('monobank')">
                            <i class="fas fa-wallet"></i> <span>MonoPay</span>
                        </button>
                    </div>
                    <div style="padding: 0 1.5rem 1.5rem;">
                        <button class="btn-back" onclick="window.backToDetails()"><i class="fas fa-arrow-left u-mr-xs"></i> Назад до деталей</button>
                    </div>
                </div>
            </div>`;
        if (isBeans) initNovaPoshtaSearch();

        if (locations.length === 0) {
            container.querySelectorAll('select[name="location"]').forEach((select) => (select.disabled = true));
            const btn = container.querySelector('.btn-checkout-primary');
            if (btn) btn.disabled = true;
            window.showToast?.('Не вдалося завантажити список кавʼярень. Спробуйте оновити сторінку.', 'error');
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
    if (!isBeans && f.elements['type']?.value === 'in_house') {
        const tableNum = f.elements['table_number']?.value.trim();
        if (!tableNum) {
            window.showToast('Будь ласка, вкажіть номер столика', 'error');
            f.elements['table_number'].focus();
            return;
        }
    }
    const orderType = f.elements['type']?.value;
    const paymentMode = f.elements['payment_mode']?.value;
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
                // Очищаємо кошик при успішному репеї (якщо він був ініційований з поточного сеансу)
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
                    window.showToast('Замовлення прийнято! Дякуємо!', 'success');
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
            window.showToast("Помилка відправки. Перевірте з'єднання.", 'error');
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
    <div class="booking-modal__overlay" onclick="window.closeBookingModal()"></div>
    <div class="booking-modal__content checkout-modal-modern">
        <button class="booking-modal__close" onclick="window.closeBookingModal()"><i class="fas fa-times"></i></button>
        <h3 class="checkout-title">Бронювання столика</h3>
        <form id="booking-form" class="booking-form" style="padding: 0 2rem 2rem;">
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
            <button type="submit" class="btn-checkout-primary" style="margin-top: 1rem;">Забронювати</button>
        </form>
    </div>`;
    container.classList.add('booking-modal--active');
    document.body.style.overflow = 'hidden';
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
            window.showToast?.('Не вдалося завантажити список кавʼярень. Спробуйте оновити сторінку.', 'error');
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
                    window.showToast('Бронювання прийнято! Ми зателефонуємо для підтвердження.', 'success');
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
        document.body.style.overflow = '';
    }
};

function showNotification(t) {
    const d = document.createElement('div');
    d.style =
        'position:fixed; bottom:20px; right:20px; background:var(--color-coffee); color:white; padding:12px 24px; border-radius:30px; z-index:10000; box-shadow:0 10px 20px rgba(0,0,0,0.2);';
    d.textContent = t;
    document.body.appendChild(d);
    setTimeout(() => d.remove(), 3000);
}

document.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
    window.setupMobileMenu?.();
    
    // Intersection Observer для анімацій появи
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('u-reveal--active');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.u-reveal, .product-card, .promo-card, .category').forEach(el => {
        if (!el.classList.contains('u-reveal')) el.classList.add('u-reveal');
        revealObserver.observe(el);
    });

    const orderId = window.getURLParameter('order_id');
    if (orderId) {
        window.CURRENT_ORDER_ID = orderId;
        const container = document.getElementById('checkout-modal-container');
        if (container) {
            container.innerHTML = `
                <div class="cart-modal__overlay"></div>
                <div class="cart-modal__content checkout-modal-modern">
                    <div class="loading" style="padding: 3rem; text-align: center;">
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
                        <div class="cart-modal__overlay" onclick="window.closeCheckoutModal()"></div>
                        <div class="cart-modal__content checkout-modal-modern">
                            <button class="cart-modal__close" onclick="window.closeCheckoutModal()"><i class="fas fa-times"></i></button>
                            <h3 class="checkout-title">Оплата замовлення</h3>
                            <div id="checkout-payment-step">
                                <div style="padding: 0 1.5rem 1rem; text-align: center;">
                                    <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">Сума до оплати:</p>
                                    <p style="font-size: 2.2rem; font-weight: 900; color: var(--color-coffee);">${order.total} ₴</p>
                                </div>
                                <p class="payment-title">Оберіть метод оплати:</p>
                                <div class="payment-methods-grid">
                                    <button class="payment-btn" onclick="window.submitCheckout('card')">
                                        <i class="fas fa-credit-card"></i> <span>Оплата картою</span>
                                    </button>
                                    <button class="payment-btn" onclick="window.submitCheckout('applepay')">
                                        <i class="fab fa-apple-pay"></i> <span>Apple Pay</span>
                                    </button>
                                    <button class="payment-btn" onclick="window.submitCheckout('googlepay')">
                                        <i class="fab fa-google-pay"></i> <span>Google Pay</span>
                                    </button>
                                    <button class="payment-btn" onclick="window.submitCheckout('privatpay')">
                                        <i class="fas fa-university"></i> <span>PrivatPay</span>
                                    </button>
                                    <button class="payment-btn" onclick="window.submitCheckout('monobank')">
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
    parent.querySelectorAll('.weight-label').forEach((l) => l.classList.remove('is-active'));
    el.classList.add('is-active');
    const radio = el.querySelector('input');
    if (radio) radio.checked = true;
};

window.toggleChoice = function (el, baseP, type) {
    if (type !== 'addon') {
        const parent = el.parentElement;
        if (parent) {
            parent.querySelectorAll('.choice-chip').forEach((c) => c.classList.remove('is-active'));
        }
        el.classList.add('is-active');
    } else {
        el.classList.toggle('is-active');
    }
    if (window.updatePopupPrice) window.updatePopupPrice(baseP);
};

window.toggleDeliveryMode = function (v) {
    const np = document.getElementById('np_wrap');
    const pick = document.getElementById('pickup_wrap');
    if (np) np.style.display = v === 'nova_poshta' ? 'block' : 'none';
    if (pick) pick.style.display = v === 'pickup' ? 'block' : 'none';
};

window.toggleTableInput = function (v) {
    const tableWrap = document.getElementById('chk_table_wrap');
    const paymentModeSection = document.getElementById('payment-mode-section');
    if (tableWrap) tableWrap.style.display = v === 'in_house' ? 'block' : 'none';
    if (paymentModeSection) paymentModeSection.style.display = v === 'in_house' ? 'block' : 'none';
};
