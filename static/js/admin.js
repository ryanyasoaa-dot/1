/**
 * admin.js — All admin page logic
 * Depends on: api.js
 */

// ── Helpers ───────────────────────────────────────────────────
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

    // Init page based on what's present in DOM
    if (document.getElementById('recentApps'))   loadDashboard();
    if (document.getElementById('appTableBody')) loadApplications();
    if (document.getElementById('usersTable'))   loadUsers();
    if (document.getElementById('sellersTable')) loadSellers();
    if (document.getElementById('ridersTable'))  loadRiders();
    if (document.getElementById('ordersTable'))  loadAdminOrders();
    if (document.getElementById('productsTableBody')) loadAdminProducts();
});

// ── Status update (shared) ────────────────────────────────────
async function updateStatus(id, status, notes = '') {
    const res = await API.applications.updateStatus(id, status, notes);
    if (res.success) {
        showToast(`✅ ${status.charAt(0).toUpperCase() + status.slice(1)} successfully.`);
        setTimeout(() => location.reload(), 1500);
    } else {
        showToast(res.error || 'Action failed.', true);
    }
}

// ── Dashboard ─────────────────────────────────────────────────
async function loadDashboard() {
    const data = await API.applications.getAll();
    const set  = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    set('stat-users',    data.length);
    set('stat-pending',  data.filter(a => a.status === 'pending').length);
    set('stat-approved', data.filter(a => a.status === 'approved').length);
    set('stat-sellers',  data.filter(a => a.role === 'seller' && a.status === 'approved').length);
    set('stat-riders',   data.filter(a => a.role === 'rider'  && a.status === 'approved').length);
    set('stat-buyers',   data.filter(a => a.role === 'buyer'  && a.status === 'approved').length);

    const tbody   = document.getElementById('recentApps');
    const pending = data.filter(a => a.status === 'pending').slice(0, 5);

    if (!pending.length) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">✅</div>No pending applications.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = pending.map(a => `
        <tr>
            <td>${a.full_name || '—'}</td>
            <td>${a.email    || '—'}</td>
            <td><span class="badge badge-${a.role}">${a.role}</span></td>
            <td>${formatDate(a.created_at)}</td>
            <td class="actions">
                <button class="btn btn-approve" onclick="updateStatus('${a.id}','approved')">Approve</button>
                <a href="/admin/applications" class="btn btn-view">Details</a>
            </td>
        </tr>
    `).join('');
}

// ── Applications ──────────────────────────────────────────────
let allApplications = [];
let currentAppId    = null;
let allAdminOrders  = [];

async function loadApplications() {
    allApplications = await API.applications.getAll();
    updateAppStats(allApplications);
    renderApps(allApplications);
}

function updateAppStats(data) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('stat-total',    data.length);
    set('stat-pending',  data.filter(a => a.status === 'pending').length);
    set('stat-approved', data.filter(a => a.status === 'approved').length);
    set('stat-rejected', data.filter(a => a.status === 'rejected').length);
}

function renderApps(data) {
    const tbody = document.getElementById('appTableBody');
    if (!tbody) return;

    if (!data.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">📋</div>No applications found.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = data.map(a => `
        <tr>
            <td>${a.full_name || '—'}</td>
            <td>${a.email    || '—'}</td>
            <td><span class="badge badge-${a.role}">${a.role}</span></td>
            <td><span class="badge badge-${a.status}">${a.status}</span></td>
            <td>${formatDate(a.created_at)}</td>
            <td class="actions">
                <button class="btn btn-view" onclick="openAppModal('${a.id}')">View</button>
                ${a.status === 'pending' ? `
                <button class="btn btn-approve" onclick="updateStatus('${a.id}','approved')">Approve</button>
                <button class="btn btn-reject"  onclick="openReject('${a.id}')">Reject</button>` : ''}
            </td>
        </tr>
    `).join('');
}

function filterApps(status) {
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-filter="${status}"]`)?.classList.add('active');
    const filtered = status === 'all' ? allApplications : allApplications.filter(a => a.status === status);
    renderApps(filtered);
}

