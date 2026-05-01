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

    set('modal-name',     a.full_name);
    set('modal-email',    a.email);
    set('modal-phone',    a.phone);
    set('modal-role',     a.role);
    set('modal-status',   a.status);
    set('modal-date',     formatDate(a.created_at));
    set('modal-region',   a.region);
    set('modal-city',     a.city);
    set('modal-barangay', a.barangay);
    set('modal-street',   a.street);
    set('modal-zip',      a.zip_code);
    set('modal-lat',      a.latitude);
    set('modal-lng',      a.longitude);

    document.getElementById('seller-row').style.display = a.role === 'seller' ? 'block' : 'none';
    document.getElementById('rider-row').style.display  = a.role === 'rider'  ? 'block' : 'none';

    if (a.role === 'seller') { set('modal-store', a.store_name); set('modal-desc', a.store_description); }
    if (a.role === 'rider')  { set('modal-vehicle', a.vehicle_type); set('modal-license', a.license_number); }

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
