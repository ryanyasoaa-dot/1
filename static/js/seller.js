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
    return '\u20b1' + Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
}

function formatDate(iso) {
    if (!iso) return '\u2014';
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
            <div class="empty-state"><div class="empty-icon">&#128230;</div>
            No products yet.
            <a href="/seller/products/add" style="color:var(--pink);font-weight:600">Add your first product</a>
            </div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => `
        <tr>
            <td>${p.name || '\u2014'}</td>
            <td>${formatCurrency(p.price)}</td>
            <td>${p.total_stock ?? 0}</td>
            <td>${p.sales ?? 0}</td>
            <td>
                <span class="badge badge-${p.status}">${p.status}</span>
                ${p.status === 'rejected' && p.reject_reason ? `<div style="font-size:11px;color:#e74c3c;margin-top:4px">Reason: ${p.reject_reason}</div>` : ''}
            </td>
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
        tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="empty-icon">&#128722;</div>No orders found.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(o => `
        <tr>
            <td>#${(o.id || '').slice(0,8)}</td>
            <td>${o.customer_name || '\u2014'}</td>
            <td>${o.items_count ?? (o.items ? o.items.length : 0)}</td>
            <td>${formatCurrency(o.total)}</td>
            <td><span class="badge badge-${o.status}">${o.status}</span></td>
            <td>${formatDate(o.created_at)}</td>
            <td style="display:flex;gap:6px;flex-wrap:wrap">
                <button class="btn btn-view" onclick="viewOrder('${o.id}')">View</button>
                ${o.status === 'pending' ? `<button class="btn btn-approve" onclick="updateOrderStatus('${o.id}','processing')">Process</button>` : ''}
                ${o.status === 'processing' ? `<button class="btn btn-view" onclick="updateOrderStatus('${o.id}','ready_for_pickup')">Ready for Pickup</button>` : ''}
                <button class="btn btn-msg" onclick="messageBuyer('${o.id}','${o.buyer_id || ''}','${(o.customer_name || '').replace(/'/g, '')}')">&#128172; Message</button>
            </td>
        </tr>
    `).join('');
}

function viewOrder(id) {
    console.log('View order:', id);
}

async function updateOrderStatus(id, status) {
    const res = await API.seller.updateOrderStatus(id, status).catch(() => ({ error: 'Network error.' }));
    if (res.success) {
        showToast('Order status updated.');
        if (document.getElementById('salesChart')) {
            loadDashboardStats();
            loadDashboardRecentOrders();
        } else {
            loadOrders();
        }
    } else {
        showToast(res.error || 'Failed to update order.', true);
    }
}

// ── Order Chat Panel ──────────────────────────────────────────
let _chatConvId    = null;
let _chatPollTimer = null;
let _chatLastMsgId = null;
let _ME_ID         = '';
const QUICK_MSG = 'Thank you for your order! We are currently processing your items. We will update you once it is ready for pickup.';

async function messageBuyer(orderId, buyerId, buyerName) {
    if (!buyerId) { showToast('Buyer information not available.', true); return; }
    const panel = document.getElementById('orderChatPanel');
    if (!panel) return;

    document.getElementById('chatPanelBuyerName').textContent = buyerName || 'Buyer';
    document.getElementById('chatPanelOrderId').textContent   = '#' + orderId.slice(0, 8);
    document.getElementById('chatPanelMessages').innerHTML    = '<div style="text-align:center;color:#adb5bd;padding:20px;font-size:13px">Loading...</div>';
    panel.classList.add('open');

    const res = await API.messages.quickMessage(buyerId, orderId, false).catch(() => null);
    if (!res || !res.conversation_id) { showToast('Could not open chat.', true); return; }
    _chatConvId = res.conversation_id;

    const qrBtn = document.getElementById('quickReplyBtn');
    if (qrBtn) qrBtn.style.display = res.already_sent ? 'none' : 'inline-flex';

    await loadChatPanelMessages();
    clearInterval(_chatPollTimer);
    _chatPollTimer = setInterval(pollChatPanel, 3000);
}

async function loadChatPanelMessages() {
    if (!_chatConvId) return;
    const msgs = await fetch(`/messages/api/conversations/${_chatConvId}/messages`).then(r => r.json()).catch(() => []);
    renderChatPanel(msgs);
    if (msgs.length) _chatLastMsgId = msgs[msgs.length - 1].id;
    scrollChatPanel();
}

async function pollChatPanel() {
    if (!_chatConvId || !_chatLastMsgId) return;
    const msgs = await fetch(`/messages/api/conversations/${_chatConvId}/messages?after=${_chatLastMsgId}`).then(r => r.json()).catch(() => []);
    if (msgs.length) {
        msgs.forEach(m => document.getElementById('chatPanelMessages').appendChild(buildChatBubble(m)));
        _chatLastMsgId = msgs[msgs.length - 1].id;
        scrollChatPanel();
    }
}

function renderChatPanel(msgs) {
    const container = document.getElementById('chatPanelMessages');
    if (!msgs.length) {
        container.innerHTML = '<div style="text-align:center;color:#adb5bd;padding:20px;font-size:13px">No messages yet. Say hello!</div>';
        return;
    }
    container.innerHTML = '';
    msgs.forEach(m => container.appendChild(buildChatBubble(m)));
}

function buildChatBubble(m) {
    const isSent = m.sender_id === _ME_ID;
    const div = document.createElement('div');
    div.style.cssText = `display:flex;flex-direction:column;align-items:${isSent ? 'flex-end' : 'flex-start'};margin-bottom:8px`;
    div.innerHTML = `
        <div style="max-width:75%;padding:9px 13px;
            border-radius:${isSent ? '14px 14px 3px 14px' : '14px 14px 14px 3px'};
            background:${isSent ? '#FF2BAC' : '#f0f2f5'};
            color:${isSent ? '#fff' : '#1a1a3e'};
            font-size:13px;line-height:1.4;word-break:break-word">${_escHtml(m.content)}</div>
        <div style="font-size:10px;color:#adb5bd;margin-top:3px">${_fmtTime(m.created_at)}</div>
    `;
    return div;
}

async function sendChatPanelMessage() {
    if (!_chatConvId) return;
    const input = document.getElementById('chatPanelInput');
    const content = (input.value || '').trim();
    if (!content) return;
    input.value = '';
    const res = await fetch(`/messages/api/conversations/${_chatConvId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _getCsrf() },
        body: JSON.stringify({ content })
    }).then(r => r.json()).catch(() => null);
    if (res && res.id) {
        document.getElementById('chatPanelMessages').appendChild(buildChatBubble(res));
        _chatLastMsgId = res.id;
        scrollChatPanel();
    }
}

