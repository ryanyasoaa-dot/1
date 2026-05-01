/**
 * shop.js — Buyer shop page logic
 * Depends on: api.js
 * Pages: market, product, cart, checkout,
 *        order_summary, orders, wishlist,
 *        address_book, settings
 */

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, isError = false) {
    const t = document.getElementById('shopToast');
    if (!t) return;
    t.textContent = msg;
    t.style.background = isError ? '#c0392b' : '#1a1a3e';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// ── Cart badge ────────────────────────────────────────────────
function updateCartBadge() {
    const cart  = getCart();
    const total = cart.reduce((sum, i) => sum + i.qty, 0);
    document.querySelectorAll('.cart-count').forEach(el => {
        el.textContent = total;
        el.style.display = total > 0 ? 'flex' : 'none';
    });
}

// ── Local cart (until API is ready) ──────────────────────────
function getCart() {
    return JSON.parse(localStorage.getItem('luxe_cart') || '[]');
}

function saveCart(cart) {
    localStorage.setItem('luxe_cart', JSON.stringify(cart));
    updateCartBadge();
}

function addToCart(product) {
    const cart = getCart();
    const idx  = cart.findIndex(i => i.id === product.id);
    if (idx > -1) cart[idx].qty += 1;
    else cart.push({ ...product, qty: 1 });
    saveCart(cart);
    showToast(`✅ ${product.name} added to cart!`);
}

function removeFromCart(productId) {
    saveCart(getCart().filter(i => i.id !== productId));
}

function updateQty(productId, qty) {
    const cart = getCart();
    const idx  = cart.findIndex(i => i.id === productId);
    if (idx > -1) {
        if (qty <= 0) cart.splice(idx, 1);
        else cart[idx].qty = qty;
    }
    saveCart(cart);
}

// ── Local wishlist ────────────────────────────────────────────
function getWishlist() {
    return JSON.parse(localStorage.getItem('luxe_wishlist') || '[]');
}

function toggleWishlist(product) {
    const list = getWishlist();
    const idx  = list.findIndex(i => i.id === product.id);
    if (idx > -1) {
        list.splice(idx, 1);
        showToast('Removed from wishlist.');
    } else {
        list.push(product);
        showToast('❤️ Added to wishlist!');
    }
    localStorage.setItem('luxe_wishlist', JSON.stringify(list));
    return idx === -1;
}

function isWishlisted(productId) {
    return getWishlist().some(i => i.id === productId);
}

// ── Format helpers ────────────────────────────────────────────
function formatCurrency(amount) {
    return '₱' + Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
}

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-PH', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

function renderStars(rating) {
    const full  = Math.floor(rating);
    const empty = 5 - full;
    return '★'.repeat(full) + '☆'.repeat(empty);
}

// ── Market page ───────────────────────────────────────────────
async function loadMarket(params = {}) {
    const grid = document.getElementById('productGrid');
    if (!grid) return;

    grid.innerHTML = `<div class="col-12 text-center py-5"><div class="spinner-border" style="color:var(--pink)"></div></div>`;

    const query = new URLSearchParams(params).toString();
    const data  = await API.shop.getProducts(query).catch(() => []);

    if (!data.length) {
        grid.innerHTML = `
            <div class="col-12">
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <h5>No products found</h5>
                    <p>Try adjusting your filters or search term.</p>
                </div>
            </div>`;
        return;
    }

    grid.innerHTML = data.map(p => renderProductCard(p)).join('');
}

function renderProductCard(p) {
    const wishlisted = isWishlisted(p.id);
    return `
    <div class="col-6 col-md-4 col-lg-3 mb-3">
        <div class="product-card" onclick="window.location='/buyer/product?id=${p.id}'">
            <div class="product-img">
                ${p.image ? `<img src="${p.image}" alt="${p.name}">` : p.emoji || '🛍️'}
                ${p.discount ? `<span class="product-badge">-${p.discount}%</span>` : ''}
                <button class="product-wishlist ${wishlisted ? 'active' : ''}"
                    onclick="event.stopPropagation(); handleWishlist(this, ${JSON.stringify(p).replace(/"/g,'&quot;')})"
                >❤️</button>
            </div>
            <div class="product-body">
                <div class="product-name">${p.name}</div>
                <div>
                    <span class="product-price">${formatCurrency(p.price)}</span>
                    ${p.original_price ? `<span class="product-original">${formatCurrency(p.original_price)}</span>` : ''}
                </div>
                <div class="product-rating">
                    <span class="stars">${renderStars(p.rating || 0)}</span>
                    <span>(${p.reviews || 0})</span>
                </div>
                <button class="btn-add-cart" onclick="event.stopPropagation(); addToCart({id:'${p.id}',name:'${p.name}',price:${p.price},emoji:'${p.emoji||'🛍️'}',image:'${p.image||''}'})">
                    Add to Cart
                </button>
            </div>
        </div>
    </div>`;
}

function handleWishlist(btn, product) {
    const added = toggleWishlist(product);
    btn.classList.toggle('active', added);
}

// ── Product detail page ───────────────────────────────────────
async function loadProduct() {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) return;

    const p = await API.shop.getProduct(id).catch(() => null);
    if (!p) return;

    const set = (elId, val) => { const el = document.getElementById(elId); if (el) el.innerHTML = val; };
    set('productEmoji',    p.emoji || '🛍️');
    set('productName',     p.name);
    set('productPrice',    formatCurrency(p.price));
    set('productOriginal', p.original_price ? formatCurrency(p.original_price) : '');
    set('productDesc',     p.description || 'No description available.');
    set('productRating',   `<span class="stars">${renderStars(p.rating || 0)}</span> (${p.reviews || 0} reviews)`);
    set('productStock',    p.stock > 0 ? `<span style="color:#10b981">In Stock (${p.stock})</span>` : `<span style="color:#ef4444">Out of Stock</span>`);

    const addBtn = document.getElementById('addToCartBtn');
    if (addBtn) addBtn.onclick = () => addToCart({ id: p.id, name: p.name, price: p.price, emoji: p.emoji, image: p.image });
}

