/**
 * psgc.js — PSGC cascading dropdowns + geolocation + Leaflet map
 * Reusable for: register, checkout, address_book
 *
 * Usage: call initPSGC(config) with element IDs
 */

const PSGC_BASE = 'https://psgc.gitlab.io/api';

// Geocoding cache for PSGC → coordinates
const PSGC_GEO_CACHE = new Map();

// Track whether user has manually set the pin
let userHasSetPin = false;

// ── Init ─────────────────────────────────────────────────────
function initPSGC(config = {}) {
    const ids = {
        region:    config.region    || 'addrRegion',
        province:  config.province  || 'addrProvince',
        city:      config.city      || 'addrCity',
        barangay:  config.barangay  || 'addrBarangay',
        street:    config.street    || 'addrStreet',
        zip:       config.zip       || 'addrZip',
        latitude:  config.latitude  || 'addrLatitude',
        longitude: config.longitude || 'addrLongitude',
        mapEl:     config.mapEl     || 'psgcMap',
        coordsEl:  config.coordsEl  || 'addrCoordsDisplay',
        geoBtn:    config.geoBtn    || 'btnGeolocate',
        hintEl:    config.hintEl    || 'mapHint',
        statusEl:  config.statusEl  || 'pinStatus',
        instrEl:   config.instrEl   || 'mapInstructionText',
    };

    loadRegions(ids);
    setupCascade(ids);
    initMap(ids);
    setupGeolocation(ids);
}

// ── Helpers ───────────────────────────────────────────────────
function getEl(id) { return document.getElementById(id); }

function setLoading(selectId, loading) {
    const wrapper = getEl(selectId)?.parentElement;
    if (wrapper) wrapper.classList.toggle('select-loading', loading);
}

function setMapLoading(loading) {
    const mapEl = getEl('psgcMap');
    if (mapEl) mapEl.classList.toggle('map-loading', loading);
}

function populateSelect(selectId, items, placeholder) {
    const el = getEl(selectId);
    if (!el) return;
    el.innerHTML = `<option value="">${placeholder}</option>`;
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.code;
        opt.textContent = item.name;
        el.appendChild(opt);
    });
    el.disabled = items.length === 0;
}

function resetSelect(selectId, placeholder) {
    const el = getEl(selectId);
    if (!el) return;
    el.innerHTML = `<option value="">${placeholder}</option>`;
    el.disabled = true;
}

function updatePinStatus(ids, isSet, message) {
    const statusEl = getEl(ids.statusEl);
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.className = 'pin-status ' + (isSet ? 'set' : 'unset');
}

function updateInstruction(ids, text) {
    const instrEl = getEl(ids.instrEl);
    if (instrEl) instrEl.textContent = text;
}

function updateHint(ids, text) {
    const hintEl = getEl(ids.hintEl);
    if (hintEl) hintEl.textContent = text;
}

