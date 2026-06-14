const _host = window.location.hostname;
const _port = window.location.port;
const _proto = window.location.protocol;
const isFileProto = _proto === 'file:';
const isLocal = _host === 'localhost' || _host === '127.0.0.1' || _host === '';

window.API_BASE_URL = '';
const reportedClientErrors = new Set();

if (isLocal && _port === '8000') {
    window.API_BASE_URL = 'http://localhost:8000';
}

window.fetchMedelinData = async function (key) {
    console.log(`[Medelin] Fetching ${key}...`);
    const fileName = `${key}.json`;
    const endpoints = [];
    
    if (window.API_BASE_URL) endpoints.push(`${window.API_BASE_URL}/api/${key}`);
    endpoints.push(`/api/${key}`);
    
    const isRoot = !window.location.pathname.includes('/pages/');
    const dataPath = isRoot ? `./assets/data/${fileName}` : `../assets/data/${fileName}`;
    endpoints.push(dataPath);
    endpoints.push(`${window.API_BASE_URL}/assets/data/${fileName}`);
    endpoints.push(`/assets/data/${fileName}`);

    const uniqueEndpoints = [...new Set(endpoints.filter(Boolean))];

    for (const url of uniqueEndpoints) {
        try {
            console.log(`[Medelin] Trying endpoint: ${url}`);
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000); 
            
            const finalUrl = url.includes('?') ? `${url}&t=${Date.now()}` : `${url}?t=${Date.now()}`;
            const response = await fetch(finalUrl, { 
                signal: controller.signal,
                headers: { 'Cache-Control': 'no-cache' }
            });
            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                if (Array.isArray(data)) {
                    console.log(`[Medelin] Successfully loaded ${key} from ${url} (${data.length} items)`);
                    return data;
                }
                console.error(`[Medelin] Endpoint ${url} returned non-array:`, data);
            } else {
                console.warn(`[Medelin] Endpoint ${url} failed with status ${response.status}`);
            }
        } catch (e) {
            console.warn(`[Medelin] Failed to fetch from ${url}:`, e.message);
        }
    }
    console.error(`[Medelin] All endpoints failed for ${key}`);
    window.reportClientError(`Failed to load ${key}`, 'All data endpoints failed');
    return null;
};

window.reportClientError = function (message, context = '') {
    try {
        const signature = `${message}|${context}`.slice(0, 240);
        if (reportedClientErrors.has(signature)) return;
        reportedClientErrors.add(signature);
        fetch(`${window.API_BASE_URL}/api/client-error`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: 'site',
                path: window.location.href,
                message: String(message || 'Client error'),
                context: String(context || '')
            })
        });
    } catch (e) {}
};

window.onerror = function(msg, url, lineNo, columnNo, error) {
    window.reportClientError(msg || (error && error.message) || 'Window error', `${url || ''}:${lineNo || 0}:${columnNo || 0}`);
    if (window.showToast) {
        window.showToast('Сталася помилка. Адміни вже працюють над цим.', 'error');
    }
    return false;
};

window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const message = reason && reason.message ? reason.message : String(reason || 'Unhandled promise rejection');
    window.reportClientError(message, 'unhandledrejection');
});

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

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

window.fixImageUrl = function(url) {
    if (!url || url.startsWith('http') || url.startsWith('data:')) return url;
    
    // If it starts with /uploads/, it's a bot-uploaded image
    // Nginx handles /uploads/ as an absolute path from the domain root
    if (url.startsWith('/uploads/')) {
        return url;
    }
    
    const isRoot = !window.location.pathname.includes('/pages/');
    const prefix = isRoot ? '' : '../';
    
    // If it starts with ../ it's already relative but might need adjustment if we are at root
    if (url.startsWith('../')) {
        return isRoot ? url.substring(3) : url;
    }
    
    return url;
};

function getCurrentOrderKind() {
    return window.location.pathname.includes('beans.html') ? 'beans' : 'menu';
}

function normalizeOrderKind(type, itemsText = '') {
    const t = String(type || '').toLowerCase();
    if (['beans', 'bean', 'coffee', 'pickup', 'nova_poshta', 'beans_delivery'].includes(t)) return 'beans';
    if (['menu', 'takeaway', 'in_house'].includes(t)) return 'menu';
    return /\((250|500|1000)\s*(г|g)\)/i.test(String(itemsText || '')) ? 'beans' : 'menu';
}

