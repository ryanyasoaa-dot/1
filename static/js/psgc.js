/**
 * psgc.js — PSGC dropdowns + Leaflet map + Geolocation
 */

const PSGC_BASE      = 'https://psgc.gitlab.io/api';
const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org';
const GEO_CACHE      = new Map();

let psgcMap    = null;
let psgcMarker = null;
let _ids       = null;

// ── Init ──────────────────────────────────────────────────────
function initPSGC(config = {}) {
    _ids = {
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
        statusEl:  config.statusEl  || 'pinStatus',
        instrEl:   config.instrEl   || 'mapInstructionText',
    };
    loadRegions(_ids);
    setupCascade(_ids);
    initMap(_ids);
    setupGeolocation(_ids);
}

// ── DOM helpers ───────────────────────────────────────────────
const getEl = (id) => document.getElementById(id);

function setInstruction(text) {
    const el = getEl(_ids?.instrEl);
    if (el) el.textContent = text;
}

function setPinStatus(ok, msg) {
    const el = getEl(_ids?.statusEl);
    if (!el) return;
    el.textContent = msg;
    el.className = 'pin-status ' + (ok ? 'set' : 'unset');
}

function setSelectLoading(id, on) {
    getEl(id)?.parentElement?.classList.toggle('select-loading', on);
}

function setGeoBtn(loading) {
    const btn = getEl(_ids?.geoBtn);
    if (!btn) return;
    btn.disabled    = loading;
    btn.textContent = loading ? '📡 Detecting location...' : '📍 Use My Current Location';
}

// ── Coords display ────────────────────────────────────────────
function setCoords(lat, lng, dragging = false) {
    const latEl  = getEl(_ids.latitude);
    const lngEl  = getEl(_ids.longitude);
    const dispEl = getEl(_ids.coordsEl);
    if (latEl)  latEl.value  = lat.toFixed(8);
    if (lngEl)  lngEl.value  = lng.toFixed(8);
    if (dispEl) {
        dispEl.textContent = `📍 Lat: ${lat.toFixed(6)}, Lng: ${lng.toFixed(6)}`;
        dispEl.style.color = dragging ? '#FF2BAC' : '#2c2c5c';
    }
}

// ── PSGC fetch ────────────────────────────────────────────────
async function fetchPSGC(endpoint) {
    const res = await fetch(`${PSGC_BASE}/${endpoint}`);
    if (!res.ok) return [];
    return res.json();
}

// ── Populate / reset selects ──────────────────────────────────
function populateSelect(id, items, placeholder) {
    const el = getEl(id);
    if (!el) return;
    el.innerHTML = `<option value="">${placeholder}</option>`;
    items.forEach(({ code, name }) => {
        const o = document.createElement('option');
        o.value = code; o.textContent = name;
        el.appendChild(o);
    });
    el.disabled = items.length === 0;
}

function resetSelect(id, placeholder = 'Select', disabled = true) {
    const el = getEl(id);
    if (!el) return;
    el.innerHTML = `<option value="">${placeholder}</option>`;
    el.disabled  = disabled;
}

// ── Load functions (all return data for chaining) ─────────────
async function loadRegions(ids) {
    setSelectLoading(ids.region, true);
    const data = await fetchPSGC('regions/').catch(() => []);
    setSelectLoading(ids.region, false);
    populateSelect(ids.region, data.map(r => ({ code: r.code, name: r.name })), 'Select Region');
    getEl(ids.region).disabled = false;
    return data;
}

async function loadProvinces(regionCode, ids) {
    resetSelect(ids.province, 'Loading...', false);
    resetSelect(ids.city,     'Select City/Municipality');
    resetSelect(ids.barangay, 'Select Barangay');
    setSelectLoading(ids.province, true);
    const data = await fetchPSGC(`regions/${regionCode}/provinces/`).catch(() => []);
    setSelectLoading(ids.province, false);
    if (data.length) {
        populateSelect(ids.province, data.map(p => ({ code: p.code, name: p.name })), 'Select Province');
    } else {
        // NCR / no-province region — load cities directly
        resetSelect(ids.province, 'N/A', false);
        await loadCitiesByRegion(regionCode, ids);
    }
    return data;
}