// ── Geocoding for PSGC ────────────────────────────────────────
async function geocodePSGC(name, type, ids) {
    let query = name;
    if (type === 'barangay' || type === 'city') {
        const prov = getEl(ids.province)?.options[getEl(ids.province)?.selectedIndex]?.text;
        const region = getEl(ids.region)?.options[getEl(ids.region)?.selectedIndex]?.text;
        if (prov && prov !== 'N/A (No Province)') query += ' ' + prov;
        if (region) query += ' ' + region;
    } else if (type === 'province') {
        const region = getEl(ids.region)?.options[getEl(ids.region)?.selectedIndex]?.text;
        if (region) query += ' ' + region;
    }
    query += ' Philippines';

    const cacheKey = `${type}:${name}`;
    if (PSGC_GEO_CACHE.has(cacheKey)) {
        return PSGC_GEO_CACHE.get(cacheKey);
    }

    try {
        const res = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&country=Philippines&limit=5`
        );
        const data = await res.json();
        if (data && data.length > 0) {
            const best = data[0];
            const result = { lat: parseFloat(best.lat), lng: parseFloat(best.lon), display_name: best.display_name };
            PSGC_GEO_CACHE.set(cacheKey, result);
            return result;
        }
    } catch (e) {
        console.warn('Geocoding failed for:', query, e);
    }
    return null;
}

// ── Map update from PSGC selection ─────────────────────────────
async function updateMapFromPSGC(ids, forceZoom) {
    if (!psgcMap) return;

    const regionOpt  = getEl(ids.region)?.options[getEl(ids.region)?.selectedIndex];
    const provOpt    = getEl(ids.province)?.options[getEl(ids.province)?.selectedIndex];
    const cityOpt    = getEl(ids.city)?.options[getEl(ids.city)?.selectedIndex];
    const barangayOpt= getEl(ids.barangay)?.options[getEl(ids.barangay)?.selectedIndex];

    const region  = regionOpt  && regionOpt.value  ? regionOpt.text  : null;
    const province= provOpt    && provOpt.value    ? provOpt.text    : null;
    const city    = cityOpt    && cityOpt.value    ? cityOpt.text    : null;
    const barangay= barangayOpt&& barangayOpt.value? barangayOpt.text: null;

    setMapLoading(true);
    updateInstruction(ids, 'Map centering... Please wait.');

    let target = null;
    let zoomLevel = 6;
    let lookupType = null;

    if (barangay) { target = barangay; zoomLevel = 14; lookupType = 'barangay'; }
    else if (city) { target = city; zoomLevel = 12; lookupType = 'city'; }
    else if (province) { target = province; zoomLevel = 10; lookupType = 'province'; }
    else if (region) { target = region; zoomLevel = 8; lookupType = 'region'; }

    if (target) {
        const coords = await geocodePSGC(target, lookupType, ids);
        if (coords) {
            psgcMap.flyTo([coords.lat, coords.lng], forceZoom || zoomLevel, { animate: true, duration: 1.2 });
            updateInstruction(ids, 'Please tap or drag the pin to set your exact delivery location');
            updateHint(ids, 'Tip: The map is centered. Adjust the pin for the exact delivery point.');
            if (!userHasSetPin && !psgcMarker) {
                placeMarker(coords.lat, coords.lng, ids, true);
            }
        } else {
            psgcMap.flyTo([12.8797, 121.7740], forceZoom || zoomLevel, { animate: true, duration: 1.2 });
        }
    }
    setTimeout(() => setMapLoading(false), 400);
}

// ── PSGC API calls ────────────────────────────────────────────
async function fetchPSGC(endpoint) {
    const res  = await fetch(`${PSGC_BASE}/${endpoint}`);
    return res.json();
}

async function loadRegions(ids) {
    setLoading(ids.region, true);
    const data = await fetchPSGC('regions/').catch(() => []);
    setLoading(ids.region, false);
    populateSelect(ids.region, data.map(r => ({ code: r.code, name: r.name })), 'Select Region');
    getEl(ids.region).disabled = false;
}

async function loadProvinces(regionCode, ids) {
    resetSelect(ids.province, 'Loading...');
    resetSelect(ids.city,     'Select City/Municipality');
    resetSelect(ids.barangay, 'Select Barangay');
    setLoading(ids.province, true);
    const data = await fetchPSGC(`regions/${regionCode}/provinces/`).catch(() => []);
    setLoading(ids.province, false);
    if (data.length) {
        populateSelect(ids.province, data.map(p => ({ code: p.code, name: p.name })), 'Select Province');
    } else {
        loadCitiesByRegion(regionCode, ids);
    }
}

async function loadCitiesByRegion(regionCode, ids) {
    setLoading(ids.city, true);
    const data = await fetchPSGC(`regions/${regionCode}/cities-municipalities/`).catch(() => []);
    setLoading(ids.city, false);
    populateSelect(ids.city, data.map(c => ({ code: c.code, name: c.name })), 'Select City/Municipality');
    resetSelect(ids.province, 'N/A (No Province)');
}

async function loadCities(provinceCode, ids) {
    resetSelect(ids.city,     'Loading...');
    resetSelect(ids.barangay, 'Select Barangay');
    setLoading(ids.city, true);
    const data = await fetchPSGC(`provinces/${provinceCode}/cities-municipalities/`).catch(() => []);
    setLoading(ids.city, false);
    populateSelect(ids.city, data.map(c => ({ code: c.code, name: c.name })), 'Select City/Municipality');
}

async function loadBarangays(cityCode, ids) {
    resetSelect(ids.barangay, 'Loading...');
    setLoading(ids.barangay, true);
    const data = await fetchPSGC(`cities-municipalities/${cityCode}/barangays/`).catch(() => []);
    setLoading(ids.barangay, false);
    populateSelect(ids.barangay, data.map(b => ({ code: b.code, name: b.name })), 'Select Barangay');
}

// ── Cascade setup ─────────────────────────────────────────────
function setupCascade(ids) {
    const onRegionChange = (e) => {
        const code = e.target.value;
        if (code) { loadProvinces(code, ids); userHasSetPin = false; setTimeout(() => updateMapFromPSGC(ids, 7), 300); }
        else { resetSelect(ids.province, 'Select Province'); resetSelect(ids.city, 'Select City/Municipality'); resetSelect(ids.barangay, 'Select Barangay'); }
    };
    const onProvinceChange = (e) => {
        const code = e.target.value;
        if (code) { loadCities(code, ids); userHasSetPin = false; setTimeout(() => updateMapFromPSGC(ids, 11), 300); }
        else { resetSelect(ids.city, 'Select City/Municipality'); resetSelect(ids.barangay, 'Select Barangay'); }
    };
    const onCityChange = (e) => {
        const code = e.target.value;
        if (code) { loadBarangays(code, ids); userHasSetPin = false; setTimeout(() => updateMapFromPSGC(ids, 14), 300); }
        else resetSelect(ids.barangay, 'Select Barangay');
    };
    const onBarangayChange = (e) => {
        if (e.target.value) { userHasSetPin = false; setTimeout(() => updateMapFromPSGC(ids, 16), 300); }
    };
    getEl(ids.region)?.addEventListener('change', onRegionChange);
    getEl(ids.province)?.addEventListener('change', onProvinceChange);
    getEl(ids.city)?.addEventListener('change', onCityChange);
    getEl(ids.barangay)?.addEventListener('change', onBarangayChange);
}

// ── Map ───────────────────────────────────────────────────────
let psgcMap = null;
let psgcMarker = null;

function initMap(ids) {
    const mapEl = getEl(ids.mapEl);
    if (!mapEl || typeof L === 'undefined') return;
    psgcMap = L.map(ids.mapEl, { tap: true, tapTolerance: 15 }).setView([12.8797, 121.7740], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors', maxZoom: 19
    }).addTo(psgcMap);
    psgcMap.on('click', (e) => {
        const { lat, lng } = e.latlng;
        placeMarker(lat, lng, ids, false);
        userHasSetPin = true;
        updateInstruction(ids, 'Pin placed. You can drag it to adjust.');
        updateHint(ids, 'Tip: Zoom in (pinch/scroll) for better precision');
    });
    psgcMap.zoomControl.setPosition('topleft');
}

function placeMarker(lat, lng, ids, isInitial = false) {
    if (psgcMarker) psgcMarker.setLatLng([lat, lng]);
    else {
        const markerDiv = L.divIcon({
            className: 'custom-div-icon',
            html: '<div class="custom-marker-icon"></div>',
            iconSize: [24, 24], iconAnchor: [12, 12]
        });
        psgcMarker = L.marker([lat, lng], {
            draggable: true, icon: markerDiv, zIndexOffset: 1000,
            keyboard: true, title: 'Drag to adjust location'
        }).addTo(psgcMap);
        psgcMarker.on('click', () => {
            updateInstruction(ids, 'Drag the pin to adjust, or click map to move it.');
        });
        psgcMarker.on('dragstart', () => { psgcMap.closePopup(); });
        psgcMarker.on('drag', () => {
            const pos = psgcMarker.getLatLng();
            setCoords(pos.lat, pos.lng, ids, true);
        });
        psgcMarker.on('dragend', (e) => {
            const pos = e.target.getLatLng();
            userHasSetPin = true;
            setCoords(pos.lat, pos.lng, ids, false);
            reverseGeocode(pos.lat, pos.lng, ids);
            updateInstruction(ids, 'Pin position set. Drag to adjust anytime.');
            updatePinStatus(ids, true, '✓ Exact delivery location set');
        });
    }
    psgcMarker.setLatLng([lat, lng]);
    if (!isInitial) {
        psgcMap.flyTo([lat, lng], 16, { animate: true, duration: 0.6 });
    }
    if (isInitial) {
        updatePinStatus(ids, false, '⚠ Approximate location. Please drag pin for precision');
        updateInstruction(ids, 'Map centered approximately. Please drag the pin to set exact delivery point.');
    } else {
        setCoords(lat, lng, ids, false);
        reverseGeocode(lat, lng, ids);
        updatePinStatus(ids, true, '✓ Exact delivery location set');
        updateInstruction(ids, 'Pin placed at exact location. You can drag it to adjust.');
    }
}

function setCoords(lat, lng, ids, isDragging) {
    const latEl = getEl(ids.latitude);
    const lngEl = getEl(ids.longitude);
    const dispEl = getEl(ids.coordsEl);
    if (latEl) latEl.value = lat.toFixed(8);
    if (lngEl) lngEl.value = lng.toFixed(8);
    if (dispEl) {
        dispEl.textContent = `📍 Lat: ${lat.toFixed(6)}, Lng: ${lng.toFixed(6)}`;
        dispEl.style.color = isDragging ? '#FF2BAC' : '#2c2c5c';
    }
}

// ── Reverse geocoding (Nominatim) ─────────────────────────────
async function reverseGeocode(lat, lng, ids) {
    try {
        const res  = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=18`);
        const data = await res.json();
        const addr = data.address || {};
        const streetEl = getEl(ids.street);
        if (streetEl && !streetEl.value.trim()) {
            const parts = [];
            if (addr.road) parts.push(addr.road);
            if (addr.house_number) parts.push(addr.house_number);
            if (parts.length) {
                streetEl.value = parts.join(' ');
                updateInstruction(ids, 'Address auto-filled. Please verify accuracy.');
            }
        }
        const zipEl = getEl(ids.zip);
        if (zipEl && !zipEl.value.trim() && addr.postcode) {
            zipEl.value = addr.postcode;
        }
        const barangayEl = getEl(ids.barangay);
        if (barangayEl && !barangayEl.value && addr.suburb) {
            const opts = barangayEl.options;
            for (let i = 0; i < opts.length; i++) {
                if (opts[i].text.toLowerCase().includes(addr.suburb.toLowerCase())) {
                    barangayEl.value = opts[i].value; break;
                }
            }
        }
        return addr;
    } catch (e) { return null; }
}