// ── Cart page ─────────────────────────────────────────────────
function loadCart() {
    const container = document.getElementById('cartItems');
    const emptyEl   = document.getElementById('cartEmpty');
    const summaryEl = document.getElementById('cartSummary');
    if (!container) return;

    const cart = getCart();

    if (!cart.length) {
        container.innerHTML = '';
        if (emptyEl)   emptyEl.style.display   = 'block';
        if (summaryEl) summaryEl.style.display  = 'none';
        return;
    }

    if (emptyEl)   emptyEl.style.display   = 'none';
    if (summaryEl) summaryEl.style.display  = 'block';

    container.innerHTML = cart.map(item => `
        <div class="cart-item">
            <div class="cart-item-img">${item.image ? `<img src="${item.image}">` : item.emoji || '🛍️'}</div>
            <div class="flex-grow-1">
                <div style="font-size:14px;font-weight:600;margin-bottom:4px">${item.name}</div>
                <div style="font-size:15px;font-weight:700;color:var(--pink);margin-bottom:8px">${formatCurrency(item.price)}</div>
                <div class="qty-control">
                    <button class="qty-btn" onclick="changeQty('${item.id}', ${item.qty - 1})">−</button>
                    <span class="qty-value">${item.qty}</span>
                    <button class="qty-btn" onclick="changeQty('${item.id}', ${item.qty + 1})">+</button>
                </div>
            </div>
            <div style="text-align:right">
                <div style="font-size:15px;font-weight:700;margin-bottom:8px">${formatCurrency(item.price * item.qty)}</div>
                <button class="btn btn-sm btn-outline-danger" onclick="removeFromCart('${item.id}'); loadCart()">🗑️</button>
            </div>
        </div>
    `).join('');

    updateCartSummary(cart);
}

function changeQty(id, qty) {
    updateQty(id, qty);
    loadCart();
}

function updateCartSummary(cart) {
    const subtotal  = cart.reduce((s, i) => s + i.price * i.qty, 0);
    const shipping  = subtotal > 500 ? 0 : 50;
    const total     = subtotal + shipping;
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('subtotalAmt',  formatCurrency(subtotal));
    set('shippingAmt',  shipping === 0 ? 'FREE' : formatCurrency(shipping));
    set('totalAmt',     formatCurrency(total));
}

// ── Checkout page ─────────────────────────────────────────────
function loadCheckout() {
    const cart = getCart();
    if (!cart.length) { window.location.href = '/buyer/cart'; return; }

    const list = document.getElementById('checkoutItems');
    if (list) {
        list.innerHTML = cart.map(i => `
            <div class="d-flex justify-content-between align-items-center mb-2" style="font-size:13px">
                <span>${i.emoji || '🛍️'} ${i.name} × ${i.qty}</span>
                <span style="font-weight:600">${formatCurrency(i.price * i.qty)}</span>
            </div>
        `).join('');
    }

    updateCartSummary(cart);
    loadAddressOptions();
}

async function loadAddressOptions() {
    const container = document.getElementById('addressOptions');
    if (!container) return;

    const data = await API.buyer.getAddresses().catch(() => []);
    if (!data.length) {
        container.innerHTML = `<p style="font-size:13px;color:var(--gray)">No saved addresses. <a href="/buyer/address_book" style="color:var(--pink)">Add one</a></p>`;
        return;
    }

    container.innerHTML = data.map((a, i) => `
        <div class="address-card ${i === 0 ? 'selected' : ''} mb-2" onclick="selectAddress(this, '${a.id}')">
            ${a.is_default ? '<span class="default-badge">Default</span>' : ''}
            <div style="font-size:13px;font-weight:600">${a.label || 'Home'}</div>
            <div style="font-size:12px;color:var(--gray)">${[a.street, a.barangay, a.city, a.region].filter(Boolean).join(', ')}</div>
        </div>
    `).join('');
}