async function loadCitiesByRegion(regionCode, ids) {
    setSelectLoading(ids.city, true);
    const data = await fetchPSGC(`regions/${regionCode}/cities-municipalities/`).catch(() => []);
    setSelectLoading(ids.city, false);
    populateSelect(ids.city, data.map(c => ({ code: c.code, name: c.name })), 'Select City/Municipality');
    return data;
}

async function loadCities(provinceCode, ids) {
    resetSelect(ids.city,     'Loading...', false);
    resetSelect(ids.barangay, 'Select Barangay');
    setSelectLoading(ids.city, true);
    const data = await fetchPSGC(`provinces/${provinceCode}/cities-municipalities/`).catch(() => []);
    setSelectLoading(ids.city, false);
    populateSelect(ids.city, data.map(c => ({ code: c.code, name: c.name })), 'Select City/Municipality');
    return data;
}

async function loadBarangays(cityCode, ids) {
    resetSelect(ids.barangay, 'Loading...', false);
    setSelectLoading(ids.barangay, true);
    const data = await fetchPSGC(`cities-municipalities/${cityCode}/barangays/`).catch(() => []);
    setSelectLoading(ids.barangay, false);
    populateSelect(ids.barangay, data.map(b => ({ code: b.code, name: b.name })), 'Select Barangay');
    return data;
}

// ── Cascade dropdowns ─────────────────────────────────────────
function setupCascade(ids) {
    getEl(ids.region)?.addEventListener('change', async (e) => {
        const code = e.target.value;
        if (!code) { resetSelect(ids.province, 'Select Province'); resetSelect(ids.city, 'Select City/Municipality'); resetSelect(ids.barangay, 'Select Barangay'); return; }
        await loadProvinces(code, ids);
        updateMapFromDropdowns(ids);
    });
    getEl(ids.province)?.addEventListener('change', async (e) => {
        const code = e.target.value;
        if (!code) { resetSelect(ids.city, 'Select City/Municipality'); resetSelect(ids.barangay, 'Select Barangay'); return; }
        await loadCities(code, ids);
        updateMapFromDropdowns(ids);
    });
    getEl(ids.city)?.addEventListener('change', async (e) => {
        const code = e.target.value;
        if (!code) { resetSelect(ids.barangay, 'Select Barangay'); return; }
        await loadBarangays(code, ids);
        updateMapFromDropdowns(ids);
    });
    getEl(ids.barangay)?.addEventListener('change', () => updateMapFromDropdowns(ids));
}

// ── Map center from dropdown selection ────────────────────────
async function updateMapFromDropdowns(ids) {
    if (!psgcMap) return;

    const optText = (id) => { const el = getEl(id); return el?.value ? el.options[el.selectedIndex]?.text : null; };
    const barangay = optText(ids.barangay);
    const city     = optText(ids.city);
    const province = optText(ids.province);
    const region   = optText(ids.region);

    let query = null, zoom = 6;
    if (barangay) { query = `${barangay}, ${city || ''}, ${province || ''}, Philippines`; zoom = 15; }
    else if (city)     { query = `${city}, ${province || ''}, Philippines`; zoom = 13; }
    else if (province) { query = `${province}, Philippines`; zoom = 10; }
    else if (region)   { query = `${region}, Philippines`; zoom = 8; }
    if (!query) return;

    const cacheKey = query;
    let coords = GEO_CACHE.get(cacheKey);
    if (!coords) {
        try {
            const res  = await fetch(`${NOMINATIM_BASE}/search?format=json&q=${encodeURIComponent(query)}&limit=1`);
            const data = await res.json();
            if (data[0]) {
                coords = { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
                GEO_CACHE.set(cacheKey, coords);
            }
        } catch { return; }
    }
    if (!coords) return;

    psgcMap.flyTo([coords.lat, coords.lng], zoom, { animate: true, duration: 1 });
    // Place a soft marker if none set yet
    if (!psgcMarker) {
        placeMarker(coords.lat, coords.lng, ids, true);
    }
    setInstruction('Dropdown location set. Drag the pin or click the map for exact position.');
}

// ── Map init ──────────────────────────────────────────────────
function initMap(ids) {
    const mapEl = getEl(ids.mapEl);
    if (!mapEl || typeof L === 'undefined') return;

    psgcMap = L.map(ids.mapEl, {
        tap: true,
        tapTolerance: 20,
        zoomControl: true,
    }).setView([12.8797, 121.7740], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
    }).addTo(psgcMap);

    psgcMap.zoomControl.setPosition('topleft');

    // Click to place pin
    psgcMap.on('click', (e) => {
        const { lat, lng } = e.latlng;
        placeMarker(lat, lng, ids, false);
        setCoords(lat, lng);
        setInstruction('Pin placed. Drag to fine-tune your exact location.');
        setPinStatus(true, '✓ Location pinned');
        reverseGeocode(lat, lng, ids);
    });
}