function parsePastOrderItems(itemsText) {
    return String(itemsText || '')
        .split(/\r?\n/)
        .map((line, idx) => {
            const cleanLine = line.replace(/^\s*[-•]\s*/, '').trim();
            if (!cleanLine) return null;
            const match = cleanLine.match(/^(.*?)\s*\((\d+)\s*(?:грн|₴|uah)?\)\s*$/i);
            const name = (match ? match[1] : cleanLine).trim();
            const price = match ? parseInt(match[2], 10) : 0;
            return {
                id: `past:${Date.now()}:${idx}:${name}`,
                name,
                price: Number.isFinite(price) ? price : 0
            };
        })
        .filter(Boolean);
}

function getPastOrderItems(order) {
    if (order && Array.isArray(order.items) && order.items.length > 0) return order.items;
    return parsePastOrderItems(order && order.items_text);
}

function getPastOrderSummary(order) {
    const items = getPastOrderItems(order);
    if (items.length > 0) return items.map((item) => item.name).join(', ');
    return String((order && order.items_text) || 'Замовлення').replace(/\s+/g, ' ').trim();
}

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
                    items: parsePastOrderItems(o.items_text),
                    items_text: o.items_text,
                    total: o.total,
                    timestamp: new Date(o.timestamp).getTime(),
                    type: normalizeOrderKind(o.type, o.items_text),
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

function clearCart() {
    cart_menu.length = 0;
    cart_beans.length = 0;
    localStorage.removeItem('cart_menu');
    localStorage.removeItem('cart_beans');
    localStorage.removeItem('medelin_pending_order_id');
    window.CURRENT_ORDER_ID = null;
    updateCartBadge();
}
window.clearCart = clearCart;

function clearPendingPayment() {
    localStorage.removeItem('medelin_pending_order_id');
    window.CURRENT_ORDER_ID = null;
}

function rememberPendingPayment(orderId) {
    if (!orderId) return;
    window.CURRENT_ORDER_ID = String(orderId);
    localStorage.setItem('medelin_pending_order_id', String(orderId));
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
    clearPendingPayment();
    cart_menu.push({ id, name, price });
    saveCart();
    updateCartBadge();
    window.openCartModal();
};