function selectAddress(el, id) {
    document.querySelectorAll('.address-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('selectedAddressId').value = id;
}

async function placeOrder() {
    const cart      = getCart();
    const addressId = document.getElementById('selectedAddressId')?.value;
    const payment   = document.querySelector('input[name="payment"]:checked')?.value;

    if (!addressId) { showToast('Please select a delivery address.', true); return; }
    if (!payment)   { showToast('Please select a payment method.', true); return; }

    const btn = document.getElementById('placeOrderBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Placing Order...'; }

    const res = await fetch('/buyer/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: cart, address_id: addressId, payment_method: payment }),
    }).then(r => r.json()).catch(() => ({ error: 'Network error.' }));

    if (res.order_id) {
        localStorage.removeItem('luxe_cart');
        updateCartBadge();
        window.location.href = `/buyer/order_summary?id=${res.order_id}`;
    } else {
        showToast(res.error || 'Failed to place order.', true);
        if (btn) { btn.disabled = false; btn.textContent = 'Place Order'; }
    }
}

// ── Order summary page ────────────────────────────────────────
async function loadOrderSummary() {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) return;

    const order = await fetch(`/buyer/api/orders/${id}`).then(r => r.json()).catch(() => null);
    if (!order) return;

    const set = (elId, val) => { const el = document.getElementById(elId); if (el) el.innerHTML = val; };
    set('orderId',    `#${order.id?.slice(0,8).toUpperCase()}`);
    set('orderDate',  formatDate(order.created_at));
    set('orderTotal', formatCurrency(order.total));
    set('orderStatus', `<span class="badge bg-success">${order.status}</span>`);
}

// ── Orders history page ───────────────────────────────────────
async function loadOrders() {
    const container = document.getElementById('ordersList');
    if (!container) return;

    const data = await API.buyer.getOrders().catch(() => []);

    if (!data.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📦</div>
                <h5>No orders yet</h5>
                <p>Start shopping to see your orders here.</p>
                <a href="/buyer/market" class="btn-pink px-4 py-2">Shop Now</a>
            </div>`;
        return;
    }

    container.innerHTML = data.map(o => `
        <div class="card mb-3 border-0 shadow-sm">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <div style="font-size:13px;font-weight:700">Order #${(o.id||'').slice(0,8).toUpperCase()}</div>
                        <div style="font-size:12px;color:var(--gray)">${formatDate(o.created_at)}</div>
                    </div>
                    <span class="badge badge-${o.status} text-uppercase">${o.status}</span>
                </div>
                <div style="font-size:13px;margin-bottom:8px">${o.items_count || 0} item(s) · <strong>${formatCurrency(o.total)}</strong></div>
                <a href="/buyer/order_summary?id=${o.id}" class="btn-outline-pink px-3 py-1" style="font-size:12px">View Details</a>
            </div>
        </div>
    `).join('');
}

// ── Wishlist page ─────────────────────────────────────────────
function loadWishlist() {
    const grid = document.getElementById('wishlistGrid');
    if (!grid) return;

    const list = getWishlist();

    if (!list.length) {
        grid.innerHTML = `
            <div class="col-12">
                <div class="empty-state">
                    <div class="empty-icon">❤️</div>
                    <h5>Your wishlist is empty</h5>
                    <p>Save items you love to buy them later.</p>
                    <a href="/buyer/market" class="btn-pink px-4 py-2">Browse Products</a>
                </div>
            </div>`;
        return;
    }

    grid.innerHTML = list.map(p => renderProductCard(p)).join('');
}

// ── Address book page ─────────────────────────────────────────
async function loadAddressBook() {
    const container = document.getElementById('addressList');
    if (!container) return;

    const data = await API.buyer.getAddresses().catch(() => []);

    if (!data.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📍</div>
                <h5>No saved addresses</h5>
                <p>Add your delivery address to get started.</p>
            </div>`;
        return;
    }

    container.innerHTML = data.map(a => `
        <div class="address-card mb-3">
            ${a.is_default ? '<span class="default-badge">Default</span>' : ''}
            <div style="font-size:14px;font-weight:600;margin-bottom:4px">${a.label || 'Home'}</div>
            <div style="font-size:13px;color:var(--gray)">${[a.street, a.barangay, a.city, a.region, a.zip_code].filter(Boolean).join(', ')}</div>
            ${a.latitude ? `<div style="font-size:12px;color:var(--gray);margin-top:4px">📍 ${Number(a.latitude).toFixed(5)}, ${Number(a.longitude).toFixed(5)}</div>` : ''}
            <div class="d-flex gap-2 mt-3">
                <button class="btn btn-sm btn-outline-secondary" onclick="editAddress('${a.id}')">Edit</button>
                <button class="btn btn-sm btn-outline-danger"    onclick="deleteAddress('${a.id}')">Delete</button>
                ${!a.is_default ? `<button class="btn btn-sm btn-outline-success" onclick="setDefault('${a.id}')">Set Default</button>` : ''}
            </div>
        </div>
    `).join('');
}

