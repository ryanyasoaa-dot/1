// Toggle password visibility
document.getElementById('togglePw').addEventListener('click', function () {
    const pw = document.getElementById('password');
    const isText = pw.type === 'text';
    pw.type = isText ? 'password' : 'text';
    this.textContent = isText ? '👁️' : '🙈';
});

// Popup helpers
function showPopup(icon, title, msg) {
    document.getElementById('popupIcon').textContent  = icon;
    document.getElementById('popupTitle').textContent = title;
    document.getElementById('popupMsg').textContent   = msg;
    document.getElementById('popupOverlay').classList.add('open');
}

function closePopup() {
    document.getElementById('popupOverlay').classList.remove('open');
}

// Login form submit
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled    = true;
    submitBtn.textContent = 'Signing in...';

    const res  = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email:    document.getElementById('email').value,
            password: document.getElementById('password').value,
        }),
    });

    const data = await res.json();

    if (res.ok) {
        window.location.href = data.redirect || '/';
    } else {
        submitBtn.disabled    = false;
        submitBtn.textContent = 'Sign In';

        const msg = data.error || 'Login failed.';
        if (msg.includes('pending')) {
            showPopup('⏳', 'Application Pending', msg);
        } else if (msg.includes('rejected')) {
            showPopup('❌', 'Application Rejected', msg);
        } else {
            showPopup('🔒', 'Login Failed', msg);
        }
    }
});
