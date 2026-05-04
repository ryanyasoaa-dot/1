/**
 * rider.js — All rider page logic with map integration
 * Depends on: api.js, Leaflet
 */

// Global map variables
let deliveryMap = null;
let pickupMarker = null;
let deliveryMarker = null;
let routeLine = null;
let currentDeliveryId = null;
let allMarkers = []; // Array to store all markers for multi-order view
let allRoutes = []; // Array to store all route lines for multi-order view
let isMultiOrderView = false; // Flag to track if showing multiple orders

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

    if (document.getElementById('deliveriesTable')) {
        loadDeliveries();
        initializeMap();
    }
    if (document.getElementById('riderRecentDeliveries')) loadRiderDashboard();
    if (document.getElementById('totalEarnings'))         loadEarnings();
});

// ── Map Integration ───────────────────────────────────────────
function initializeMap() {
    const mapElement = document.getElementById('deliveryMap');
    if (!mapElement || typeof L === 'undefined') return;

    // Initialize map centered on Philippines
    deliveryMap = L.map('deliveryMap').setView([12.8797, 121.7740], 6);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(deliveryMap);
}

function showDeliveryRoute(orderId) {
    if (!deliveryMap) {
        initializeMap();
        if (!deliveryMap) return;
    }

    currentDeliveryId = orderId;
    const mapContainer = document.getElementById('mapContainer');
    const mapTitle = document.getElementById('mapTitle');
    
    mapContainer.style.display = 'block';
    mapTitle.textContent = `Delivery Route - Order #${orderId.slice(0, 8)}`;

    // Clear existing markers and route
    if (pickupMarker) deliveryMap.removeLayer(pickupMarker);
    if (deliveryMarker) deliveryMap.removeLayer(deliveryMarker);
    if (routeLine) deliveryMap.removeLayer(routeLine);

    // Fetch location data
    API.rider.getLocations(orderId)
        .then(data => {
            const pickup = data.pickup_location;
            const delivery = data.delivery_location;

            // Update address displays
            document.getElementById('pickupAddress').textContent = pickup.formatted_address;
            document.getElementById('deliveryAddress').textContent = delivery.formatted_address;

            // Add markers if coordinates are available
            if (pickup.latitude && pickup.longitude) {
                pickupMarker = L.marker([pickup.latitude, pickup.longitude], {
                    icon: L.divIcon({
                        className: 'custom-marker pickup-marker-icon',
                        html: '<div style="background:#007bff;color:white;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:16px;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3)">📦</div>',
                        iconSize: [30, 30],
                        iconAnchor: [15, 15]
                    })
                }).addTo(deliveryMap);
                
                pickupMarker.bindPopup(`
                    <div style="text-align:center;">
                        <strong>📦 Pickup Location</strong><br>
                        <small>${pickup.formatted_address}</small>
                    </div>
                `);
            }

            if (delivery.latitude && delivery.longitude) {
                deliveryMarker = L.marker([delivery.latitude, delivery.longitude], {
                    icon: L.divIcon({
                        className: 'custom-marker delivery-marker-icon',
                        html: '<div style="background:#dc3545;color:white;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:16px;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3)">🎯</div>',
                        iconSize: [30, 30],
                        iconAnchor: [15, 15]
                    })
                }).addTo(deliveryMap);
                
                deliveryMarker.bindPopup(`
                    <div style="text-align:center;">
                        <strong>🎯 Delivery Location</strong><br>
                        <small>${delivery.formatted_address}</small>
                    </div>
                `);
            }

            // Draw route and calculate distance if both coordinates exist
            if (pickup.latitude && pickup.longitude && delivery.latitude && delivery.longitude) {
                const pickupLatLng = [pickup.latitude, pickup.longitude];
                const deliveryLatLng = [delivery.latitude, delivery.longitude];
                
                // Draw route line
                routeLine = L.polyline([pickupLatLng, deliveryLatLng], {
                    color: '#28a745',
                    weight: 4,
                    opacity: 0.7,
                    dashArray: '10, 10'
                }).addTo(deliveryMap);
                
                // Calculate and display distance
                const distance = calculateDistance(pickup.latitude, pickup.longitude, delivery.latitude, delivery.longitude);
                document.getElementById('routeDistance').textContent = `Distance: ${distance.toFixed(2)} km`;
                
                // Fit map to show both markers
                const group = new L.featureGroup([pickupMarker, deliveryMarker]);
                deliveryMap.fitBounds(group.getBounds().pad(0.1));
            } else {
                // If coordinates missing, show message
                let missingInfo = [];
                if (!pickup.latitude || !pickup.longitude) missingInfo.push('pickup location');
                if (!delivery.latitude || !delivery.longitude) missingInfo.push('delivery location');
                
                document.getElementById('routeDistance').textContent = `Missing coordinates for ${missingInfo.join(' and ')}`;
                
                // Center on available location or default
                if (pickup.latitude && pickup.longitude) {
                    deliveryMap.setView([pickup.latitude, pickup.longitude], 15);
                } else if (delivery.latitude && delivery.longitude) {
                    deliveryMap.setView([delivery.latitude, delivery.longitude], 15);
                }
            }

            // Refresh map size
            setTimeout(() => {
                deliveryMap.invalidateSize();
            }, 100);
        })
        .catch(error => {
            console.error('Error loading delivery locations:', error);
            document.getElementById('pickupAddress').textContent = 'Error loading pickup address';
            document.getElementById('deliveryAddress').textContent = 'Error loading delivery address';
            document.getElementById('routeDistance').textContent = 'Error calculating distance';
        });
}