// ── Marker ────────────────────────────────────────────────────
function placeMarker(lat, lng, ids, soft = false) {
    if (psgcMarker) {
        psgcMarker.setLatLng([lat, lng]);
    } else {
        const icon = L.divIcon({
            className: 'custom-div-icon',
            html: '<div class="custom-marker-icon"></div>',
            iconSize: [28, 28],
            iconAnchor: [14, 28],   // tip of the pin at click point
            popupAnchor: [0, -28],
        });
        psgcMarker = L.marker([lat, lng], {
            draggable: true,
            icon,
            zIndexOffset: 1000,
            title: 'Drag to adjust location',
        }).addTo(psgcMap);

        psgcMarker.on('drag', () => {
            const p = psgcMarker.getLatLng();
            setCoords(p.lat, p.lng, true);
        });

        psgcMarker.on('dragend', () => {
            const p = psgcMarker.getLatLng();
            setCoords(p.lat, p.lng, false);
            setPinStatus(true, '✓ Exact location set');
            setInstruction('Pin moved. Updating address...');
            reverseGeocode(p.lat, p.lng, ids);
        });
    }

    if (!soft) {
        psgcMap.flyTo([lat, lng], Math.max(psgcMap.getZoom(), 16), { animate: true, duration: 0.8 });
        setCoords(lat, lng);
        setPinStatus(true, '✓ Location pinned');
    } else {
        // Soft = just center, don't override coords
        setPinStatus(false, '⚠ Approximate — drag pin for precision');
    }
}

// ── Reverse geocode → fill dropdowns ─────────────────────────
async function reverseGeocode(lat, lng, ids) {
    try {
        const res  = await fetch(`${NOMINATIM_BASE}/reverse?lat=${lat}&lon=${lng}&format=json&zoom=18&addressdetails=1`);
        const data = await res.json();
        const addr = data.address || {};

        // Street
        const streetEl = getEl(ids.street);
        if (streetEl) {
            const parts = [addr.house_number, addr.road].filter(Boolean);
            if (parts.length) streetEl.value = parts.join(' ');
        }

        // ZIP
        const zipEl = getEl(ids.zip);
        if (zipEl && addr.postcode) zipEl.value = addr.postcode;

        // Dropdowns
        await syncDropdownsFromAddress(addr, ids);

        setInstruction('Address filled. Please verify and adjust if needed.');
    } catch (e) {
        console.warn('Reverse geocode failed', e);
    }
}

