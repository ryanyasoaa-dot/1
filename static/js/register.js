// ── Step navigation ───────────────────────────────────────────
let currentStep = 1;

function goToStep(step) {
    if (step === 2 && !validateStep1()) return;
    if (step === 3 && !validateStep2()) return;

    // Hide all steps
    document.querySelectorAll('.step-content').forEach(s => s.style.display = 'none');
    document.getElementById(`step${step}`).style.display = 'block';

    // Update indicators
    for (let i = 1; i <= 3; i++) {
        const ind  = document.getElementById(`ind${i}`);
        const circ = ind.querySelector('.step-circle');
        ind.classList.remove('active', 'done');
        if (i < step)  { ind.classList.add('done');   circ.textContent = '✓'; }
        if (i === step) { ind.classList.add('active'); circ.textContent = i;  }
        if (i > step)   circ.textContent = i;
    }

    // Update step lines
    document.querySelectorAll('.step-line').forEach((line, idx) => {
        line.classList.toggle('done', idx + 1 < step);
    });

    // Init PSGC map when step 3 is shown
    if (step === 3 && !window._psgcInited) {
        initPSGC();
        window._psgcInited = true;
    }

    // Show correct doc section on step 2
    if (step === 2) showDocSection();

    currentStep = step;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Show correct doc section based on role ────────────────────
function showDocSection() {
    const role = document.querySelector('input[name="role"]:checked').value;
    document.getElementById('buyerDocs').style.display  = role === 'buyer'  ? 'block' : 'none';
    document.getElementById('sellerDocs').style.display = role === 'seller' ? 'block' : 'none';
    document.getElementById('riderDocs').style.display  = role === 'rider'  ? 'block' : 'none';
}

// ── Validation ────────────────────────────────────────────────
function showError(msg) {
    const el = document.getElementById('errorMsg');
    el.textContent   = msg;
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 4000);
}

function validateStep1() {
    const g = (id) => document.getElementById(id)?.value.trim();

    if (!g('first_name'))  { showError('First name is required.'); return false; }
    if (!g('last_name'))   { showError('Last name is required.'); return false; }
    if (!g('email'))       { showError('Email is required.'); return false; }
    if (!g('phone'))       { showError('Phone number is required.'); return false; }

    const pw  = document.getElementById('password').value;
    const cpw = document.getElementById('confirm_password').value;

    if (pw.length < 8)  { showError('Password must be at least 8 characters.'); return false; }
    if (pw !== cpw)     { showError('Passwords do not match.'); return false; }

    return true;
}

function validateStep2() {
    const role = document.querySelector('input[name="role"]:checked').value;

    if (role === 'buyer') {
        if (!document.getElementById('buyer_valid_id')?.files[0]) {
            showError('Please upload a valid ID.'); return false;
        }
    }

    if (role === 'seller') {
        if (!document.getElementById('store_name')?.value.trim()) {
            showError('Store name is required.'); return false;
        }
        const category = document.querySelector('input[name="store_category"]:checked');
        if (!category) {
            showError('Please select a store category.'); return false;
        }
    }

    if (role === 'rider') {
        if (!document.getElementById('license_number')?.value.trim()) {
            showError('License number is required.'); return false;
        }
    }

    return true;
}

// ── Password strength ─────────────────────────────────────────
const pwInput = document.getElementById('password');
const fill    = document.getElementById('strengthFill');
const text    = document.getElementById('strengthText');
const levels  = [
    { label: '',          color: '',        w: '0%'   },
    { label: 'Weak',      color: '#e74c3c', w: '25%'  },
    { label: 'Fair',      color: '#e67e22', w: '50%'  },
    { label: 'Good',      color: '#f1c40f', w: '75%'  },
    { label: 'Strong 💪', color: '#2ecc71', w: '100%' },
];

pwInput.addEventListener('input', () => {
    const v = pwInput.value;
    let score = 0;
    if (v.length >= 8)          score++;
    if (/[A-Z]/.test(v))        score++;
    if (/[0-9]/.test(v))        score++;
    if (/[^A-Za-z0-9]/.test(v)) score++;
    const l = v ? levels[score] : levels[0];
    fill.style.width      = l.w;
    fill.style.background = l.color;
    text.textContent      = l.label;
    text.style.color      = l.color;
});