function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function hideMap() {
    const mapContainer = document.getElementById('mapContainer');
    mapContainer.style.display = 'none';
    currentDeliveryId = null;
    clearMultiOrderView();
}

function clearMultiOrderView() {
    // Clear all markers and routes from multi-order view
    allMarkers.forEach(marker => {
        if (deliveryMap && marker) deliveryMap.removeLayer(marker);
    });
    allRoutes.forEach(route => {
        if (deliveryMap && route) deliveryMap.removeLayer(route);
    });
    allMarkers = [];
    allRoutes = [];
    isMultiOrderView = false;
}

async function showAllOrdersMap() {
    if (!deliveryMap) {
        initializeMap();
        if (!deliveryMap) return;
    }

    const mapContainer = document.getElementById('mapContainer');
    const mapTitle = document.getElementById('mapTitle');
    
    mapContainer.style.display = 'block';
    mapTitle.textContent = 'All Active Deliveries';
    
    // Clear existing markers and routes
    clearMultiOrderView();
    isMultiOrderView = true;

    try {
        // Get all assigned orders for this rider
        const data = await API.rider.getDeliveries().catch(() => []);
        const assignedOrders = data.filter(d => d.status === 'in_transit');
        
        if (assignedOrders.length === 0) {
            document.getElementById('pickupAddress').textContent = 'No active deliveries found';
            document.getElementById('deliveryAddress').textContent = 'No active deliveries found';
            document.getElementById('routeDistance').textContent = 'No active deliveries';
            return;
        }

        let bounds = [];
        let totalDistance = 0;
        let pickupAddresses = [];
        let deliveryAddresses = [];

        // Add markers for each order
        for (const order of assignedOrders) {
            const pickupLat = order.pickup_latitude;
            const pickupLng = order.pickup_longitude;
            const deliveryLat = order.delivery_latitude;
            const deliveryLng = order.delivery_longitude;

            // Add pickup marker
            if (pickupLat && pickupLng) {
                const pickupMarker = L.marker([pickupLat, pickupLng], {
                    icon: L.divIcon({
                        className: 'custom-marker pickup-marker-icon',
                        html: '<div style="background:#007bff;color:white;border-radius:50%;width:25px;height:25px;display:flex;align-items:center;justify-content:center;font-size:12px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)">📦</div>',
                        iconSize: [25, 25],
                        iconAnchor: [12, 12]
                    })
                }).addTo(deliveryMap);
                
                pickupMarker.bindPopup(`
                    <div style="text-align:center;">
                        <strong>📦 Pickup</strong><br>
                        <small>Order #${(order.id || '').slice(0,8)}</small><br>
                        <small>${order.pickup_address || 'Address not available'}</small>
                    </div>
                `);
                
                allMarkers.push(pickupMarker);
                bounds.push([pickupLat, pickupLng]);
                pickupAddresses.push(order.pickup_address || 'Address not available');
            }

            // Add delivery marker
            if (deliveryLat && deliveryLng) {
                const deliveryMarker = L.marker([deliveryLat, deliveryLng], {
                    icon: L.divIcon({
                        className: 'custom-marker delivery-marker-icon',
                        html: '<div style="background:#dc3545;color:white;border-radius:50%;width:25px;height:25px;display:flex;align-items:center;justify-content:center;font-size:12px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3)">🎯</div>',
                        iconSize: [25, 25],
                        iconAnchor: [12, 12]
                    })
                }).addTo(deliveryMap);
                
                deliveryMarker.bindPopup(`
                    <div style="text-align:center;">
                        <strong>🎯 Delivery</strong><br>
                        <small>Order #${(order.id || '').slice(0,8)}</small><br>
                        <small>${order.address || 'Address not available'}</small>
                    </div>
                `);
                
                allMarkers.push(deliveryMarker);
                bounds.push([deliveryLat, deliveryLng]);
                deliveryAddresses.push(order.address || 'Address not available');
            }

            // Draw route line if both coordinates exist
            if (pickupLat && pickupLng && deliveryLat && deliveryLng) {
                const routeLine = L.polyline([[pickupLat, pickupLng], [deliveryLat, deliveryLng]], {
                    color: '#28a745',
                    weight: 3,
                    opacity: 0.6,
                    dashArray: '5, 5'
                }).addTo(deliveryMap);
                
                allRoutes.push(routeLine);
                
                // Calculate distance
                const distance = calculateDistance(pickupLat, pickupLng, deliveryLat, deliveryLng);
                totalDistance += distance;
            }
        }

        // Update map display
        if (bounds.length > 0) {
            // Fit map to show all markers
            const group = new L.featureGroup(allMarkers);
            deliveryMap.fitBounds(group.getBounds().pad(0.15));
            
            // Update address displays
            document.getElementById('pickupAddress').textContent = 
                `${pickupAddresses.length} pickup locations:\n${pickupAddresses.slice(0, 3).join('\n')}${pickupAddresses.length > 3 ? '\n...' : ''}`;
            document.getElementById('deliveryAddress').textContent = 
                `${deliveryAddresses.length} delivery locations:\n${deliveryAddresses.slice(0, 3).join('\n')}${deliveryAddresses.length > 3 ? '\n...' : ''}`;
            document.getElementById('routeDistance').textContent = 
                `${assignedOrders.length} active deliveries • Total distance: ${totalDistance.toFixed(2)} km`;
        } else {
            document.getElementById('pickupAddress').textContent = 'No coordinates available';
            document.getElementById('deliveryAddress').textContent = 'No coordinates available';
            document.getElementById('routeDistance').textContent = 'No coordinates available';
        }

        // Refresh map size
        setTimeout(() => {
            deliveryMap.invalidateSize();
        }, 100);

    } catch (error) {
        console.error('Error loading all deliveries:', error);
        document.getElementById('pickupAddress').textContent = 'Error loading deliveries';
        document.getElementById('deliveryAddress').textContent = 'Error loading deliveries';
        document.getElementById('routeDistance').textContent = 'Error loading deliveries';
    }
}
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

    tbody.innerHTML = filtered.map(d => {
        const hasCoordinates = (d.pickup_latitude && d.pickup_longitude) || (d.delivery_latitude && d.delivery_longitude);
        const mapButton = hasCoordinates 
            ? `<button class="btn btn-view" onclick="showDeliveryRoute('${d.id}')" style="margin-right:4px;">📍 Map</button>`
            : '';
        
        return `
            <tr>
                <td>#${(d.id || '').slice(0,8)}</td>
                <td>${d.customer_name || '—'}</td>
                <td>${d.address       || '—'}</td>
                <td>${d.store_name    || '—'}</td>
                <td><span class="badge badge-${d.status}">${d.status}</span></td>
                <td class="actions">
                    ${mapButton}
                    ${d.status === 'ready_for_pickup'
                        ? `<button class="btn btn-view" onclick="acceptDelivery('${d.id}')">Accept</button>`
                        : d.status === 'in_transit'
                        ? `<button class="btn btn-approve" onclick="markDelivered('${d.id}')">Mark Delivered</button>`
                        : '—'}
                </td>
            </tr>
        `;
    }).join('');
}