// ── Match Nominatim address → PSGC dropdowns ─────────────────
async function syncDropdownsFromAddress(addr, ids) {
    const regionName   = addr.state || addr.region || '';
    const provinceName = addr.province || addr.county || '';
    const cityName     = addr.city || addr.town || addr.municipality ||
                         addr.city_district || addr.village || '';
    const barangayName = addr.suburb || addr.neighbourhood || addr.quarter ||
                         addr.hamlet || addr.residential || '';

    // Map common Philippine region names to PSGC codes
    const regionMap = {
        'national capital region': '130000000',
        'ncr': '130000000',
        'metro manila': '130000000',
        'region i': '010000000',
        'ilocos region': '010000000',
        'region ii': '020000000',
        'cagayan valley': '020000000',
        'region iii': '030000000',
        'central luzon': '030000000',
        'region iv-a': '040000000',
        'calabarzon': '040000000',
        'region iv-b': '170000000',
        'mimaropa': '170000000',
        'region v': '050000000',
        'bicol region': '050000000',
        'region vi': '060000000',
        'western visayas': '060000000',
        'region vii': '070000000',
        'central visayas': '070000000',
        'region viii': '080000000',
        'eastern visayas': '080000000',
        'region ix': '090000000',
        'zamboanga peninsula': '090000000',
        'region x': '100000000',
        'northern mindanao': '100000000',
        'region xi': '110000000',
        'davao region': '110000000',
        'region xii': '120000000',
        'soccsksargen': '120000000',
        'region xiii': '160000000',
        'caraga': '160000000',
        'bangsamoro autonomous region in muslim mindanao': '190000000',
        'barrm': '190000000',
        'cordillera administrative region': '140000000',
        'car': '140000000'
    };

    let regionCode = null;
    const normRegion = normalizePH(regionName);
    if (normRegion in regionMap) {
        regionCode = regionMap[normRegion];
    } else {
        // Fallback to matching
        const regionEl = getEl(ids.region);
        if (!regionEl) return;
        await waitForOptions(regionEl);
        regionCode = matchOption(regionEl, regionName);
    }

    if (!regionCode) return;
    getEl(ids.region).value = regionCode;

    // 2. Load provinces for this region
    const provinces = await fetchPSGC(`regions/${regionCode}/provinces/`).catch(() => []);
    const provEl = getEl(ids.province);

    let cityCode = null;

    if (provinces.length) {
        // Has provinces — populate and match
        populateSelect(ids.province, provinces.map(p => ({ code: p.code, name: p.name })), 'Select Province');
        if (provEl) provEl.disabled = false;

        let provCode = provinceName ? matchOption(provEl, provinceName) : null;

        let cities = [];
        if (provCode) {
            provEl.value = provCode;
            cities = await fetchPSGC(`provinces/${provCode}/cities-municipalities/`).catch(() => []);
        } else {
            // Province not matched — load all cities in region as fallback
            cities = await fetchPSGC(`regions/${regionCode}/cities-municipalities/`).catch(() => []);
        }

        populateSelect(ids.city, cities.map(c => ({ code: c.code, name: c.name })), 'Select City/Municipality');
        const cityEl = getEl(ids.city);
        if (cityEl) cityEl.disabled = false;
        cityCode = matchOption(cityEl, cityName);
        if (cityCode) cityEl.value = cityCode;

    } else {
        // No provinces (NCR) — load cities directly by region
        if (provEl) { provEl.innerHTML = '<option value="">N/A</option>'; provEl.disabled = false; }
        resetSelect(ids.city, 'Select City/Municipality');
        resetSelect(ids.barangay, 'Select Barangay');

        const cities = await fetchPSGC(`regions/${regionCode}/cities-municipalities/`).catch(() => []);
        populateSelect(ids.city, cities.map(c => ({ code: c.code, name: c.name })), 'Select City/Municipality');
        const cityEl = getEl(ids.city);
        if (cityEl) cityEl.disabled = false;
        cityCode = matchOption(cityEl, cityName);
        if (cityCode) cityEl.value = cityCode;
    }

    if (!cityCode) return;

    // 3. Load barangays for matched city
    const barangays = await fetchPSGC(`cities-municipalities/${cityCode}/barangays/`).catch(() => []);
    populateSelect(ids.barangay, barangays.map(b => ({ code: b.code, name: b.name })), 'Select Barangay');
    const brgyEl = getEl(ids.barangay);
    if (brgyEl) brgyEl.disabled = false;

    if (barangayName) {
        const brgyCode = matchOption(brgyEl, barangayName);
        if (brgyCode) brgyEl.value = brgyCode;
    }
}