// ── Geolocation ───────────────────────────────────────────────
function setupGeolocation(ids) {
    const btn = getEl(ids.geoBtn);
    if (!btn) return;
    btn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
        }
        btn.disabled = true;
        btn.textContent = '📡 Getting location...';
        updateInstruction(ids, 'Detecting your current location...');
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                placeMarker(lat, lng, ids, false);
                userHasSetPin = true;
                btn.disabled = false;
                btn.innerHTML = '📍 Use My Current Location';
                updateInstruction(ids, 'Your location detected. Drag pin to adjust if needed.');
                updatePinStatus(ids, true, '✓ Location set from device GPS');
                updateHint(ids, 'Tip: Pin automatically placed. Drag to fine-tune position');
            },
            (err) => {
                alert('Could not get your location. Please place the pin manually on the map.');
                btn.disabled = false;
                btn.innerHTML = '📍 Use My Current Location';
                updateInstruction(ids, 'Please tap the map or drag the pin to set your location.');
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
        );
    });
}

// ── Get selected text values (for saving) ────────────────────
function getPSGCValues(ids = {}) {
    const getText = (id) => { const el = getEl(id); return el ? el.options[el.selectedIndex]?.text || '' : ''; };
    const getVal = (id) => getEl(id)?.value || '';
    return {
        region:    getText(ids.region    || 'addrRegion'),
        province:  getText(ids.province  || 'addrProvince'),
        city:      getText(ids.city      || 'addrCity'),
        barangay:  getText(ids.barangay  || 'addrBarangay'),
        street:    getVal(ids.street     || 'addrStreet'),
        zip_code:  getVal(ids.zip        || 'addrZip'),
        latitude:  getVal(ids.latitude   || 'addrLatitude')  || null,
        longitude: getVal(ids.longitude  || 'addrLongitude') || null,
    };
}