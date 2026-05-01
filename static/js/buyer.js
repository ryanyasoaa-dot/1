/**
 * buyer.js — All buyer page logic
 * Depends on: api.js
 */

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-PH', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

function formatCurrency(amount) {
    return '₱' + Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
}

// ── Orders ────────────────────────────────────────────────────
async function loadOrders() {
    const tbody = document.getElementById('ordersTable');
    if (!tbody) return;

    const data = await API.buyer.getOrders().catch(() => []);

    if (!data.length) {
        tbody.innerHTML = `<tr><td colspan="5">
            <div class="empty-orders">
                <div class="empty-icon">📦</div>
                <p>No orders yet. Start shopping!</p>
                <a href="/" class="btn-shop">Browse Products</a>
            </div>
        </td></tr>`;
        return;
    }

    tbody.innerHTML = data.map(o => `
        <tr>
            <td>#${(o.id || '').slice(0,8)}</td>
            <td>${o.store_name || '—'}</td>
            <td>${formatCurrency(o.total)}</td>
            <td><span class="badge badge-${o.status}">${o.status}</span></td>
            <td>${formatDate(o.created_at)}</td>
        </tr>
    `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('ordersTable')) loadOrders();
});
