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
let adminSalesChart  = null;
let adminStatusChart = null;
let _commissionRate  = 5;

async function loadDashboard() {
    // Load summary + commission in parallel
    const [summary, earnings] = await Promise.all([
        API.admin.getDashboard().catch(() => ({})),
        API.admin.getEarnings().catch(() => ({}))
    ]);

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('statUsers',      summary.total_users      ?? '—');
    set('statSellers',    summary.total_sellers    ?? '—');
    set('statRiders',     summary.total_riders     ?? '—');
    set('statOrders',     summary.total_orders     ?? '—');
    set('statRevenue',    formatCurrency(summary.total_revenue    || 0));
    set('statCommission', formatCurrency(summary.admin_commission || 0));

    // Commission banner
    _commissionRate = summary.commission_rate || 5;
    set('commissionTotal', formatCurrency(earnings.total_commission || 0));
    set('commissionToday', formatCurrency(earnings.today_commission || 0));
    set('commissionWeek',  formatCurrency(earnings.week_commission  || 0));
    set('commissionMonth', formatCurrency(earnings.month_commission || 0));
    const badge = document.getElementById('commissionRateBadge');
    if (badge) badge.textContent = `Rate: ${_commissionRate}%`;

    // Pre-fill rate inputs
    const rateInput = document.getElementById('commissionRateInput');
    if (rateInput) rateInput.value = _commissionRate;

    // Load commission settings for rider rate
    const cfg = await API.admin.getCommission().catch(() => ({}));
    const riderInput = document.getElementById('riderRateInput');
    if (riderInput) riderInput.value = cfg.rider_rate || 50;

    // Charts
    loadAdminSalesChart('daily');
    loadAdminStatusChart(summary.status_breakdown || {});

    // Recent orders
    loadAdminRecentOrders();

    // Pending applications
    const apps = await API.applications.getAll().catch(() => []);
    const pending = apps.filter(a => a.status === 'pending').slice(0, 5);
    const tbody = document.getElementById('recentApps');
    if (tbody) {
        if (!pending.length) {
            tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">✅</div>No pending applications.</div></td></tr>`;
        } else {
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
    }
}

async function loadAdminSalesChart(period = 'daily') {
    const res  = await API.admin.getSalesAnalytics(period).catch(() => ({ data: [] }));
    const data = res.data || [];
    const canvas = document.getElementById('adminSalesChart');
    if (!canvas) return;
    if (adminSalesChart) adminSalesChart.destroy();
    adminSalesChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: 'Revenue (₱)',
                data:  data.map(d => d.value),
                backgroundColor: 'rgba(26,26,62,.15)',
                borderColor: '#1a1a3e',
                borderWidth: 2,
                borderRadius: 6,
            }, {
                label: 'Orders',
                data:  data.map(d => d.orders),
                type:  'line',
                borderColor: '#FF2BAC',
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 4,
                yAxisID: 'orders',
            }]
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { position: 'top' } },
            scales: {
                y:      { beginAtZero: true, ticks: { callback: v => '₱' + v.toLocaleString() } },
                orders: { position: 'right', beginAtZero: true, grid: { drawOnChartArea: false } }
            }
        }
    });
}

function loadAdminStatusChart(breakdown) {
    const canvas = document.getElementById('adminStatusChart');
    if (!canvas) return;
    const labels = ['Pending', 'Processing', 'Ready', 'In Transit', 'Delivered'];
    const keys   = ['pending', 'processing', 'ready_for_pickup', 'in_transit', 'delivered'];
    const colors = ['#ffc107', '#17a2b8', '#fd7e14', '#6f42c1', '#28a745'];
    const values = keys.map(k => breakdown[k] || 0);
    if (adminStatusChart) adminStatusChart.destroy();
    adminStatusChart = new Chart(canvas, {
        type: 'doughnut',
        data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 2 }] },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });
    const legend = document.getElementById('statusLegend');
    if (legend) {
        legend.innerHTML = labels.map((l, i) => `
            <span style="margin-right:12px">
                <span style="background:${colors[i]};width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:4px"></span>
                ${l}: <strong>${values[i]}</strong>
            </span>
        `).join('');
    }
}

function changeAdminPeriod(period, btn) {
    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadAdminSalesChart(period);
}

