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
async function updateCartBadge() {
    const cart = await API.buyer.getCart().catch(() => []);
    const total = cart.reduce((sum, i) => sum + Number(i.quantity || 0), 0);
    document.querySelectorAll('.cart-count').forEach(el => {
        el.textContent = total;
        el.style.display = total > 0 ? 'flex' : 'none';
    });
}

// ── Cart (Supabase-backed) ────────────────────────────────────
async function addToCart(product, quantity = 1, variantId = null) {
    const res = await API.buyer.addToCart({
        product_id: product.id,
        variant_id: variantId,
        quantity: quantity,
    }).catch(() => ({ error: 'Network error.' }));
    if (res.success) {
        showToast(`✅ ${product.name} added to cart!`);
        updateCartBadge();
    } else {
        showToast(res.error || 'Failed to add to cart.', true);
    }
}

async function removeFromCart(itemId) {
    await API.buyer.removeCartItem(itemId).catch(() => null);
    updateCartBadge();
}

async function updateQty(itemId, qty) {
    await API.buyer.updateCartItem(itemId, qty).catch(() => null);
    updateCartBadge();
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

    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:60px 0"><div class="home-spinner"></div></div>`;

    const query = Object.entries(params)
        .filter(([, v]) => v !== '' && v != null)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');

    const data = await fetch(`/buyer/api/products${query ? '?' + query : ''}`)
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw new Error(JSON.stringify(e)); });
            return r.json();
        })
        .catch(err => {
            console.error('loadMarket error:', err);
            return null;
        });

    if (!data || !Array.isArray(data) || !data.length) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:60px 20px">
                <div style="font-size:48px;margin-bottom:16px">${!data ? '⚠️' : '🔍'}</div>
                <div style="font-size:16px;font-weight:600;color:var(--color-text-dark);margin-bottom:8px">
                    ${!data ? 'Failed to load products' : 'No products found'}
                </div>
                <p style="font-size:13px;color:#999">
                    ${!data ? 'Check the browser console for details.' : 'Try adjusting your filters.'}
                </p>
            </div>`;
        return;
    }

    grid.innerHTML = '';
    data.forEach(p => grid.appendChild(buildMarketCard(p)));
}

function buildMarketCard(p) {
    const price    = parseFloat(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
    const imgSrc   = p.image ? (p.image.startsWith('/') ? p.image : '/' + p.image) : '';
    const imgEl    = imgSrc
        ? `<img src="${imgSrc}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover">`
        : `<span style="font-size:48px">🛍️</span>`;
    const seller   = p.seller ? `${p.seller.first_name || ''} ${p.seller.last_name || ''}`.trim() : '';
    const stock    = p.total_stock ?? 0;
    const wishlisted = isWishlisted(p.id);

    const card = document.createElement('div');
    card.className = 'product-card';
    card.style.cursor = 'pointer';
    card.innerHTML = `
        <div class="product-image-wrapper" onclick="window.location='/buyer/product?id=${p.id}'">
            ${imgEl}
            <button class="product-wishlist ${wishlisted ? 'active' : ''}"
                onclick="event.stopPropagation(); handleWishlist(this, ${JSON.stringify(p).replace(/"/g, '&quot;')})"
                title="Wishlist">❤️</button>
        </div>
        <h3 class="product-name" onclick="window.location='/buyer/product?id=${p.id}'" style="cursor:pointer">${p.name}</h3>
        ${seller ? `<div style="font-size:11px;color:#999;margin-bottom:4px">by ${seller}</div>` : ''}
        <div class="product-price">
            <span class="current">₱${price}</span>
        </div>
        <div style="font-size:11px;color:#999;margin-bottom:10px">
            ${stock > 0 ? `${stock} in stock` : '<span style="color:#e74c3c">Out of stock</span>'}
        </div>
        <button class="quick-add-btn"
            onclick="addToCart({id:'${p.id}',name:'${p.name}'})"
            ${stock <= 0 ? 'disabled style="opacity:0.5;cursor:not-allowed"' : ''}>
            ${stock > 0 ? 'Add to Cart' : 'Out of Stock'}
        </button>`;
    return card;
}

function handleWishlist(btn, product) {
    const added = toggleWishlist(product);
    btn.classList.toggle('active', added);
}

// ── Product card rendering ────────────────────────────────────
function renderProductCard(p) {
    const price    = parseFloat(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
    const imgSrc   = p.image ? (p.image.startsWith('/') ? p.image : '/' + p.image) : '';
    const imgEl    = imgSrc
        ? `<img src="${imgSrc}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover">`
        : `<span style="font-size:48px">🛍️</span>`;
    const seller   = p.seller ? `${p.seller.first_name || ''} ${p.seller.last_name || ''}`.trim() : '';
    const stock    = p.total_stock ?? 0;
    const wishlisted = isWishlisted(p.id);

    return `
        <div class="col-md-4 col-sm-6 mb-4">
            <div class="product-card">
                <div class="product-image-wrapper" onclick="window.location='/buyer/product?id=${p.id}'">
                    ${imgEl}
                    <button class="product-wishlist ${wishlisted ? 'active' : ''}"
                        onclick="event.stopPropagation(); handleWishlist(this, ${JSON.stringify(p).replace(/"/g, '&quot;')})"
                        title="Wishlist">❤️</button>
                </div>
                <h3 class="product-name" onclick="window.location='/buyer/product?id=${p.id}'" style="cursor:pointer">${p.name}</h3>
                ${seller ? `<div style="font-size:11px;color:#999;margin-bottom:4px">by ${seller}</div>` : ''}
                <div class="product-price">
                    <span class="current">₱${price}</span>
                </div>
                <div style="font-size:11px;color:#999;margin-bottom:10px">
                    ${stock > 0 ? `${stock} in stock` : '<span style="color:#e74c3c">Out of stock</span>'}
                </div>
                <button class="quick-add-btn"
                    onclick="addToCart({id:'${p.id}',name:'${p.name}'})"
                    ${stock <= 0 ? 'disabled style="opacity:0.5;cursor:not-allowed"' : ''}>
                    ${stock > 0 ? 'Add to Cart' : 'Out of Stock'}
                </button>
            </div>
        </div>`;
}

// ── Product detail page ───────────────────────────────────────
async function loadProduct() {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) return;

    const p = await API.shop.getProduct(id).catch(() => null);
    if (!p) return;

    const set = (elId, val) => { const el = document.getElementById(elId); if (el) el.innerHTML = val; };
    set('productName',     p.name);
    set('productBreadcrumbName', p.name);
    set('productPrice',    formatCurrency(p.price));
    set('productOriginal', p.original_price ? formatCurrency(p.original_price) : '');
    set('productDesc',     p.description || 'No description available.');
    set('productRating',   `<span class="stars">${renderStars(p.rating || 0)}</span> (${p.reviews || 0} reviews)`);

    const stock = p.total_stock ?? p.stock ?? 0;
    set('productStock', stock > 0 ? `<span style="color:#10b981">In Stock (${stock})</span>` : `<span style="color:#ef4444">Out of Stock</span>`);

    const variantsEl = document.getElementById('productVariants');
    const variantSelect = document.getElementById('selectedVariant');
    if (variantsEl) {
        const variants = p.product_variants || [];
        variantsEl.innerHTML = variants.length
            ? variants.map(v => `<span style="display:inline-block;margin-right:8px;padding:4px 8px;background:#f9f9f9;border-radius:999px">${v.variant_type}: ${v.value} (${v.stock})</span>`).join('')
            : 'No variants listed';
        if (variantSelect) {
            variantSelect.innerHTML = `<option value="">No variant</option>` + variants
                .map(v => `<option value="${v.id}">${v.variant_type}: ${v.value} (${v.stock})</option>`)
                .join('');
        }
    }

    const mainImageEl = document.getElementById('productMainImage');
    const thumbsEl = document.getElementById('productThumbs');
    const images = p.product_images || [];
    const primary = images.find(i => i.is_primary) || images[0];
    if (mainImageEl) {
        if (primary && primary.image_url) {
            const imageUrl = primary.image_url.startsWith('/') ? primary.image_url : '/' + primary.image_url;
            mainImageEl.innerHTML = `<img src="${imageUrl}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover">`;
        } else {
            mainImageEl.textContent = p.emoji || '🛍️';
        }
    }
    if (thumbsEl) {
        thumbsEl.innerHTML = images.map(img => {
            const imageUrl = img.image_url.startsWith('/') ? img.image_url : '/' + img.image_url;
            return `
            <button type="button" style="border:1px solid #eee;background:#fff;padding:0;border-radius:6px;overflow:hidden;height:64px" onclick="setMainProductImage('${imageUrl.replace(/'/g, "\\'")}')">
                <img src="${imageUrl}" alt="thumbnail" style="width:100%;height:100%;object-fit:cover">
            </button>
        `;
        }).join('');
    }

    const addBtn = document.getElementById('addToCartBtn');
    if (addBtn) addBtn.onclick = () => addToCart({ id: p.id, name: p.name }, detailQty, variantSelect?.value || null);
}

function setMainProductImage(url) {
    const mainImageEl = document.getElementById('productMainImage');
    if (!mainImageEl) return;
    const imageUrl = url.startsWith('/') ? url : '/' + url;
    mainImageEl.innerHTML = `<img src="${imageUrl}" alt="product image" style="width:100%;height:100%;object-fit:cover">`;
}

// ── Cart page ─────────────────────────────────────────────────
function loadCart() {
    // The new cart.html has its own loadCartPage() — this fallback
    // handles any legacy page that still uses #cartItems.
    const container = document.getElementById('cartItems');
    const emptyEl   = document.getElementById('cartEmpty');
    const summaryEl = document.getElementById('cartSummary');
    if (!container) return;

    API.buyer.getCart().then(cart => {
        if (!cart.length) {
            container.innerHTML = '';
            if (emptyEl)   emptyEl.style.display  = 'block';
            if (summaryEl) summaryEl.style.display = 'none';
            return;
        }
        if (emptyEl)   emptyEl.style.display  = 'none';
        if (summaryEl) summaryEl.style.display = 'block';

        container.innerHTML = cart.map(item => {
            const imgSrc = item.image
                ? (item.image.startsWith('/') ? item.image : '/' + item.image)
                : null;
            return `
            <div class="cart-item">
                <div class="cart-item-img">${imgSrc ? `<img src="${imgSrc}" onerror="this.parentElement.innerHTML='🛍️'">` : '🛍️'}</div>
                <div class="flex-grow-1">
                    <div style="font-size:14px;font-weight:600;margin-bottom:4px">${item.name || item.product?.name || 'Product'}</div>
                    <div style="font-size:15px;font-weight:700;color:var(--pink);margin-bottom:8px">${formatCurrency(item.price_snapshot)}</div>
                    <div class="qty-control">
                        <button class="qty-btn" onclick="changeQty('${item.id}', ${Number(item.quantity) - 1})">−</button>
                        <span class="qty-value">${item.quantity}</span>
                        <button class="qty-btn" onclick="changeQty('${item.id}', ${Number(item.quantity) + 1})">+</button>
                    </div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:15px;font-weight:700;margin-bottom:8px">${formatCurrency(item.subtotal)}</div>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeFromCart('${item.id}'); loadCart()">🗑️</button>
                </div>
            </div>`;
        }).join('');

        updateCartSummary(cart.map(i => ({ price: Number(i.price_snapshot || 0), qty: Number(i.quantity || 0) })));
    }).catch(() => {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div>Failed to load cart.</div>';
    });
}

async function changeQty(id, qty) {
    await updateQty(id, qty);
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
    API.buyer.getCart().then(cart => {
        if (!cart.length) { window.location.href = '/buyer/cart'; return; }

        const list = document.getElementById('checkoutItems');
        if (list) {
            list.innerHTML = cart.map(i => `
            <div class="d-flex justify-content-between align-items-center mb-2" style="font-size:13px">
                <span>🛍️ ${i.name || i.product?.name || 'Product'} × ${i.quantity}</span>
                <span style="font-weight:600">${formatCurrency(i.subtotal)}</span>
            </div>
        `).join('');
        }

        updateCartSummary(cart.map(i => ({ price: Number(i.price_snapshot || 0), qty: Number(i.quantity || 0) })));
        loadAddressOptions();
    }).catch(() => {
        showToast('Failed to load checkout items.', true);
    });
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
    const addressId = document.getElementById('selectedAddressId')?.value;
    const payment   = document.querySelector('input[name="payment"]:checked')?.value;

    if (!addressId) { showToast('Please select a delivery address.', true); return; }
    if (!payment)   { showToast('Please select a payment method.', true); return; }

    const btn = document.getElementById('placeOrderBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Placing Order...'; }

    const res = await API.buyer.checkout({
        address_id: addressId,
        payment_method: payment,
    }).catch(() => ({ error: 'Network error.' }));

    if (res.order_id) {
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
    set('orderStatus', `<span class="badge bg-dark">${order.status.replace(/_/g, ' ').toUpperCase()}</span>`);

    const statusOrder = ['pending', 'processing', 'ready_for_pickup', 'in_transit', 'delivered'];
    const currentIndex = statusOrder.indexOf(order.status);

    statusOrder.forEach((status, index) => {
        const item = document.getElementById(`step-${status}`);
        const dateEl = document.getElementById(`step-${status}-date`);
        if (!item || !dateEl) return;

        if (index <= currentIndex) {
            item.classList.add('done');
            item.classList.remove('active');
        } else {
            item.classList.remove('done');
            item.classList.remove('active');
        }
        if (index === currentIndex) {
            item.classList.add('active');
        }

        if (status === 'pending') {
            dateEl.textContent = formatDate(order.created_at);
        } else {
            dateEl.textContent = index <= currentIndex ? 'Completed' : 'Pending';
        }
    });
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

    // Update count badge
    const countBadge = document.getElementById('wishlistCount');
    if (countBadge) countBadge.textContent = list.length;

    if (!list.length) {
        grid.innerHTML = `
            <div class="wishlist-empty">
                <div class="empty-heart">❤️</div>
                <h3>Your wishlist is empty</h3>
                <p>Save items you love to buy them later.</p>
                <a href="/buyer/market" class="btn-browse">Browse Products</a>
            </div>`;
        return;
    }

    grid.innerHTML = '';
    list.forEach(p => grid.appendChild(buildWishlistCard(p)));
}

function buildWishlistCard(p) {
    const price = parseFloat(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
    const imgSrc = p.image ? (p.image.startsWith('/') ? p.image : '/' + p.image) : '';
    const seller = p.seller ? `${p.seller.first_name || ''} ${p.seller.last_name || ''}`.trim() : '';
    const stock = p.total_stock ?? p.stock ?? 0;

    const card = document.createElement('div');
    card.className = 'wishlist-card';

    const imgEl = imgSrc
        ? `<img src="${imgSrc}" alt="${p.name}" onerror="this.parentElement.innerHTML='<span class=\\'wc-image-placeholder\\'>🛍️</span>'">`
        : `<span class="wc-image-placeholder">🛍️</span>`;

    card.innerHTML = `
        <div class="wc-image" onclick="window.location='/buyer/product?id=${p.id}'">
            ${imgEl}
            <button class="wc-remove" onclick="event.stopPropagation(); removeWishlistItem(${JSON.stringify(p).replace(/"/g, '"')})" title="Remove from wishlist">✕</button>
        </div>
        <div class="wc-body">
            <h3 class="wc-name" onclick="window.location='/buyer/product?id=${p.id}'">${p.name}</h3>
            ${seller ? `<div class="wc-seller">by ${seller}</div>` : ''}
            <div class="wc-price">₱${price}</div>
            <div class="wc-stock ${stock > 0 ? 'in-stock' : 'out-stock'}">
                ${stock > 0 ? `${stock} in stock` : 'Out of stock'}
            </div>
            <div class="wc-actions">
                <button class="wc-btn-cart" onclick="addToCart({id:'${p.id}',name:'${p.name}'})" ${stock <= 0 ? 'disabled' : ''}>
                    ${stock > 0 ? 'Add to Cart' : 'Out of Stock'}
                </button>
                <button class="wc-btn-remove" onclick="removeWishlistItem(${JSON.stringify(p).replace(/"/g, '"')})">
                    ❤️ Remove
                </button>
            </div>
        </div>`;
    return card;
}

function removeWishlistItem(product) {
    const list = getWishlist();
    const idx = list.findIndex(i => i.id === product.id);
    if (idx > -1) {
        list.splice(idx, 1);
        localStorage.setItem('luxe_wishlist', JSON.stringify(list));
        showToast('Removed from wishlist.');
        loadWishlist(); // Refresh the grid
        updateWishlistIcons(); // Update heart icons on other pages
    }
}

function updateWishlistIcons() {
    // Update all wishlist heart icons across the page
    const wishlist = getWishlist();
    document.querySelectorAll('.product-wishlist').forEach(btn => {
        const card = btn.closest('.product-card');
        if (card) {
            const productId = card.dataset.productId || null;
            if (productId) {
                const isWishlisted = wishlist.some(i => i.id == productId);
                btn.classList.toggle('active', isWishlisted);
            }
        }
    });
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

async function editAddress(id) {
    // For now, just show a message. You can implement full editing later
    showToast('Edit address feature coming soon!', true);
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
    // Only call loadProduct if we're not on the dedicated product detail page
    if (document.getElementById('productName') && !document.getElementById('productMainImage'))    loadProduct();
    if (document.getElementById('cartItems'))      loadCart();  // legacy cart pages only
    if (document.getElementById('checkoutItems'))  loadCheckout();
    if (document.getElementById('orderId')) {
        loadOrderSummary();
        setInterval(() => loadOrderSummary(), 15000);
    }
    if (document.getElementById('ordersList')) {
        loadOrders();
        setInterval(() => loadOrders(), 15000);
    }
    if (document.getElementById('wishlistGrid'))   loadWishlist();
    if (document.getElementById('addressList'))    { loadAddressBook(); initAddressMap(); }
    if (document.querySelector('.settings-nav'))   initSettings();
    if (document.getElementById('profilePreview')) initProfilePicturePreview();
});

// ── Profile Picture Functions ─────────────────────────────────
function initProfilePicturePreview() {
    const preview   = document.getElementById('profilePreview');
    const input     = document.getElementById('profilePictureInput');
    const changeBtn = document.getElementById('changePicBtn');
    const picUrl    = document.body.dataset.profilePicture;
    if (preview) preview.src = picUrl ? '/' + picUrl : '/static/uploads/default-avatar.png';
    changeBtn?.addEventListener('click', () => input?.click());
    input?.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file && preview) {
            const reader = new FileReader();
            reader.onload = (ev) => { preview.src = ev.target.result; };
            reader.readAsDataURL(file);
        }
    });
}
