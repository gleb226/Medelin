let map;
let markers = [];

async function initLocations() {
    const gridRoot = document.getElementById('locations-grid');
    const popupsRoot = document.getElementById('popups-container');
    if (!gridRoot) return;

    gridRoot.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Завантаження локацій...</div>';

    if (document.getElementById('map') && !map) {
        try {
            map = L.map('map').setView([48.6217, 22.2875], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            }).addTo(map);
        } catch (e) {}
    }

    const cached = typeof window.getCachedData === 'function' ? window.getCachedData('locations') : null;
    if (cached) {
        renderLocations(cached);
    }

    try {
        const data = await window.fetchMedelinData('locations');
        if (data) {
            window.setCachedData('locations', data);
            renderLocations(data);
        } else if (!cached) {
            gridRoot.innerHTML = '<div class="error-msg">Не вдалося завантажити список локацій. <br><button onclick="location.reload()" class="btn btn--sm u-mt-md">Оновити сторінку</button></div>';
        }
    } catch (err) {
        console.error('initLocations error:', err);
        if (!cached) gridRoot.innerHTML = '<div class="error-msg">Критична помилка завантаження локацій.</div>';
    }
}

function renderLocations(locations) {
    const gridRoot = document.getElementById('locations-grid');
    const popupsRoot = document.getElementById('popups-container');
    if (!gridRoot || !popupsRoot) return;

    gridRoot.innerHTML = '';
    popupsRoot.innerHTML = '';

    locations.forEach((loc, index) => {
        const locId = `loc-${index}`;
        const article = document.createElement('article');
        article.className = 'product-card';
        article.onclick = () => window.openPopup(locId);

        article.innerHTML = `
            <div class="product-card__image" style="background-image: url('${loc.image_url}')"></div>
            <div class="product-card__content">
                <h3 class="product-card__title">${loc.name}</h3>
                <p style="font-size: 0.9rem; color: var(--color-muted);">${loc.address}</p>
            </div>
        `;
        gridRoot.appendChild(article);

        const popup = document.createElement('div');
        popup.className = 'popup';
        popup.id = locId;
        popup.innerHTML = `
            <div class="popup__overlay" onclick="window.closePopup('${locId}')"></div>
            <div class="popup__content">
                <button class="popup__close" onclick="window.closePopup('${locId}')"><i class="fas fa-times"></i></button>
                <img src="${loc.image_url}" class="popup__image">
                <div class="popup__body-inner">
                    <h3 class="popup__title u-mb-md">${loc.name}</h3>
                    <p class="popup__description">${loc.atmosphere || ''}</p>
                    <div class="popup__info-list">
                        <div class="popup__info-item">
                            <i class="fas fa-map-marker-alt popup__info-icon"></i>
                            <div><strong class="popup__info-label">Адреса</strong><span class="popup__info-value">${loc.address}</span></div>
                        </div>
                        <div class="popup__info-item">
                            <i class="fas fa-clock popup__info-icon"></i>
                            <div><strong class="popup__info-label">Графік</strong><span class="popup__info-value">${loc.schedule}</span></div>
                        </div>
                        <div class="popup__info-item">
                            <i class="fas fa-phone-alt popup__info-icon"></i>
                            <div><strong class="popup__info-label">Телефон</strong><span class="popup__info-value">${loc.phone}</span></div>
                        </div>
                    </div>
                    <div class="amenities-tags">
                        ${(loc.amenities || []).map((a) => `<span class="tag">${a}</span>`).join('')}
                    </div>
                    <a href="${loc.google_maps_url}" target="_blank" class="btn btn--full-width"><i class="fas fa-route" style="margin-right:8px;"></i> Прокласти маршрут</a>
                </div>
            </div>
        `;
        popupsRoot.appendChild(popup);

        if (loc.coordinates && map) {
            addMarkerToMap(loc, locId);
        }
    });
}

