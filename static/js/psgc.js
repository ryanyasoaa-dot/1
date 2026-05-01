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
    // Nominatim PH fields:
    // state       → region (e.g. "Calabarzon", "Metro Manila")
    // province    → province (e.g. "Laguna")
    // city/town/municipality/village → city
    // suburb/neighbourhood/quarter  → barangay

    const regionName   = addr.state || addr.region || '';
    const provinceName = addr.province || addr.county || '';
    const cityName     = addr.city || addr.town || addr.municipality || addr.city_district || addr.village || '';
    const barangayName = addr.suburb || addr.neighbourhood || addr.quarter || '';

    const regionEl = getEl(ids.region);
    if (!regionEl || !regionName) return;

    // 1. Match region
    const regionCode = matchOption(regionEl, regionName);
    if (!regionCode) return;
    regionEl.value = regionCode;

    // 2. Load & match province
    const provinces = await loadProvinces(regionCode, ids);
    const provEl    = getEl(ids.province);

    let cityData = [];
    if (provinces.length && provinceName) {
        const provCode = matchOption(provEl, provinceName);
        if (provCode) {
            provEl.value = provCode;
            cityData = await loadCities(provCode, ids);
        } else {
            // Province not matched — try loading cities by region
            cityData = await loadCitiesByRegion(regionCode, ids);
        }
    } else {
        // No province (NCR) — cities already loaded by loadProvinces
        cityData = Array.from(getEl(ids.city)?.options || [])
            .filter(o => o.value)
            .map(o => ({ code: o.value, name: o.text }));
    }

    // 3. Match city
    const cityEl   = getEl(ids.city);
    const cityCode = matchOption(cityEl, cityName);
    if (!cityCode) return;
    cityEl.value = cityCode;

    // 4. Load & match barangay
    await loadBarangays(cityCode, ids);
    if (barangayName) {
        const brgyEl   = getEl(ids.barangay);
        const brgyCode = matchOption(brgyEl, barangayName);
        if (brgyCode) brgyEl.value = brgyCode;
    }
}

// ── Fuzzy option matcher ──────────────────────────────────────
function matchOption(selectEl, name) {
    if (!selectEl || !name) return null;
    const q    = name.toLowerCase().trim();
    const opts = Array.from(selectEl.options).filter(o => o.value);

    // 1. Exact
    for (const o of opts) if (o.text.toLowerCase() === q) return o.value;
    // 2. Select contains query
    for (const o of opts) if (o.text.toLowerCase().includes(q)) return o.value;
    // 3. Query contains option text
    for (const o of opts) if (q.includes(o.text.toLowerCase())) return o.value;
    // 4. Word-level overlap
    const qWords = q.split(/\s+/);
    for (const o of opts) {
        const oWords = o.text.toLowerCase().split(/\s+/);
        if (qWords.some(w => w.length > 3 && oWords.some(ow => ow.includes(w) || w.includes(ow)))) return o.value;
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