// ── Application modal ─────────────────────────────────────────
async function openAppModal(id) {
    currentAppId = id;
    const a = await API.applications.getOne(id);
    const set = (elId, val) => { const el = document.getElementById(elId); if (el) el.textContent = val ?? '—'; };

    set('modal-appid',   a.id);
    set('modal-userid',  a.user_id);
    set('modal-name',    a.full_name);
    set('modal-email',   a.email);
    set('modal-phone',   a.phone);
    set('modal-role',    a.role);
    set('modal-status',  a.status);
    set('modal-date',    formatDate(a.created_at));
    set('modal-region',  a.region);
    set('modal-city',    a.city);
    set('modal-barangay',a.barangay);
    set('modal-street',  a.street);
    set('modal-zip',     a.zip_code);
    set('modal-lat',     a.latitude);
    set('modal-lng',     a.longitude);

    document.getElementById('seller-row').style.display = a.role === 'seller' ? 'block' : 'none';
    document.getElementById('rider-row').style.display  = a.role === 'rider'  ? 'block' : 'none';

    if (a.role === 'seller') {
        set('modal-store',          a.store_name);
        set('modal-store-category', a.store_category);
        set('modal-desc',           a.store_description);
    }
    if (a.role === 'rider') {
        set('modal-vehicle', a.vehicle_type);
        set('modal-license', a.license_number);
    }

    const docsEl = document.getElementById('modal-docs');
    docsEl.innerHTML = a.documents?.length
        ? a.documents.map(d => `<a class="doc-link" href="/${d.file_path}" target="_blank">📄 ${d.doc_type.replace(/_/g,' ').toUpperCase()}</a>`).join('')
        : '<span style="font-size:13px;color:#999">No documents uploaded.</span>';

    document.getElementById('modal-actions').style.display = a.status === 'pending' ? 'flex' : 'none';
    document.getElementById('modal-notes').value = '';
    document.getElementById('modalOverlay').classList.add('open');
}

function closeAppModal() {
    document.getElementById('modalOverlay').classList.remove('open');
    currentAppId = null;
}

async function approveFromModal() {
    const notes = document.getElementById('modal-notes').value.trim();
    await updateStatus(currentAppId, 'approved', notes);
    closeAppModal();
}

function openReject(id) {
    currentAppId = id;
    document.getElementById('rejectNotes').value = '';
    document.getElementById('rejectOverlay').classList.add('open');
}

function closeReject() {
    document.getElementById('rejectOverlay').classList.remove('open');
}

async function confirmReject() {
    const notes = document.getElementById('rejectNotes').value.trim();
    await updateStatus(currentAppId, 'rejected', notes);
    closeReject();
    closeAppModal();
}

// ── Users ─────────────────────────────────────────────────────
let allUsers    = [];
let userFilter  = 'all';

async function loadUsers() {
    allUsers = await API.applications.getAll();
    renderUsers(allUsers);
}

