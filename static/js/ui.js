/**
 * ui.js — Shared UI helpers
 * Used by: admin.js, seller.js, rider.js, buyer.js
 */

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, isError = false) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.style.background = isError ? '#c0392b' : '#1a1a3e';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// ── Modal ─────────────────────────────────────────────────────
function openModal(id) {
    document.getElementById(id)?.classList.add('open');
}

function closeModal(id) {
    document.getElementById(id)?.classList.remove('open');
}

// ── Popup ─────────────────────────────────────────────────────
function showPopup(icon, title, msg) {
    document.getElementById('popupIcon').textContent  = icon;
    document.getElementById('popupTitle').textContent = title;
    document.getElementById('popupMsg').textContent   = msg;
    document.getElementById('popupOverlay').classList.add('open');
}

function closePopup() {
    document.getElementById('popupOverlay')?.classList.remove('open');
}

// ── Formatters ────────────────────────────────────────────────
function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-PH', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

function formatCurrency(amount) {
    return '₱' + Number(amount || 0).toLocaleString('en-PH', {
        minimumFractionDigits: 2
    });
}

// ── File upload label ─────────────────────────────────────────
function showName(input, targetId) {
    const el = document.getElementById(targetId);
    if (el) el.textContent = input.files[0] ? '✅ ' + input.files[0].name : '';
}

// ── Mobile sidebar toggle ─────────────────────────────────────
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