async function acceptDelivery(id) {
    const res = await API.rider.acceptDelivery(id).catch(() => ({ error: 'Network error.' }));
    if (res.success) {
        showToast('Delivery accepted. Status set to in_transit.');
        loadDeliveries();
    } else {
        showToast(res.error || 'Failed.', true);
    }
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

// ── Rider Dashboard ───────────────────────────────────────────
let riderEarningsChart = null;

async function loadRiderDashboard() {
    const [summary, earningsData] = await Promise.all([
        API.rider.getDashboard().catch(() => ({})),
        API.rider.getEarnings().catch(() => ({}))
    ]);

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('statTotal',     summary.total_deliveries     || 0);
    set('statCompleted', summary.completed_deliveries || 0);
    set('statActive',    summary.active_deliveries    || 0);
    set('statEarnings',  formatCurrency(summary.total_earnings || 0));
    set('earningsBig',   formatCurrency(summary.total_earnings || 0));
    set('earningsToday', formatCurrency(summary.today_earnings || 0));
    set('earningsWeek',  formatCurrency(summary.week_earnings  || 0));
    set('earningsMonth', formatCurrency(summary.month_earnings || 0));
    const rateLabel = document.getElementById('rateLabel');
    if (rateLabel) rateLabel.textContent = `₱${summary.rate_per_delivery || 50} per delivery`;

    const chart  = earningsData.chart || [];
    const canvas = document.getElementById('riderEarningsChart');
    if (canvas) {
        if (riderEarningsChart) riderEarningsChart.destroy();
        riderEarningsChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: chart.map(d => d.label),
                datasets: [{ label: 'Earnings (₱)', data: chart.map(d => d.value), backgroundColor: 'rgba(26,26,62,.15)', borderColor: '#1a1a3e', borderWidth: 2, borderRadius: 6 }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => '₱' + v } } } }
        });
    }

    const tbody  = document.getElementById('riderRecentDeliveries');
    if (tbody) {
        const history = (earningsData.history || []).slice(0, 10);
        if (!history.length) {
            tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">🚚</div>No deliveries yet.</div></td></tr>';
        } else {
            tbody.innerHTML = history.map(h => `
                <tr>
                    <td>#${h.order_id}</td>
                    <td>—</td>
                    <td>—</td>
                    <td style="color:#28a745;font-weight:600">${formatCurrency(h.amount)}</td>
                    <td><span class="badge badge-delivered">delivered</span></td>
                </tr>
            `).join('');
        }
    }
}