function initAddressMap() {
    const mapEl = document.getElementById('addressMap');
    if (!mapEl || typeof L === 'undefined') return;

    const map = L.map('addressMap').setView([12.8797, 121.7740], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    let marker;
    map.on('click', (e) => {
        const { lat, lng } = e.latlng;
        if (marker) marker.setLatLng(e.latlng);
        else marker = L.marker(e.latlng).addTo(map);
        const latEl = document.getElementById('addrLatitude');
        const lngEl = document.getElementById('addrLongitude');
        const dispEl = document.getElementById('addrCoordsDisplay');
        if (latEl)  latEl.value  = lat.toFixed(7);
        if (lngEl)  lngEl.value  = lng.toFixed(7);
        if (dispEl) dispEl.textContent = `📍 Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
    });
}

async function saveAddress(e) {
    e.preventDefault();
    const g = id => document.getElementById(id)?.value.trim();
    const payload = {
        label:     g('addrLabel'),
        region:    g('addrRegion'),
        city:      g('addrCity'),
        barangay:  g('addrBarangay'),
        street:    g('addrStreet'),
        zip_code:  g('addrZip'),
        latitude:  g('addrLatitude')  || null,
        longitude: g('addrLongitude') || null,
    };

    const res = await fetch('/buyer/api/addresses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    }).then(r => r.json()).catch(() => ({ error: 'Network error.' }));

    if (res.success) {
        showToast('Address saved!');
        document.getElementById('addressForm')?.reset();
        loadAddressBook();
        bootstrap.Modal.getInstance(document.getElementById('addAddressModal'))?.hide();
    } else {
        showToast(res.error || 'Failed to save address.', true);
    }
}

async function deleteAddress(id) {
    if (!confirm('Delete this address?')) return;
    await fetch(`/buyer/api/addresses/${id}`, { method: 'DELETE' });
    showToast('Address deleted.');
    loadAddressBook();
}

async function setDefault(id) {
    await fetch(`/buyer/api/addresses/${id}/default`, { method: 'POST' });
    showToast('Default address updated.');
    loadAddressBook();
}

// ── Settings page ─────────────────────────────────────────────
function initSettings() {
    const links = document.querySelectorAll('.settings-nav .nav-link');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            const target = link.dataset.section;
            document.querySelectorAll('.settings-section').forEach(s => s.classList.remove('active'));
            document.getElementById(target)?.classList.add('active');
        });
    });
}

async function saveProfile(e) {
    e.preventDefault();
    const payload = {
        full_name: document.getElementById('profileName')?.value.trim(),
        phone:     document.getElementById('profilePhone')?.value.trim(),
    };
    const res = await fetch('/buyer/api/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    }).then(r => r.json()).catch(() => ({ error: 'Network error.' }));
    showToast(res.success ? 'Profile updated!' : (res.error || 'Failed.'), !res.success);
}

async function changePassword(e) {
    e.preventDefault();
    const current  = document.getElementById('currentPw')?.value;
    const newPw    = document.getElementById('newPw')?.value;
    const confirm  = document.getElementById('confirmPw')?.value;
    if (newPw !== confirm) { showToast('Passwords do not match.', true); return; }
    const res = await fetch('/buyer/api/password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: current, new_password: newPw }),
    }).then(r => r.json()).catch(() => ({ error: 'Network error.' }));
    showToast(res.success ? 'Password changed!' : (res.error || 'Failed.'), !res.success);
}

// ── Init on page load ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
    if (document.getElementById('productGrid'))    loadMarket();
    if (document.getElementById('productName'))    loadProduct();
    if (document.getElementById('cartItems'))      loadCart();
    if (document.getElementById('checkoutItems'))  loadCheckout();
    if (document.getElementById('orderId'))        loadOrderSummary();
    if (document.getElementById('ordersList'))     loadOrders();
    if (document.getElementById('wishlistGrid'))   loadWishlist();
    if (document.getElementById('addressList'))    { loadAddressBook(); initAddressMap(); }
    if (document.querySelector('.settings-nav'))   initSettings();
});