async function sendQuickReply() {
    if (!_chatConvId) return;
    const btn = document.getElementById('quickReplyBtn');
    if (btn) btn.disabled = true;
    const res = await fetch(`/messages/api/conversations/${_chatConvId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _getCsrf() },
        body: JSON.stringify({ content: QUICK_MSG })
    }).then(r => r.json()).catch(() => null);
    if (res && res.id) {
        document.getElementById('chatPanelMessages').appendChild(buildChatBubble(res));
        _chatLastMsgId = res.id;
        scrollChatPanel();
        if (btn) btn.style.display = 'none';
        showToast('Welcome message sent!');
    } else {
        if (btn) btn.disabled = false;
        showToast('Failed to send.', true);
    }
}

function closeOrderChat() {
    clearInterval(_chatPollTimer);
    _chatConvId = _chatLastMsgId = null;
    document.getElementById('orderChatPanel')?.classList.remove('open');
}

function handleChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatPanelMessage(); }
}

function scrollChatPanel() {
    const el = document.getElementById('chatPanelMessages');
    if (el) el.scrollTop = el.scrollHeight;
}

function _escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _fmtTime(iso) {
    return iso ? new Date(iso).toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit' }) : '';
}

function _getCsrf() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

// ── Shipping ──────────────────────────────────────────────────
async function loadShipping(filter = 'all') {
    const tbody = document.getElementById('shippingTable');
    if (!tbody) return;

    const data     = await API.seller.getShipping().catch(() => []);
    const filtered = filter === 'all' ? data : data.filter(s => s.status === filter);

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">&#128666;</div>No active deliveries.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(s => `
        <tr>
            <td>#${(s.order_id || '').slice(0,8)}</td>
            <td>${s.customer_name || '\u2014'}</td>
            <td>${s.address || '\u2014'}</td>
            <td>${s.rider_name || 'Unassigned'}</td>
            <td><span class="badge badge-${s.status}">${s.status}</span></td>
            <td><button class="btn btn-view">Track</button></td>
        </tr>
    `).join('');
}

// ── Dashboard ─────────────────────────────────────────────────
let salesChart = null;

async function loadDashboardStats() {
    const res = await API.seller.getDashboardSummary().catch(() => ({}));
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('statRevenue',  formatCurrency(res.total_sales   || 0));
    set('statOrders',   res.total_orders   || 0);
    set('statProducts', res.products_listed || 0);
    set('statPending',  res.pending_orders  || 0);
    set('statToday',    formatCurrency(res.today_sales   || 0));
    set('statItems',    res.items_sold      || 0);
    loadStatusBreakdown(res.status_breakdown || {});
}

function loadStatusBreakdown(breakdown) {
    const el = document.getElementById('statusBreakdown');
    if (!el) return;
    const statuses = [
        { key: 'pending',          label: 'Pending',    color: '#ffc107' },
        { key: 'processing',       label: 'Processing', color: '#17a2b8' },
        { key: 'ready_for_pickup', label: 'Ready',      color: '#fd7e14' },
        { key: 'in_transit',       label: 'In Transit', color: '#6f42c1' },
        { key: 'delivered',        label: 'Delivered',  color: '#28a745' },
    ];
    el.innerHTML = statuses.map(s => `
        <div class="status-item status-${s.key}">
            <div class="status-count" style="color:${s.color}">${breakdown[s.key] || 0}</div>
            <div class="status-label">${s.label}</div>
        </div>
    `).join('');
}

async function loadSalesChart(period = 'daily') {
    const res = await API.seller.getSalesAnalytics(period).catch(() => ({ data: [] }));
    const data = res.data || [];
    const canvas = document.getElementById('salesChart');
    if (!canvas) return;

    if (salesChart) salesChart.destroy();
    salesChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: 'Sales (\u20b1)',
                data: data.map(d => d.value),
                backgroundColor: 'rgba(255, 43, 172, 0.15)',
                borderColor: '#FF2BAC',
                borderWidth: 2,
                borderRadius: 6,
                tension: 0.4,
            }, {
                label: 'Orders',
                data: data.map(d => d.orders),
                type: 'line',
                borderColor: '#1a1a3e',
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
                y:      { beginAtZero: true, ticks: { callback: v => '\u20b1' + v.toLocaleString() } },
                orders: { position: 'right', beginAtZero: true, grid: { drawOnChartArea: false } }
            }
        }
    });
}

function changePeriod(period, btn) {
    document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadSalesChart(period);
}

async function loadTopProducts() {
    const el = document.getElementById('topProducts');
    if (!el) return;
    const data = await API.seller.getTopProducts(5).catch(() => []);
    if (!data.length) {
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128230;</div>No sales data yet.</div>';
        return;
    }
    el.innerHTML = data.map((p, i) => `
        <div class="product-item">
            <div>
                <span style="color:#999;font-size:12px;margin-right:8px">#${i + 1}</span>
                <span class="product-name">${p.name}</span>
            </div>
            <div class="product-stats">
                <div class="product-revenue">${formatCurrency(p.total_revenue)}</div>
                <div class="product-quantity">${p.quantity_sold} sold</div>
            </div>
        </div>
    `).join('');
}

async function loadLowStock() {
    const el = document.getElementById('lowStockAlert');
    if (!el) return;
    const data = await API.seller.getLowStock(10).catch(() => []);
    if (!data.length) {
        el.innerHTML = '<div style="color:#28a745;text-align:center;padding:20px">&#10003; All products have sufficient stock.</div>';
        return;
    }
    el.innerHTML = data.map(p => `
        <div class="low-stock-item">
            <span style="font-size:13px;font-weight:500">${p.name}</span>
            <span class="stock-badge" style="background:${p.status === 'critical' ? '#dc3545' : p.status === 'low' ? '#fd7e14' : '#ffc107'}">
                ${p.current_stock === 0 ? 'Out of Stock' : p.current_stock + ' left'}
            </span>
        </div>
    `).join('');
}

async function loadDashboardRecentOrders() {
    const tbody = document.getElementById('ordersTable');
    if (!tbody) return;
    const data = await API.seller.getRecentOrders(10).catch(() => []);
    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="empty-icon">&#128722;</div>No orders yet.</div></td></tr>';
        return;
    }
    tbody.innerHTML = data.map(o => `
        <tr>
            <td>#${(o.order_id || '').slice(0, 8)}</td>
            <td>${o.customer_name || '\u2014'}</td>
            <td>${o.items_count || 0}</td>
            <td>${formatCurrency(o.total_amount)}</td>
            <td><span class="badge badge-${o.status}">${o.status}</span></td>
            <td>${formatDate(o.created_at)}</td>
            <td style="display:flex;gap:6px;flex-wrap:wrap">
                ${o.status === 'pending'    ? `<button class="btn btn-approve" onclick="updateOrderStatus('${o.id}','processing')">Process</button>` : ''}
                ${o.status === 'processing' ? `<button class="btn btn-view" onclick="updateOrderStatus('${o.id}','ready_for_pickup')">Ready</button>` : ''}
                <button class="btn btn-msg" onclick="messageBuyer('${o.id}','${o.buyer_id || ''}','${(o.customer_name || '').replace(/'/g, '')}')">&#128172; Message</button>
            </td>
        </tr>
    `).join('');
}

// ── Earnings ──────────────────────────────────────────────────
async function loadEarnings() {
    const data = await API.seller.getEarnings().catch(() => ({}));
    const set  = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('totalEarnings',  formatCurrency(data.total_revenue || 0));
    set('pendingPayout',  formatCurrency(data.pending || 0));
    set('releasedPayout', formatCurrency(data.released || 0));
    set('monthEarnings',  formatCurrency(data.month_revenue || 0));
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
        if (el) el.textContent = `&#128205; Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
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
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">&#11088;</div>No reviews yet.</div>`;
        return;
    }

    container.innerHTML = filtered.map(r => `
        <div style="padding:16px;border-bottom:1px solid var(--border)">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <strong style="font-size:13px">${r.customer_name || 'Anonymous'}</strong>
                <span class="stars">${'\u2605'.repeat(r.rating)}${'\u2606'.repeat(5 - r.rating)}</span>
            </div>
            <p style="font-size:13px;color:var(--gray)">${r.comment || ''}</p>
            <div style="font-size:11px;color:#999;margin-top:4px">${formatDate(r.created_at)}</div>
        </div>
    `).join('');
}

// ── Page init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('productsTable')) loadProducts();
    if (document.getElementById('shippingTable')) loadShipping();
    if (document.getElementById('reviewsList'))   loadReviews();
    if (document.getElementById('storeMap'))      initStoreMap();
    if (document.getElementById('totalEarnings')) loadEarnings();

    if (document.getElementById('salesChart')) {
        loadDashboardStats();
        loadSalesChart('daily');
        loadTopProducts();
        loadLowStock();
        loadDashboardRecentOrders();
    } else {
        if (document.getElementById('ordersTable')) loadOrders();
    }

    const storeForm = document.getElementById('storeForm');
    if (storeForm) storeForm.addEventListener('submit', saveStore);
});
