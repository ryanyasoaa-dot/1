/**
 * rider.js — All rider page logic
 * Depends on: api.js
 */

// ── Helpers ───────────────────────────────────────────────────
function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-PH', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

function formatCurrency(amount) {
    return '₱' + Number(amount || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
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

    if (document.getElementById('deliveriesTable')) loadDeliveries();
    if (document.getElementById('totalEarnings'))   loadEarnings();
});

// ── Deliveries ────────────────────────────────────────────────
async function loadDeliveries(filter = 'all') {
    const tbody = document.getElementById('deliveriesTable');
    if (!tbody) return;

    const data     = await API.rider.getDeliveries().catch(() => []);
    const filtered = filter === 'all' ? data : data.filter(d => d.status === filter);

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">🚚</div>No deliveries found.</div></td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(d => `
        <tr>
            <td>#${(d.id || '').slice(0,8)}</td>
            <td>${d.customer_name || '—'}</td>
            <td>${d.address       || '—'}</td>
            <td>${d.store_name    || '—'}</td>
            <td><span class="badge badge-${d.status}">${d.status}</span></td>
            <td class="actions">
                ${d.status === 'assigned'
                    ? `<button class="btn btn-approve" onclick="markDelivered('${d.id}')">Mark Delivered</button>`
                    : '—'
                }
            </td>
        </tr>
    `).join('');
}

async function markDelivered(id) {
    const res = await API.rider.updateStatus(id, 'delivered');
    if (res.success) {
        showToast('Marked as delivered!');
        loadDeliveries();
    } else {
        showToast(res.error || 'Failed.', true);
    }
}

function setFilterTab(el, callback, value) {
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    callback(value);
}

// ── Earnings ──────────────────────────────────────────────────
async function loadEarnings() {
    const data = await API.rider.getEarnings().catch(() => ({}));
    const set  = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('totalEarnings',  formatCurrency(data.total));
    set('pendingPayout',  formatCurrency(data.pending));
    set('releasedPayout', formatCurrency(data.released));
    set('totalDeliveries', data.deliveries ?? 0);
}
