/**
 * seller.js — All seller page logic
 * Depends on: api.js, ui.js
 */

// ── Sidebar mobile toggle ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const toggle  = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (overlay) overlay.style.display =
                sidebar.classList.contains('open') ? 'block' : 'none';
        });
    }
    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar?.classList.remove('open');
            overlay.style.display = 'none';
        });
    }
});

// ── Helpers ───────────────────────────────────────────────────
function formatCurrency(amount) {
    return '₱' + Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
}

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-PH', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

function showToast(msg, isError = false) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.style.background = isError ? '#c0392b' : '#1a1a3e';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

function setFilterTab(el, callback, value) {
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    callback(value);
}

// ── Products ──────────────────────────────────────────────────
async function loadProducts(filter = 'all') {
    const tbody = document.getElementById('productsTable');
    if (!tbody) return;

    const data = await API.seller.getProducts().catch(() => []);
    const filtered = filter === 'all' ? data : data.filter(p => p.status === filter);

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="6">
            <div class="empty-state"><div class="empty-icon">📦</div>
            No products yet.
            <a href="/seller/products/add" style="color:var(--pink);font-weight:600">Add your first product</a>
            </div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => `
        <tr>
            <td>${p.name || '—'}</td>
            <td>${formatCurrency(p.price)}</td>
            <td>${p.stock ?? 0}</td>
            <td>${p.sales ?? 0}</td>
            <td><span class="badge badge-${p.status}">${p.status}</span></td>
            <td class="actions">
                <a href="/seller/products/${p.id}/edit" class="btn btn-view">Edit</a>
                <button class="btn btn-reject" onclick="deleteProduct('${p.id}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

async function deleteProduct(id) {
    if (!confirm('Delete this product?')) return;
    showToast('Product deleted.');
    loadProducts();
}

// ── Orders ────────────────────────────────────────────────────
async function loadOrders(filter = 'all') {
    const tbody = document.getElementById('ordersTable');
    if (!tbody) return;

    const data     = await API.seller.getOrders().catch(() => []);
    const filtered = filter === 'all' ? data : data.filter(o => o.status === filter);

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">🛒</div>No orders found.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(o => `
        <tr>
            <td>#${(o.id || '').slice(0,8)}</td>
            <td>${o.customer_name || '—'}</td>
            <td>${o.items ?? 0}</td>
            <td>${formatCurrency(o.total)}</td>
            <td><span class="badge badge-${o.status}">${o.status}</span></td>
            <td>${formatDate(o.created_at)}</td>
            <td><button class="btn btn-view" onclick="viewOrder('${o.id}')">View</button></td>
        </tr>
    `).join('');
}

function viewOrder(id) {
    console.log('View order:', id);
}

// ── Shipping ──────────────────────────────────────────────────
async function loadShipping(filter = 'all') {
    const tbody = document.getElementById('shippingTable');
    if (!tbody) return;

    const data     = await API.seller.getShipping().catch(() => []);
    const filtered = filter === 'all' ? data : data.filter(s => s.status === filter);

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">🚚</div>No active deliveries.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(s => `
        <tr>
            <td>#${(s.order_id || '').slice(0,8)}</td>
            <td>${s.customer_name || '—'}</td>
            <td>${s.address || '—'}</td>
            <td>${s.rider_name || 'Unassigned'}</td>
            <td><span class="badge badge-${s.status}">${s.status}</span></td>
            <td><button class="btn btn-view">Track</button></td>
        </tr>
    `).join('');
}

// ── Earnings ──────────────────────────────────────────────────
async function loadEarnings() {
    const data = await API.seller.getEarnings().catch(() => ({}));
    const set  = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('totalEarnings',  formatCurrency(data.total));
    set('pendingPayout',  formatCurrency(data.pending));
    set('releasedPayout', formatCurrency(data.released));
    set('monthEarnings',  formatCurrency(data.month));
}

// ── Store map ─────────────────────────────────────────────────
function initStoreMap() {
    const mapEl = document.getElementById('storeMap');
    if (!mapEl || typeof L === 'undefined') return;

    const map = L.map('storeMap').setView([12.8797, 121.7740], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    let marker;
    map.on('click', (e) => {
        const { lat, lng } = e.latlng;
        if (marker) marker.setLatLng(e.latlng);
        else marker = L.marker(e.latlng).addTo(map);
        const el = document.getElementById('coordsDisplay');
        if (el) el.textContent = `📍 Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
        const latInput = document.getElementById('store_latitude');
        const lngInput = document.getElementById('store_longitude');
        if (latInput) latInput.value = lat.toFixed(7);
        if (lngInput) lngInput.value = lng.toFixed(7);
    });
}

// ── Store form save ───────────────────────────────────────────
async function saveStore(e) {
    e.preventDefault();
    const data = {
        store_name:        document.getElementById('store_name')?.value.trim(),
        store_description: document.getElementById('store_description')?.value.trim(),
        open_time:         document.getElementById('open_time')?.value,
        close_time:        document.getElementById('close_time')?.value,
        latitude:          document.getElementById('store_latitude')?.value,
        longitude:         document.getElementById('store_longitude')?.value,
    };
    const res = await API.seller.updateStore(data);
    showToast(res.success ? 'Store updated!' : (res.error || 'Failed.'), !res.success);
}

// ── Reviews ───────────────────────────────────────────────────
async function loadReviews(filter = 'all') {
    const container = document.getElementById('reviewsList');
    if (!container) return;

    const data     = await API.seller.getReviews().catch(() => []);
    const filtered = filter === 'all' ? data : data.filter(r => String(r.rating) === filter);

    if (!filtered.length) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">⭐</div>No reviews yet.</div>`;
        return;
    }

    container.innerHTML = filtered.map(r => `
        <div style="padding:16px;border-bottom:1px solid var(--border)">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <strong style="font-size:13px">${r.customer_name || 'Anonymous'}</strong>
                <span class="stars">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)}</span>
            </div>
            <p style="font-size:13px;color:var(--gray)">${r.comment || ''}</p>
            <div style="font-size:11px;color:#999;margin-top:4px">${formatDate(r.created_at)}</div>
        </div>
    `).join('');
}

// ── Page init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('productsTable')) loadProducts();
    if (document.getElementById('ordersTable'))   loadOrders();
    if (document.getElementById('shippingTable')) loadShipping();
    if (document.getElementById('reviewsList'))   loadReviews();
    if (document.getElementById('storeMap'))      initStoreMap();
    if (document.getElementById('totalEarnings')) loadEarnings();

    const storeForm = document.getElementById('storeForm');
    if (storeForm) storeForm.addEventListener('submit', saveStore);
});