// ── Earnings page ─────────────────────────────────────────────
let earningsPageChart = null;

async function loadEarnings() {
    const data = await API.rider.getEarnings().catch(() => ({}));
    const set  = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('totalEarnings',  formatCurrency(data.total  || 0));
    set('monthEarnings',  formatCurrency(data.month  || 0));
    set('weekEarnings',   formatCurrency(data.week   || 0));
    set('totalDeliveries', data.deliveries ?? 0);

    const chart  = data.chart || [];
    const canvas = document.getElementById('earningsChart');
    if (canvas) {
        if (earningsPageChart) earningsPageChart.destroy();
        earningsPageChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: chart.map(d => d.label),
                datasets: [{ label: 'Earnings (₱)', data: chart.map(d => d.value), backgroundColor: 'rgba(26,26,62,.15)', borderColor: '#1a1a3e', borderWidth: 2, borderRadius: 6 }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => '₱' + v } } } }
        });
    }

    const tbody = document.getElementById('earningsHistory');
    if (tbody) {
        const history = data.history || [];
        if (!history.length) {
            tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state"><div class="empty-icon">💰</div>No earnings yet.</div></td></tr>';
        } else {
            tbody.innerHTML = history.map(h => `
                <tr>
                    <td>${formatDate(h.created_at)}</td>
                    <td>#${h.order_id}</td>
                    <td>${formatCurrency(h.order_total)}</td>
                    <td style="color:#28a745;font-weight:600">${formatCurrency(h.amount)}</td>
                </tr>
            `).join('');
        }
    }
}