// Confirm password match indicator
document.getElementById('confirm_password').addEventListener('input', function () {
    const ct = document.getElementById('confirmText');
    if (!this.value) { ct.textContent = ''; return; }
    const match = this.value === pwInput.value;
    ct.textContent = match ? '✅ Passwords match' : '❌ Passwords do not match';
    ct.style.color = match ? '#2ecc71' : '#e74c3c';
});

// Password toggles
document.getElementById('pwToggle').addEventListener('click', function () {
    const isText = pwInput.type === 'text';
    pwInput.type     = isText ? 'password' : 'text';
    this.textContent = isText ? '👁️' : '🙈';
});

document.getElementById('pwToggle2').addEventListener('click', function () {
    const cpw = document.getElementById('confirm_password');
    const isText = cpw.type === 'text';
    cpw.type         = isText ? 'password' : 'text';
    this.textContent = isText ? '👁️' : '🙈';
});

// ── File upload label ─────────────────────────────────────────
function showName(input, targetId) {
    document.getElementById(targetId).textContent = input.files[0] ? '✅ ' + input.files[0].name : '';
}

// ── Submit ────────────────────────────────────────────────────
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorMsg   = document.getElementById('errorMsg');
    const successMsg = document.getElementById('successMsg');
    const btn        = document.getElementById('submitBtn');
    const role       = document.querySelector('input[name="role"]:checked').value;
    const g          = (id) => document.getElementById(id);
    const addr       = getPSGCValues();

    errorMsg.style.display   = 'none';
    successMsg.style.display = 'none';
    btn.disabled    = true;
    btn.textContent = 'Submitting...';

    const fd = new FormData();
    fd.append('first_name',  g('first_name').value.trim());
    fd.append('middle_name', g('middle_name')?.value.trim() || '');
    fd.append('last_name',   g('last_name').value.trim());
    fd.append('email',       g('email').value.trim());
    fd.append('phone',       g('phone').value.trim());
    fd.append('password',    g('password').value);
    fd.append('role',        role);
    fd.append('region',      addr.region);
    fd.append('province',    addr.province);
    fd.append('city',        addr.city);
    fd.append('barangay',    addr.barangay);
    fd.append('street',      addr.street);
    fd.append('zip_code',    addr.zip_code);
    fd.append('latitude',    addr.latitude  || '');
    fd.append('longitude',   addr.longitude || '');

    if (role === 'buyer') {
        const buyerId = g('buyer_valid_id').files[0];
        if (buyerId) fd.append('valid_id', buyerId);
    } else if (role === 'seller') {
        fd.append('store_name',        g('store_name').value.trim());
        fd.append('store_description', g('store_description').value.trim());
        const category = document.querySelector('input[name="store_category"]:checked');
        if (category) fd.append('store_category', category.value);
        const validId = g('valid_id').files[0];
        const bp      = g('business_permit').files[0];
        const dti     = g('dti_sec').files[0];
        if (validId) fd.append('valid_id', validId);
        if (bp)      fd.append('business_permit', bp);
        if (dti)     fd.append('dti_or_sec', dti);
    }
    
    if (role === 'rider') {
        fd.append('vehicle_type',   g('vehicle_type').value.trim());
        fd.append('license_number', g('license_number').value.trim());
        const dl  = g('driver_license').files[0];
        const vid = g('rider_valid_id').files[0];
        if (dl)  fd.append('driver_license', dl);
        if (vid) fd.append('valid_id', vid);
    }

    try {
        const res  = await fetch('/api/register', { method: 'POST', body: fd });
        const data = await res.json();

        if (res.ok) {
            successMsg.textContent   = data.message;
            successMsg.style.display = 'block';
            document.getElementById('registerForm').reset();
            fill.style.width = '0'; text.textContent = '';
            setTimeout(() => window.location.href = '/login', 3000);
        } else {
            errorMsg.textContent   = data.error || 'Something went wrong.';
            errorMsg.style.display = 'block';
        }
    } catch {
        errorMsg.textContent   = 'Network error. Please try again.';
        errorMsg.style.display = 'block';
    }

    btn.disabled    = false;
    btn.textContent = 'Create Account';
});