// ── Wait for a select to have options (regions load async) ────
function waitForOptions(selectEl, maxWait = 5000) {
    return new Promise(resolve => {
        if (selectEl.options.length > 1) { resolve(); return; }
        const start = Date.now();
        const check = setInterval(() => {
            if (selectEl.options.length > 1 || Date.now() - start > maxWait) {
                clearInterval(check);
                resolve();
            }
        }, 100);
    });
}

// ── Fuzzy option matcher ──────────────────────────────────────
function normalizePH(s) {
    return (s || '').toLowerCase()
        .replace(/\bncr\b/g, 'national capital region')
        .replace(/\bmetro manila\b/g, 'national capital region')
        .replace(/^city of /,  '')
        .replace(/^municipality of /, '')
        .replace(/ city$/, '')
        .replace(/\bst\.?\s/g, 'saint ')
        .replace(/[^a-z0-9\s]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

function matchOption(selectEl, name) {
    if (!selectEl || !name) return null;
    const opts = Array.from(selectEl.options).filter(o => o.value);
    const raw  = name.toLowerCase().trim();
    const norm = normalizePH(name);

    // 1. Exact raw
    for (const o of opts) if (o.text.toLowerCase() === raw)  return o.value;
    // 2. Exact normalized
    for (const o of opts) if (normalizePH(o.text) === norm)  return o.value;
    // 3. Option text contains query (raw)
    for (const o of opts) if (o.text.toLowerCase().includes(raw))  return o.value;
    // 4. Query contains option text (normalized)
    for (const o of opts) if (norm.includes(normalizePH(o.text)))  return o.value;
    // 5. Option text contains query (normalized)
    for (const o of opts) if (normalizePH(o.text).includes(norm))  return o.value;
    // 6. Word-level overlap (normalized)
    const qWords = norm.split(/\s+/).filter(w => w.length > 2);
    for (const o of opts) {
        const oWords = normalizePH(o.text).split(/\s+/);
        const hits = qWords.filter(w => oWords.some(ow => ow.includes(w) || w.includes(ow)));
        if (hits.length >= Math.min(2, qWords.length)) return o.value;
    }
    // 7. Single strong word match
    for (const o of opts) {
        const oWords = normalizePH(o.text).split(/\s+/);
        if (qWords.some(w => w.length > 4 && oWords.includes(w))) return o.value;
    }
    return null;
}

// ── Geolocation button ────────────────────────────────────────
function setupGeolocation(ids) {
    const btn = getEl(ids.geoBtn);
    if (!btn) return;

    btn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
        }
        setGeoBtn(true);
        setInstruction('Detecting your GPS location...');

        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;

                // Place pin exactly at GPS coords
                placeMarker(lat, lng, ids, false);
                setCoords(lat, lng);
                setPinStatus(true, '✓ GPS location detected');
                setInstruction('Location found. Filling in address details...');
                setGeoBtn(false);

                // Reverse geocode → fill all dropdowns
                await reverseGeocode(lat, lng, ids);
                setInstruction('Done! Verify the address and drag the pin if needed.');
            },
            (err) => {
                setGeoBtn(false);
                setInstruction('Could not get location. Click the map to place pin manually.');
                setPinStatus(false, '✗ GPS failed — place pin manually');
                console.warn('Geolocation error:', err.message);
            },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    });
}

// ── Get values for form submission ────────────────────────────
function getPSGCValues(ids = {}) {
    const getText = (id) => {
        const el = getEl(id);
        return el?.value ? (el.options[el.selectedIndex]?.text || '') : '';
    };
    const getVal = (id) => getEl(id)?.value?.trim() || '';
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