const SOCIAL_ICONS = {
    instagram: 'fab fa-instagram',
    facebook: 'fab fa-facebook-f',
    email: 'fas fa-envelope',
    phone: 'fas fa-phone-alt',
    github: 'fab fa-github',
    tiktok: 'fab fa-tiktok',
    telegram: 'fab fa-telegram',
    viber: 'fab fa-viber',
    youtube: 'fab fa-youtube',
};

function guessSocialKeyFromUrl(url) {
    const u = String(url || '').toLowerCase();
    if (u.includes('instagram.')) return 'instagram';
    if (u.includes('tiktok.')) return 'tiktok';
    if (u.includes('facebook.') || u.includes('fb.')) return 'facebook';
    if (u.includes('youtube.') || u.includes('youtu.be')) return 'youtube';
    if (u.includes('telegram.') || u.includes('t.me/')) return 'telegram';
    if (u.includes('viber.')) return 'viber';
    if (u.includes('github.')) return 'github';
    return null;
}

async function initSocials() {
    const socialsRoot = document.getElementById('socials-list');
    const footerSocials = document.getElementById('footer-socials');
    if (!socialsRoot && !footerSocials) return;

    try {
        const socials = await window.fetchMedelinData('socials');
        if (!socials) return;

        if (socialsRoot) {
            socialsRoot.innerHTML = '<div class="contact-social-icons"></div>';
            const container = socialsRoot.querySelector('.contact-social-icons');
            socials.forEach((soc) => {
                const nameKey = soc.name.toLowerCase().trim();
                const byUrl = guessSocialKeyFromUrl(soc.url);
                let iconClass = SOCIAL_ICONS[nameKey] || (byUrl ? SOCIAL_ICONS[byUrl] : null) || 'fas fa-link';
                const a = document.createElement('a');
                a.href = soc.url;
                a.className = 'social-icon';
                a.target = '_blank';
                a.title = soc.name;
                a.innerHTML = `<i class="${iconClass}"></i><span style="font-size:0.7rem; font-weight:700; text-transform:uppercase;">${soc.name}</span>`;
                container.appendChild(a);
            });
        }

        if (footerSocials) {
            footerSocials.innerHTML = '';
            socials.forEach((soc) => {
                const a = document.createElement('a');
                a.href = soc.url;
                a.target = '_blank';
                a.className = 'footer__link';
                const nameKey = soc.name.toLowerCase().trim();
                const byUrl = guessSocialKeyFromUrl(soc.url);
                const iconClass = SOCIAL_ICONS[nameKey] || (byUrl ? SOCIAL_ICONS[byUrl] : null) || 'fas fa-link';
                a.innerHTML = `<i class="${iconClass}" style="margin-right:5px;"></i>${soc.name}`;
                a.style.marginRight = '15px';
                footerSocials.appendChild(a);
            });
        }
    } catch (err) {
        console.error('initSocials error:', err);
    }
}

function addMarkerToMap(loc, locId) {
    if (!map) return;
    const coffeeIcon = L.divIcon({
        className: 'custom-map-pin',
        html: `<div class="pin-droplet"><span class="pin-icon"><i class="fas fa-coffee"></i></span></div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 40],
        popupAnchor: [0, -40],
    });

    const popupHtml = `
        <div class="map-popup">
            <div class="map-popup__header" style="background-image: url('${loc.image_url}');"></div>
            <div class="map-popup__body">
                <h4 class="map-popup__title">${loc.name}</h4>
                <p class="map-popup__address"><span><i class="fas fa-map-marker-alt" style="margin-right:5px;"></i></span> ${loc.address}</p>
                <div class="map-popup__footer">
                    <a href="${loc.google_maps_url}" target="_blank" class="btn-map-route">Маршрут</a>
                </div>
            </div>
        </div>
    `;

    const marker = L.marker([loc.coordinates.lat, loc.coordinates.lon], { icon: coffeeIcon }).addTo(map);
    marker.bindPopup(popupHtml, {
        className: 'modern-popup',
        maxWidth: 280,
    });
}

function startContactPage() {
    initLocations();
    initSocials();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startContactPage);
} else {
    startContactPage();
}