window.addBeanToCart = function (id, name, weightName) {
    clearPendingPayment();
    const r = document.querySelector(`input[name="${weightName}"]:checked`);
    if (!r) {
        alert('Будь ласка, оберіть вагу');
        return;
    }
    const w = r.value;
    const p = parseInt(r.dataset.price);
    const fullName = name;
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

    // Group items by ID and Weight to show Qty
    const grouped = [];
    activeCart.forEach((item) => {
        const key = item.id + (item.weight || '');
        const existing = grouped.find(g => (g.id + (g.weight || '')) === key);
        if (existing) {
            existing.qty++;
        } else {
            grouped.push({ ...item, qty: 1 });
        }
    });

    let html = `
    <div class="cart-modal__overlay" data-action="close-cart-modal"></div>
    <div class="cart-modal__content">
        <button class="cart-modal__close" type="button" data-action="close-cart-modal"><i class="fas fa-times"></i></button>
        <h3 class="cart-modal__title">Кошик</h3>
        <div class="cart-modal__body">
            <ul class="cart-modal__list">`;

    if (grouped.length === 0) {
        html += `<li class="cart-modal__empty">Кошик порожній</li>`;
    } else {
        grouped.forEach((item, index) => {
            // Find stock if specialty
            let maxStock = 999;
            if (isBeans && typeof allCoffeeData !== 'undefined') {
                const bean = allCoffeeData.find(b => (b.id || b._id) === item.id);
                if (bean && bean.stock_packs !== undefined) {
                    const q = (bean.quality_score || '').trim();
                    const isSpec = q && q !== '—' && q !== '-' && q !== '0';
                    if (isSpec) maxStock = parseInt(bean.stock_packs);
                }
            }

            html += `
            <li>
                <div class="cart-item-info">
                    <strong>${item.name}</strong>
                    <div class="cart-modal__item-price">${item.price * item.qty} ₴</div>
                </div>
                <div class="cart-item-end">
                    <div class="cart-qty-stepper">
                        <button class="cart-qty-btn" type="button" onclick="window.updateCartQty('${typeLabel}', '${item.id}', '${item.weight || ''}', -1)" ${item.qty <= 1 ? 'disabled' : ''}><i class="fas fa-minus"></i></button>
                        <span class="cart-qty-val">${item.qty}</span>
                        <button class="cart-qty-btn" type="button" onclick="window.updateCartQty('${typeLabel}', '${item.id}', '${item.weight || ''}', 1)" ${item.qty >= maxStock ? 'disabled' : ''}><i class="fas fa-plus"></i></button>
                    </div>
                    <button class="cart-modal__remove-btn" type="button" onclick="window.removeFromCartById('${typeLabel}', '${item.id}', '${item.weight || ''}')"><i class="fas fa-trash"></i></button>
                </div>
            </li>`;
        });
    }

    const pastOrders = window.getPastOrders();
    const currentOrderKind = getCurrentOrderKind();
    const visiblePastOrders = pastOrders
        .map((order, index) => ({ order, index }))
        .filter(({ order }) => normalizeOrderKind(order && order.type, order && order.items_text) === currentOrderKind);
    const userData = window.getUserData();
    let pastOrdersHtml = '';
    if (visiblePastOrders.length > 0 || (userData && userData.phone)) {
        pastOrdersHtml += `<div class="cart-modal__past-orders">
            <div class="cart-modal__past-orders-head">
                <h4 class="cart-modal__past-orders-title" style="margin: 0;">Минулі замовлення</h4>
            </div>
            <div class="cart-modal__past-orders-list">`;

        if (visiblePastOrders.length > 0) {
            visiblePastOrders.slice(0, 4).forEach(({ order, index }) => {
                const date = new Date(order.timestamp).toLocaleDateString('uk-UA');
                const summary = getPastOrderSummary(order);
                pastOrdersHtml += `<button class="past-order" type="button" data-action="repeat-order" data-order-index="${index}">
                    <div class="past-order__meta">
                        <strong class="past-order__summary">${escapeHtml(summary)}</strong>
                        <div class="past-order__date">${date} — ${order.total} ₴</div>
                    </div>
                    <span class="past-order__add-icon"><i class="fas fa-plus"></i></span>
                </button>`;
            });
        } else {
            pastOrdersHtml += `<div class="cart-modal__empty" style="padding: 10px 0;">Попередніх замовлень цього типу ще немає</div>`;
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

window.updateCartQty = function(type, id, weight, delta) {
    const cart = type === 'beans' ? cart_beans : cart_menu;
    if (delta > 0) {
        // Add one
        const item = cart.find(i => i.id === id && (i.weight || '') === weight);
        if (item) {
            cart.push({ ...item });
        }
    } else {
        // Remove one
        const idx = cart.findLastIndex(i => i.id === id && (i.weight || '') === weight);
        if (idx !== -1) {
            cart.splice(idx, 1);
        }
    }
    if (type === 'beans') cart_beans = cart; else cart_menu = cart;
    saveCart();
    updateCartBadge();
    window.openCartModal();
};

window.removeFromCartById = function(type, id, weight) {
    if (type === 'beans') {
        cart_beans = cart_beans.filter(i => !(i.id === id && (i.weight || '') === weight));
    } else {
        cart_menu = cart_menu.filter(i => !(i.id === id && (i.weight || '') === weight));
    }
    saveCart();
    updateCartBadge();
    window.openCartModal();
};

window.repeatOrder = function (idx) {
    const pastOrders = window.getPastOrders();
    const order = pastOrders[idx];
    if (!order) return;
    const items = getPastOrderItems(order);
    if (!items.length) {
        window.showToast('Не вдалося відновити склад замовлення', 'error');
        return;
    }

    const isBeans = normalizeOrderKind(order.type, order.items_text) === 'beans';
    
    // Group items from past order to check stock
    const groupedPast = {};
    items.forEach(item => {
        const key = item.id + (item.weight || '');
        if (!groupedPast[key]) groupedPast[key] = { ...item, count: 0 };
        groupedPast[key].count++;
    });

    // Check against available stock
    if (isBeans && typeof allCoffeeData !== 'undefined') {
        for (const key in groupedPast) {
            const item = groupedPast[key];
            const bean = allCoffeeData.find(b => (b.id || b._id) === item.id);
            if (bean && bean.stock_packs !== undefined) {
                const q = (bean.quality_score || '').trim();
                const isSpec = q && q !== '—' && q !== '-' && q !== '0';
                if (isSpec) {
                    const available = parseInt(bean.stock_packs);
                    if (item.count > available) {
                        alert(`Вибачте, ${bean.name} залишилося лише ${available} пачок. Ваше минуле замовлення містило ${item.count}.`);
                        return;
                    }
                }
            }
        }
    }

    clearPendingPayment();
    if (isBeans) {
        cart_beans = [...cart_beans, ...items];
    } else {
        cart_menu = [...cart_menu, ...items];
    }
    saveCart();
    updateCartBadge();
    window.openCartModal();
    window.showToast('Замовлення додано до кошика', 'success');
};

document.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    const action = target.dataset.action;

    if (action === 'repeat-order') {
        const idx = target.dataset.orderIndex;
        if (idx !== undefined) window.repeatOrder(parseInt(idx));
    }
    if (action === 'close-cart-modal') window.closeCartModal();
    if (action === 'close-checkout-modal') window.closeCheckoutModal();
    if (action === 'go-to-payment-step') window.goToPaymentStep();
    if (action === 'back-to-details') window.backToDetails();
    if (action === 'submit-checkout') {
        const method = target.dataset.method;
        window.submitCheckout(method);
    }
    if (action === 'open-checkout-modal') window.openCheckoutModal();
});

window.closeCartModal = function () {
    const c = document.getElementById('cart-modal-container');
    if (c) c.classList.remove('cart-modal--active');
    document.body.classList.remove('body--scroll-locked');
};

window.removeFromCart = function (t, i) {
    clearPendingPayment();
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
                        ${isBeans ? `
                        <div class="form-group">
                            <label class="form-label">Телефон</label>
                            <input type="tel" name="phone" placeholder="Телефон (+380...)" value="${userData.phone || ''}" required>
                        </div>
                        ` : ''}
                        <div class="form-group">
                            <label class="form-label">Побажання чи уточнення — опційно</label>
                            <textarea name="comment" placeholder="Ваші побажання до замовлення..." rows="2"></textarea>
                        </div>

                        ${
                            isBeans
                                ? `
                            <div id="np_details_wrap" class="np-container" style="display:block; margin-top: 1.5rem;">
                                <p class="form-label">Місто:</p>
                                <div class="search-wrapper">
                                    <input type="text" id="np_city_search" placeholder="Введіть назву міста...">
                                    <div id="np_city_results" class="np-search-results"></div>
                                </div>
                                <input type="hidden" name="np_city_ref" id="np_city_ref">
                                <input type="hidden" name="np_city_name" id="np_city_name">
                                <input type="hidden" name="delivery_type" value="nova_poshta">

                                <div class="form-group" style="margin-top: 1rem;">
                                    <label class="form-label">Тип доставки Нової Пошти:</label>
                                    <div class="choice-grid" style="grid-template-columns: 1fr 1fr;">
                                        <label class="choice-chip choice-chip--active" id="np_type_branch_label">
                                            <input type="radio" name="np_delivery_mode" value="branch" checked style="display:none;" onchange="window.toggleNpMode('branch')">
                                            <span class="choice-chip__label">Відділення</span>
                                        </label>
                                        <label class="choice-chip" id="np_type_courier_label">
                                            <input type="radio" name="np_delivery_mode" value="courier" style="display:none;" onchange="window.toggleNpMode('courier')">
                                            <span class="choice-chip__label">Кур'єр</span>
                                        </label>
                                    </div>
                                </div>

                                <div id="np_branch_fields" style="display:block; margin-top: 1rem;">
                                    <div id="np_warehouse_search_wrap" class="np-warehouse-search" style="display:none; padding-top: 1rem; border-top: 1px solid rgba(0,0,0,0.05);">
                                        <p class="form-label">Відділення або поштомат (№ або вул):</p>
                                        <div class="search-wrapper">
                                            <input type="text" id="np_wh_input" placeholder="Наприклад: 1 або Головна">
                                            <div id="np_wh_results" class="np-search-results"></div>
                                        </div>
                                        <input type="hidden" name="np_warehouse" id="np_warehouse_final">
                                        <div id="np_selected_wh_display" class="np-selected-display"></div>
                                    </div>
                                </div>

                                <div id="np_courier_fields" style="display:none; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(0,0,0,0.05);">
                                    <div class="form-group">
                                        <label class="form-label">Вулиця:</label>
                                        <div class="search-wrapper">
                                            <input type="text" id="np_street_search" placeholder="Почніть вводити назву вулиці...">
                                            <div id="np_street_results" class="np-search-results"></div>
                                        </div>
                                        <input type="hidden" name="np_street_name" id="np_street_name">
                                    </div>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                                        <div class="form-group">
                                            <label class="form-label">Будинок:</label>
                                            <input type="text" name="np_house" placeholder="12А">
                                        </div>
                                        <div class="form-group">
                                            <label class="form-label">Кв./Офіс:</label>
                                            <input type="text" name="np_flat" placeholder="45">
                                        </div>
                                    </div>
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
                            <i class="fas fa-credit-card"></i> <span>Картка</span>
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
                        <button class="payment-btn" type="button" data-action="submit-checkout" data-method="cash">
                            <i class="fas fa-truck-ramp-box"></i> <span>Накладний платіж</span>
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

window.toggleNpMode = function(mode) {
    const branchFields = document.getElementById('np_branch_fields');
    const courierFields = document.getElementById('np_courier_fields');
    const branchLabel = document.getElementById('np_type_branch_label');
    const courierLabel = document.getElementById('np_type_courier_label');
    
    if (mode === 'courier') {
        if (branchFields) branchFields.style.display = 'none';
        if (courierFields) courierFields.style.display = 'block';
        if (branchLabel) branchLabel.classList.remove('choice-chip--active');
        if (courierLabel) courierLabel.classList.add('choice-chip--active');
    } else {
        if (branchFields) branchFields.style.display = 'block';
        if (courierFields) courierFields.style.display = 'none';
        if (branchLabel) branchLabel.classList.add('choice-chip--active');
        if (courierLabel) courierLabel.classList.remove('choice-chip--active');
    }
};

function initNovaPoshtaSearch() {
    const inp = document.getElementById('np_city_search');
    const res = document.getElementById('np_city_results');
    const branchWrap = document.getElementById('np_warehouse_search_wrap');
    const courierWrap = document.getElementById('np_courier_fields');
    if (!inp) return;

    const searchStreets = debounce((val) => {
        const ref = document.getElementById('np_city_ref').value;
        const streetRes = document.getElementById('np_street_results');
        if (!ref || !streetRes) return;
        if (val.length < 2) {
            streetRes.style.display = 'none';
            return;
        }
        streetRes.innerHTML = '<div class="np-result-item" style="opacity:0.5;">Шукаємо...</div>';
        streetRes.style.display = 'block';
        fetch(`${window.API_BASE_URL}/api/nova-poshta/streets?cityRef=${ref}&search=${encodeURIComponent(val)}`)
            .then((r) => r.json())
            .then((data) => {
                streetRes.innerHTML = '';
                const streets = Array.isArray(data) ? data : [];
                if (streets.length === 0) {
                    streetRes.innerHTML = '<div class="np-result-item">Нічого не знайдено</div>';
                } else {
                        streets.forEach((s) => {
                            const item = document.createElement('div');
                            item.className = 'np-result-item';
                            
                            const cleanText = (text) => {
                                if (!text) return '';
                                // Remove UUIDs: 8-4-4-4-12 hex chars
                                let cleaned = text.replace(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/gi, '');
                                // Remove any words that look like hex IDs or are too long/weird
                                cleaned = cleaned.split(/[\s,]+/).filter(word => {
                                    const isId = /[a-f0-9]{8,}/i.test(word) || word.length > 20 || /^[a-f0-9-]{15,}$/i.test(word);
                                    return !isId;
                                }).join(' ').trim();
                                return cleaned.replace(/^[\s,]+|[\s,]+$/g, '');
                            };

                            let desc = cleanText(s.Description || s.SettlementStreetDescription || '');
                            const type = cleanText(s.StreetsType || s.SettlementStreetDescriptionTyp || '');
                            
                            const full = type ? `${type} ${desc}` : desc;
                            item.textContent = full;
                            item.onclick = () => {
                                document.getElementById('np_street_search').value = full;
                                document.getElementById('np_street_name').value = full;
                                streetRes.style.display = 'none';
                            };
                            streetRes.appendChild(item);
                        });
                }
            });
    }, 400);

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
                const whs = Array.isArray(data) ? data : [];
                if (whs.length === 0) {
                    if (!val) {
                        whRes.innerHTML = '<div class="np-result-item" style="opacity:0.6;">Введіть номер або назву...</div>';
                    } else {
                        whRes.innerHTML = '<div class="np-result-item">Нічого не знайдено</div>';
                    }
                } else {
                    whs.forEach((w) => {
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
    }, 500);

    const searchCities = debounce((val) => {
        if (val.length < 2) {
            res.style.display = 'none';
            return;
        }
        res.innerHTML = '<div class="np-result-item" style="opacity:0.5;">Шукаємо...</div>';
        res.style.display = 'block';
        fetch(`${window.API_BASE_URL}/api/nova-poshta/cities?search=${encodeURIComponent(val)}`)
            .then((r) => r.json())
            .then((data) => {
                res.innerHTML = '';
                const cities = Array.isArray(data) ? data : [];
                if (cities.length === 0) {
                    res.innerHTML = '<div class="np-result-item">Не знайдено</div>';
                } else {
                    cities.forEach((c) => {
                        const item = document.createElement('div');
                        item.className = 'np-result-item';
                        // searchSettlements returns Present (m. Kyiv, Kyivska obl)
                        const cityName = c.Present || c.Description;
                        const area = c.AreaDescription || '';
                        const region = c.RegionsDescription || '';
                        
                        item.innerHTML = `<div style="font-weight:700;">${cityName}</div>${area ? `<div style="font-size:0.75rem; opacity:0.7;">${area} обл., ${region}</div>` : ''}`;
                        
                        item.onclick = () => {
                            inp.value = cityName;
                            // For searchSettlements, 'Ref' is the SettlementRef (used for streets)
                            // 'CityRef' is the CityRef (used for warehouses)
                            document.getElementById('np_city_ref').value = c.Ref || c.CityRef;
                            document.getElementById('np_city_name').value = cityName;
                            res.style.display = 'none';
                            if (branchWrap) branchWrap.style.display = 'block';
                            document.getElementById('np_wh_input').value = '';
                            if (typeof searchWh === 'function') searchWh('');
                        };
                        res.appendChild(item);
                    });
                }
            });
    }, 400);

    inp.oninput = (e) => searchCities(e.target.value.trim());
    const whInp = document.getElementById('np_wh_input');
    if (whInp) whInp.oninput = (e) => searchWh(e.target.value.trim());
    const stInp = document.getElementById('np_street_search');
    if (stInp) stInp.oninput = (e) => searchStreets(e.target.value.trim());
}

window.goToPaymentStep = function () {
    const f = document.getElementById('checkout-details-form');
    if (!f || !f.reportValidity()) return;
    const isBeans = window.location.pathname.includes('beans.html');
    if (isBeans && f.elements['delivery_type'].value === 'nova_poshta') {
        const mode = f.elements['np_delivery_mode'] ? f.elements['np_delivery_mode'].value : 'branch';
        if (mode === 'branch' && !document.getElementById('np_warehouse_final').value) {
            window.showToast('Будь ласка, оберіть відділення Нової Пошти', 'error');
            return;
        }
        if (mode === 'courier' && !document.getElementById('np_street_name').value) {
            window.showToast('Будь ласка, оберіть вулицю для доставки', 'error');
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
    });
    const data = {
        user_details: {
            name: fd.get('name'),
            phone: fd.get('phone'),
            comment: fd.get('comment'),
            location: fd.get('location'),
            type: fd.get('type'),
            table_number: fd.get('table_number'),
            payment_mode: method === 'cash' ? 'pay_at_checkout' : 'pay_now',
            delivery_type: fd.get('delivery_type'),
            np_city_ref: fd.get('np_city_ref'),
            np_city_name: fd.get('np_city_name'),
            np_warehouse: fd.get('np_warehouse'),
            np_delivery_mode: fd.get('np_delivery_mode'),
            np_street_name: fd.get('np_street_name'),
            np_house: fd.get('np_house'),
            np_flat: fd.get('np_flat'),
        },
        cart_menu: activeCart,
        payment_method: method,
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
                    id: res.order_id,
                    items: [...activeCart],
                    total: activeCart.reduce((s, i) => s + i.price, 0),
                    type: isBeans ? 'beans' : 'menu',
                });
                if (res.url) {
                    window.location.href = res.url;
                }
                else if (res.data && res.signature) {
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'https://www.liqpay.ua/api/3/checkout';
                    form.innerHTML = `<input type="hidden" name="data" value="${res.data}"><input type="hidden" name="signature" value="${res.signature}">`;
                    document.body.appendChild(form);
                    form.submit();
                } else {
                    window.showToast('Замовлення прийнято!', 'success');
                    clearCart();
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

document.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
    if (window.setupMobileMenu) window.setupMobileMenu();
    if (typeof window.syncPastOrders === 'function') window.syncPastOrders();

    document.body.classList.add('js-enabled');

    const paymentStatus = window.getURLParameter('payment');
    if (paymentStatus === 'success') {
        if (typeof clearCart === 'function') clearCart();
        window.showToast('Оплату успішно проведено! Дякуємо за замовлення.', 'success');
        const url = new URL(window.location);
        url.searchParams.delete('payment');
        url.searchParams.delete('order_id');
        window.history.replaceState({}, document.title, url.pathname + url.search);
    }
    
    const initRevealAnimations = () => {
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealable--active');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.05, rootMargin: '0px 0px -50px 0px' });

        const revealElements = document.querySelectorAll('.revealable, .product-card, .promo-card, .category, .menu-item');
        revealElements.forEach(el => {
            if (!el.classList.contains('revealable')) el.classList.add('revealable');
            revealObserver.observe(el);
        });

        setTimeout(() => {
            revealElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.top < window.innerHeight && rect.bottom > 0) {
                    el.classList.add('revealable--active');
                }
            });
        }, 500);
    };

    initRevealAnimations();
    window.refreshAnimations = () => { initRevealAnimations(); };

    const orderId = window.getURLParameter('order_id');
    if (orderId && paymentStatus !== 'success') {
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
                .then(r => r.ok ? r.json() : { detail: 'Помилка' })
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

// Order status polling and notifications
(function initOrderStatusPolling() {
    const pollStatuses = async () => {
        const pastOrders = window.getPastOrders();
        if (!pastOrders || pastOrders.length === 0) return;
        
        // Poll only latest 3 orders
        const latest = pastOrders.slice(0, 3);
        const knownStatuses = JSON.parse(localStorage.getItem('medelin_order_statuses') || '{}');
        let changed = false;

        for (const order of latest) {
            if (!order.id) continue;
            // Don't poll if it's already completed or rejected long ago
            if (knownStatuses[order.id] === 'confirmed' || knownStatuses[order.id] === 'rejected') continue;

            try {
                const resp = await fetch(`${window.API_BASE_URL}/api/orders/${order.id}`);
                if (resp.ok) {
                    const data = await resp.json();
                    if (data.status && data.status !== knownStatuses[order.id]) {
                        knownStatuses[order.id] = data.status;
                        changed = true;
                        if (data.status === 'confirmed') {
                            const summary = getPastOrderSummary(order);
                            window.showToast(`Ваше замовлення підтверджено! (${summary})`, 'success');
                        } else if (data.status === 'rejected') {
                            window.showToast(`Замовлення відхилено.`, 'error');
                        }
                    }
                }
            } catch (e) {}
        }

        if (changed) {
            localStorage.setItem('medelin_order_statuses', JSON.stringify(knownStatuses));
        }
    };

    setInterval(pollStatuses, 15000); // Poll every 15s
    setTimeout(pollStatuses, 2000); // Initial poll
})();