function renderUsers(data) {
    const tbody = document.getElementById('usersTable');
    if (!tbody) return;

    if (!data.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">👥</div>No users found.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = data.map(u => `
        <tr>
            <td>${u.full_name || '—'}</td>
            <td>${u.email    || '—'}</td>
            <td><span class="badge badge-${u.role}">${u.role}</span></td>
            <td><span class="badge badge-${u.status}">${u.status}</span></td>
            <td>${formatDate(u.created_at)}</td>
            <td class="actions">
                ${u.status === 'approved'
                    ? `<button class="btn btn-suspend" onclick="updateStatus('${u.id}','rejected')">Suspend</button>`
                    : `<button class="btn btn-approve" onclick="updateStatus('${u.id}','approved')">Activate</button>`
                }
            </td>
        </tr>
    `).join('');
}

function filterUsers(role, el) {
    userFilter = role;
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    searchUsers();
}

function searchUsers() {
    const q = (document.getElementById('searchInput')?.value || '').toLowerCase();
    let filtered = userFilter === 'all' ? allUsers : allUsers.filter(u => u.role === userFilter);
    if (q) filtered = filtered.filter(u =>
        (u.full_name||'').toLowerCase().includes(q) ||
        (u.email||'').toLowerCase().includes(q)
    );
    renderUsers(filtered);
}

// ── Sellers ───────────────────────────────────────────────────
async function loadSellers() {
    const data    = await API.applications.getAll();
    const sellers = data.filter(a => a.role === 'seller');
    const tbody   = document.getElementById('sellersTable');
    if (!tbody) return;

    if (!sellers.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">🏪</div>No sellers yet.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = sellers.map(s => `
        <tr>
            <td>${s.full_name  || '—'}</td>
            <td>${s.email      || '—'}</td>
            <td>${s.store_name || '—'}</td>
            <td><span class="badge badge-${s.status}">${s.status}</span></td>
            <td>${formatDate(s.created_at)}</td>
            <td class="actions">
                ${s.status === 'pending' ? `
                <button class="btn btn-approve" onclick="updateStatus('${s.id}','approved')">Approve</button>
                <button class="btn btn-reject"  onclick="openReject('${s.id}')">Reject</button>` :
                `<span style="font-size:12px;color:#999">${s.status}</span>`}
            </td>
        </tr>
    `).join('');
}

// ── Riders ────────────────────────────────────────────────────
async function loadRiders() {
    const data   = await API.applications.getAll();
    const riders = data.filter(a => a.role === 'rider');
    const tbody  = document.getElementById('ridersTable');
    if (!tbody) return;

    if (!riders.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">🏍️</div>No riders yet.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = riders.map(r => `
        <tr>
            <td>${r.full_name      || '—'}</td>
            <td>${r.email          || '—'}</td>
            <td>${r.vehicle_type   || '—'}</td>
            <td>${r.license_number || '—'}</td>
            <td><span class="badge badge-${r.status}">${r.status}</span></td>
            <td class="actions">
                ${r.status === 'pending' ? `
                <button class="btn btn-approve" onclick="updateStatus('${r.id}','approved')">Approve</button>
                <button class="btn btn-reject"  onclick="openReject('${r.id}')">Reject</button>` :
                `<span style="font-size:12px;color:#999">${r.status}</span>`}
            </td>
        </tr>
    `).join('');
}

// ── Admin Orders ─────────────────────────────────────────────
const adminOrderStatuses = ['pending', 'processing', 'ready_for_pickup', 'in_transit', 'delivered'];

async function loadAdminOrders(filter = 'all') {
    const tbody = document.getElementById('ordersTable');
    if (!tbody) return;

    allAdminOrders = await API.admin.getOrders().catch(() => []);
    const filtered = filter === 'all' ? allAdminOrders : allAdminOrders.filter(o => o.status === filter);

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="empty-icon">🛒</div>No orders found.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(o => {
        const buyer = o.buyer || {};
        const rider = o.rider || {};
        const statusOptions = adminOrderStatuses.map(status => `
            <option value="${status}" ${status === o.status ? 'selected' : ''}>
                ${status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </option>
        `).join('');
        return `
        <tr>
            <td>#${(o.id || '').slice(0,8)}</td>
            <td>${buyer.first_name || ''} ${buyer.last_name || ''}</td>
            <td>${rider.first_name || ''} ${rider.last_name || ''}</td>
            <td>₱${Number(o.total_amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
            <td><span class="badge badge-${o.status}">${o.status.replace(/_/g, ' ').toUpperCase()}</span></td>
            <td>${formatDate(o.created_at)}</td>
            <td>${(o.shipping_address?.street || '') + ', ' + (o.shipping_address?.city || '')}</td>
            <td class="actions">
                <button class="btn btn-view" onclick="showOrderDetails('${o.id}')">View</button>
                <select class="status-select" onchange="adminUpdateOrderStatus('${o.id}', this.value)">${statusOptions}</select>
            </td>
        </tr>`;
    }).join('');
}

function filterAdminOrders(status, el) {
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    loadAdminOrders(status);
}

function showOrderDetails(orderId) {
    const order = allAdminOrders.find(o => o.id === orderId);
    if (!order) {
        showToast('Order details not available.', true);
        return;
    }
    const buyer = order.buyer || {};
    const rider = order.rider || {};
    const summary = [
        `Order: #${(order.id || '').slice(0,8).toUpperCase()}`,
        `Status: ${order.status.replace(/_/g, ' ').toUpperCase()}`,
        `Buyer: ${buyer.first_name || ''} ${buyer.last_name || ''}`,
        `Rider: ${rider.first_name || ''} ${rider.last_name || ''}`.trim(),
        `Total: ₱${Number(order.total_amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 })}`,
    ].filter(Boolean).join('\n');
    alert(summary);
}

async function adminUpdateOrderStatus(orderId, status) {
    if (!status) return;
    const current = allAdminOrders.find(o => o.id === orderId);
    if (!current || current.status === status) return;

    let rider_id = '';
    if (status === 'in_transit' && !current.rider) {
        rider_id = prompt('Enter rider ID to assign for in_transit status (optional)') || '';
    }

    const res = await API.admin.updateOrderStatus(orderId, status, rider_id).catch(() => ({ error: 'Network error.' }));
    if (res.success) {
        showToast('Order status overridden successfully.');
        loadAdminOrders();
    } else {
        showToast(res.error || 'Failed to update status.', true);
    }
}

// ── Product moderation ────────────────────────────────────────
let productFilter = 'pending';
let selectedProductId = null;

function setProductFilter(el, status) {
    productFilter = status;
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    loadAdminProducts();
}

async function loadAdminProducts() {
    const tbody = document.getElementById('productsTableBody');
    if (!tbody) return;
    const status = productFilter === 'all' ? '' : productFilter;
    const products = await API.adminProducts.getAll(status).catch(() => []);

    if (!products.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">📦</div>No products found.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = products.map(p => `
        <tr>
            <td>${p.name || '—'}</td>
            <td>${p.seller ? `${p.seller.first_name || ''} ${p.seller.last_name || ''}`.trim() : '—'}</td>
            <td>${p.category || '—'}</td>
            <td>₱${Number(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
            <td><span class="badge badge-${p.status}">${p.status}</span></td>
            <td class="actions">
                <button class="btn btn-view" onclick="openProductModal('${p.id}')">View</button>
            </td>
        </tr>
    `).join('');
}

async function openProductModal(productId) {
    const p = await API.adminProducts.getOne(productId);
    if (!p || p.error) {
        showToast('Failed to load product.', true);
        return;
    }
    selectedProductId = productId;
    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? '—';
    };
    setText('product-modal-name', p.name);
    setText('product-modal-seller', p.seller ? `${p.seller.first_name || ''} ${p.seller.last_name || ''}`.trim() : '—');
    setText('product-modal-category', p.category);
    setText('product-modal-price', `₱${Number(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 })}`);
    setText('product-modal-status', p.status);
    setText('product-modal-stock', p.total_stock ?? 0);
    setText('product-modal-description', p.description || 'No description provided.');

    const variantsEl = document.getElementById('product-modal-variants');
    if (variantsEl) {
        const variants = p.product_variants || [];
        variantsEl.innerHTML = variants.length
            ? variants.map(v => `${v.variant_type}: ${v.value} (${v.stock} stock)`).join('<br>')
            : 'No variants';
    }

    const imagesEl = document.getElementById('product-modal-images');
    if (imagesEl) {
        const images = p.product_images || [];
        imagesEl.innerHTML = images.length
            ? images.map(img => `<img src="${img.image_url}" alt="product image" style="width:100%;height:90px;object-fit:cover;border-radius:6px;border:1px solid #eee">`).join('')
            : '<span style="font-size:12px;color:#999">No images</span>';
    }

    const actions = document.getElementById('product-modal-actions');
    if (actions) actions.style.display = p.status === 'pending' ? 'flex' : 'none';
    const reason = document.getElementById('product-reject-reason');
    if (reason) reason.value = '';

    document.getElementById('productModalOverlay')?.classList.add('open');
}

function closeProductModal() {
    document.getElementById('productModalOverlay')?.classList.remove('open');
    selectedProductId = null;
}

async function approveProduct() {
    if (!selectedProductId) return;
    const res = await API.adminProducts.updateStatus(selectedProductId, 'active');
    if (res.success) {
        showToast('Product approved.');
        closeProductModal();
        loadAdminProducts();
    } else {
        showToast(res.error || 'Failed to approve product.', true);
    }
}

async function rejectProduct() {
    if (!selectedProductId) return;
    const reason = document.getElementById('product-reject-reason')?.value.trim() || '';
    const res = await API.adminProducts.updateStatus(selectedProductId, 'rejected', reason);
    if (res.success) {
        showToast('Product rejected.');
        closeProductModal();
        loadAdminProducts();
    } else {
        showToast(res.error || 'Failed to reject product.', true);
    }
}