async function loadAdminRecentOrders() {
    const tbody = document.getElementById('adminRecentOrders');
    if (!tbody) return;
    const data = await API.admin.getRecentOrders(10).catch(() => []);
    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">🛒</div>No orders yet.</div></td></tr>';
        return;
    }
    tbody.innerHTML = data.map(o => {
        const commission = (parseFloat(o.total_amount) * _commissionRate / 100).toFixed(2);
        return `
        <tr>
            <td>#${o.short_id}</td>
            <td>${o.buyer_name}</td>
            <td>${o.rider_name}</td>
            <td>${formatCurrency(o.total_amount)}</td>
            <td style="color:#28a745;font-weight:600">${o.status === 'delivered' ? formatCurrency(commission) : '—'}</td>
            <td><span class="badge badge-${o.status}">${o.status}</span></td>
            <td>${formatDate(o.created_at)}</td>
        </tr>`;
    }).join('');
}

async function saveCommissionRates() {
    const rate  = parseFloat(document.getElementById('commissionRateInput')?.value || 5);
    const rider = parseFloat(document.getElementById('riderRateInput')?.value || 50);
    if (rate < 1 || rate > 30) { showToast('Commission rate must be 1–30%.', true); return; }
    if (rider < 1)             { showToast('Rider rate must be at least ₱1.', true); return; }
    const res = await API.admin.setCommission({ commission_rate: rate, rider_rate: rider }).catch(() => ({ error: 'Network error.' }));
    if (res.success) {
        showToast('Rates saved successfully.');
        loadDashboard();
    } else {
        showToast(res.error || 'Failed to save rates.', true);
    }
}

function formatCurrency(amount) {
    return '₱' + Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
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

    // Organize images: separate general images from variant-specific images
    const images = p.product_images || [];
    const generalImages = images.filter(img => !img.variant_id);
    const variantImages = images.filter(img => img.variant_id);
    
    // Create a map of variant IDs to variant details for lookup
    const variantMap = {};
    (p.product_variants || []).forEach(v => {
        variantMap[v.id] = v;
    });

    // Display general product images
    const generalImagesEl = document.getElementById('product-modal-general-images');
    const generalImagesEmptyEl = document.getElementById('product-modal-general-images-empty');
    if (generalImagesEl) {
        if (generalImages.length > 0) {
            generalImagesEl.innerHTML = generalImages
                .map(img => `<img src="${img.image_url.startsWith('/') ? img.image_url : '/' + img.image_url}" alt="product image" title="General product image" style="width:100%;height:90px;object-fit:cover;border-radius:6px;border:2px solid #27ae60;cursor:pointer" onclick="this.style.borderColor=this.style.borderColor==='rgb(39, 174, 96)'?'#eee':'#27ae60'">`)
                .join('');
            if (generalImagesEmptyEl) generalImagesEmptyEl.style.display = 'none';
        } else {
            generalImagesEl.innerHTML = '';
            if (generalImagesEmptyEl) generalImagesEmptyEl.style.display = 'block';
        }
    }

    // Display variant-specific images
    const variantImagesEl = document.getElementById('product-modal-variant-images');
    const variantImagesEmptyEl = document.getElementById('product-modal-variant-images-empty');
    if (variantImagesEl) {
        if (variantImages.length > 0) {
            const variantImagesByVariantId = {};
            variantImages.forEach(img => {
                if (!variantImagesByVariantId[img.variant_id]) {
                    variantImagesByVariantId[img.variant_id] = [];
                }
                variantImagesByVariantId[img.variant_id].push(img);
            });
            
            variantImagesEl.innerHTML = Object.entries(variantImagesByVariantId)
                .map(([variantId, imgs]) => {
                    const variant = variantMap[variantId];
                    const variantLabel = variant 
                        ? `${variant.variant_type}: ${variant.value}`
                        : `Variant: ${variantId}`;
                    return `
                        <div style="margin-bottom:16px">
                            <div style="font-size:12px;font-weight:600;color:#333;margin-bottom:6px">🏷️ ${variantLabel}</div>
                            <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(90px, 1fr));gap:8px">
                                ${imgs.map(img => `<img src="${img.image_url.startsWith('/') ? img.image_url : '/' + img.image_url}" alt="variant image" title="Variant: ${variantLabel}" style="width:100%;height:90px;object-fit:cover;border-radius:6px;border:2px solid #3498db;cursor:pointer" onclick="this.style.borderColor=this.style.borderColor==='rgb(52, 152, 219)'?'#eee':'#3498db'">`).join('')}
                            </div>
                        </div>
                    `;
                })
                .join('');
            if (variantImagesEmptyEl) variantImagesEmptyEl.style.display = 'none';
        } else {
            variantImagesEl.innerHTML = '';
            if (variantImagesEmptyEl) variantImagesEmptyEl.style.display = 'block';
        }
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
