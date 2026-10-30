/* MotoServe 360 - Real-Time Location-Based Service Discovery & Map Integration */

let mainMap = null;
let userMarker = null;
let dropMarker = null;
let routePolyline = null;
let providerMarkersGroup = null;

// Initialize standard Leaflet Map
function initMap(mapElementId, defaultLat = 12.2958, defaultLng = 76.6394, zoom = 14) {
  const mapContainer = document.getElementById(mapElementId);
  if (!mapContainer) return null;

  // Cleanup if map already initialized
  if (mainMap && mainMap._leaflet_id && mapContainer.classList.contains('leaflet-container')) {
    try { mainMap.remove(); } catch (e) {}
  }

  mainMap = L.map(mapElementId, { zoomControl: true }).setView([defaultLat, defaultLng], zoom);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(mainMap);

  return mainMap;
}

// Create Custom Map Pin Icons
function createCustomIcon(iconClass, color, isPartner = false) {
  const partnerBadge = isPartner
    ? `<span style="position: absolute; top: -3px; right: -3px; background: #10b981; color: white; width: 14px; height: 14px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 8px; border: 1.5px solid white;"><i class="fas fa-check"></i></span>`
    : '';

  return L.divIcon({
    html: `<div style="position: relative; background-color: ${color}; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.35); border: 2.5px solid white;">
      <i class="${iconClass}"></i>
      ${partnerBadge}
    </div>`,
    className: 'custom-leaflet-pin',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20]
  });
}

// Fetch Place Name via Backend API or Nominatim Fallback
function fetchPlaceName(lat, lng, addressInputId, localityInputId = 'locality', onComplete = null) {
  const addressInput = document.getElementById(addressInputId);
  const localityInput = localityInputId ? document.getElementById(localityInputId) : null;
  const statusDisplay = document.getElementById('location-status-text');

  if (addressInput && !addressInput.value) {
    addressInput.value = "📍 Resolving address...";
  }
  if (statusDisplay) {
    statusDisplay.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> Resolving location...`;
  }

  fetch(`/api/location/reverse?lat=${lat}&lng=${lng}`)
    .then(res => res.json())
    .then(payload => {
      let resolvedAddress = "";
      let localityName = "";
      let cityName = "";

      if (payload && payload.status === 'success' && payload.data) {
        resolvedAddress = payload.data.display_name;
        localityName = payload.data.locality || payload.data.city || "";
        cityName = payload.data.city || "";
      } else {
        resolvedAddress = `Location (${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)})`;
      }

      if (addressInput) addressInput.value = resolvedAddress;
      if (localityInput && localityName) localityInput.value = localityName;

      if (statusDisplay) {
        const badgeCity = cityName || localityName || `${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)}`;
        statusDisplay.innerHTML = `<i class="fas fa-location-dot text-success me-1"></i> <strong>${badgeCity}</strong> (${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)})`;
      }

      if (onComplete && typeof onComplete === 'function') {
        onComplete(payload.data || { lat, lng, display_name: resolvedAddress });
      }
    })
    .catch(err => {
      console.warn("Reverse geocode fallback:", err);
      const fallback = `Coordinates: (${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)})`;
      if (addressInput) addressInput.value = fallback;
      if (statusDisplay) {
        statusDisplay.innerHTML = `<i class="fas fa-location-dot text-primary me-1"></i> (${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)})`;
      }
      if (onComplete && typeof onComplete === 'function') {
        onComplete({ lat, lng, display_name: fallback });
      }
    });
}

/**
 * Service Booking Map Integration:
 * Handles user location discovery, reverse-geocoding, Leaflet markers,
 * real-time nearby provider searching (/api/nearby/{service}),
 * interactive provider selection, distance calculation, and empty states.
 */
function initServiceBookingMap(options) {
  const mapElementId = options.mapElementId;
  const serviceType = options.serviceType; // 'fuel', 'repair', 'tow'
  const latInputId = options.latInputId || 'pickup_lat';
  const lngInputId = options.lngInputId || 'pickup_lng';
  const addressInputId = options.addressInputId || 'pickup_address';
  const localityInputId = options.localityInputId || 'locality';

  const providerIdInput = document.getElementById(options.providerIdInputId || 'selected_provider_id');
  const providerNameInput = document.getElementById(options.providerNameInputId || 'selected_provider_name');
  const providerLatInput = document.getElementById(options.providerLatInputId || 'provider_lat');
  const providerLngInput = document.getElementById(options.providerLngInputId || 'provider_lng');
  const providerAddressInput = document.getElementById(options.providerAddressInputId || 'provider_address');
  const providerSourceInput = document.getElementById(options.providerSourceInputId || 'provider_source');

  const providersContainer = document.getElementById(options.providerListContainerId || 'nearby-providers-list');
  const selectedProviderCard = document.getElementById(options.selectedProviderCardId || 'selected-provider-card');
  const selectedProviderNameText = document.getElementById('selected-provider-name-text');
  const selectedProviderMetaText = document.getElementById('selected-provider-meta-text');
  const btnClearProvider = document.getElementById('btn-clear-provider');

  let currentRadius = options.initialRadius || (serviceType === 'fuel' ? 10 : serviceType === 'repair' ? 15 : 25);
  let nearbyProvidersData = [];

  // Default coordinate: starts with clean center, then immediately triggers geolocation detection
  const latEl = document.getElementById(latInputId);
  const lngEl = document.getElementById(lngInputId);
  let activeLat = latEl && latEl.value ? parseFloat(latEl.value) : 12.2958;
  let activeLng = lngEl && lngEl.value ? parseFloat(lngEl.value) : 76.6394;

  const map = initMap(mapElementId, activeLat, activeLng, 14);
  if (!map) return;

  // Layer Group for Provider Pins
  if (providerMarkersGroup) {
    try { map.removeLayer(providerMarkersGroup); } catch (e) {}
  }
  providerMarkersGroup = L.layerGroup().addTo(map);

  // User Marker
  const customerIcon = createCustomIcon('fas fa-user-pin', '#2563eb');
  userMarker = L.marker([activeLat, activeLng], {
    icon: customerIcon,
    draggable: true,
    zIndexOffset: 1000
  }).addTo(map);
  userMarker.bindTooltip("Your Service Location (Drag to adjust)", { permanent: false, direction: 'top' });

  // Update inputs and refresh nearby providers
  function setLocation(lat, lng, addressName = null, autoZoom = false) {
    activeLat = parseFloat(lat);
    activeLng = parseFloat(lng);

    userMarker.setLatLng([activeLat, activeLng]);
    if (autoZoom) {
      map.setView([activeLat, activeLng], 14);
    }

    if (latEl) latEl.value = Number(activeLat).toFixed(6);
    if (lngEl) lngEl.value = Number(activeLng).toFixed(6);

    fetchPlaceName(activeLat, activeLng, addressInputId, localityInputId, function(data) {
      loadNearbyProviders(activeLat, activeLng, currentRadius);
    });
  }

  // Fetch Nearby Providers from Backend
  function loadNearbyProviders(lat, lng, radius) {
    if (!providersContainer) return;

    providersContainer.innerHTML = `
      <div class="text-center py-4 text-muted">
        <div class="spinner-border spinner-border-sm text-primary mb-2" role="status"></div>
        <p class="small mb-0">Searching real mapped ${serviceType} providers within ${radius} km...</p>
      </div>
    `;

    providerMarkersGroup.clearLayers();

    const apiUrl = `/api/nearby/${serviceType}?lat=${lat}&lng=${lng}&radius=${radius}`;
    fetch(apiUrl)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.providers && data.providers.length > 0) {
          nearbyProvidersData = data.providers;
          renderProviderMarkers(data.providers);
          renderProviderList(data.providers, data.radius_km);

          // Auto-select the nearest provider as default so user is immediately connected
          if (!providerNameInput || !providerNameInput.value) {
            selectProvider(data.providers[0]);
          }
        } else {
          nearbyProvidersData = [];
          renderEmptyState(radius);
        }
      })
      .catch(err => {
        console.error("Nearby search error:", err);
        providersContainer.innerHTML = `
          <div class="alert alert-warning small p-3 mb-0">
            <i class="fas fa-triangle-exclamation me-1"></i>
            Could not fetch provider list at this moment. You can still submit your request and the nearest dispatch will be alerted.
          </div>
        `;
      });
  }

  // Render Markers on Leaflet Map
  function renderProviderMarkers(providers) {
    providerMarkersGroup.clearLayers();

    const iconClass = serviceType === 'fuel' ? 'fas fa-gas-pump' : serviceType === 'repair' ? 'fas fa-wrench' : 'fas fa-truck-pickup';
    const baseColor = serviceType === 'fuel' ? '#f59e0b' : serviceType === 'repair' ? '#0284c7' : '#ef4444';

    providers.forEach(p => {
      const isPartner = p.is_partner === true;
      const markerColor = isPartner ? '#10b981' : baseColor;
      const icon = createCustomIcon(iconClass, markerColor, isPartner);

      const marker = L.marker([p.lat, p.lng], { icon: icon }).addTo(providerMarkersGroup);

      const partnerBadge = isPartner
        ? `<span class="badge bg-success small me-1"><i class="fas fa-shield-check me-1"></i>Verified Partner</span>`
        : `<span class="badge bg-secondary small me-1"><i class="fas fa-map-pin me-1"></i>OpenStreetMap Verified</span>`;

      const brandBadge = p.brand ? `<span class="badge bg-warning-subtle text-dark border small me-1"><i class="fas fa-gas-pump text-warning me-1"></i>${escapeHtml(p.brand)}</span>` : '';
      const distBadge = `<span class="badge bg-primary text-white small">${p.formatted_distance || (p.distance_km + ' km')}</span>`;

      const popupContent = `
        <div style="min-width: 220px; font-family: inherit;">
          <h6 class="fw-bold text-dark mb-1">${escapeHtml(p.business_name || p.name)}</h6>
          <div class="mb-2 d-flex flex-wrap gap-1 align-items-center">${partnerBadge} ${brandBadge} ${distBadge}</div>
          <p class="small text-muted mb-1"><i class="fas fa-location-dot me-1"></i>${escapeHtml(p.address || 'Address on record')}</p>
          ${p.opening_hours ? `<div class="small text-muted mb-2"><i class="fas fa-clock me-1"></i>${escapeHtml(p.opening_hours)}</div>` : ''}
          <div class="small text-secondary mb-2">Straight-line distance: <strong>${p.formatted_distance}</strong></div>
          <button type="button" class="btn btn-sm btn-primary w-100 fw-bold py-1 select-provider-btn" data-pid="${p.id}" data-pname="${escapeHtml(p.business_name || p.name)}">
            <i class="fas fa-circle-check me-1"></i>Select This ${serviceType === 'fuel' ? 'Station' : 'Provider'}
          </button>
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('popupopen', function () {
        const btn = document.querySelector(`.select-provider-btn[data-pid="${p.id}"]`);
        if (btn) {
          btn.onclick = function () {
            selectProvider(p);
            marker.closePopup();
          };
        }
      });

      p._marker = marker;
    });

    if (providers.length > 0) {
      try {
        const bounds = L.latLngBounds([[activeLat, activeLng]]);
        providers.forEach(p => bounds.extend([p.lat, p.lng]));
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
      } catch (e) {
        console.warn("Could not fit bounds:", e);
      }
    }
  }

  // Render Provider List in DOM
  function renderProviderList(providers, radiusKm) {
    if (!providersContainer) return;

    let html = `
      <div class="d-flex justify-content-between align-items-center mb-2 pb-1 border-bottom">
        <span class="small fw-bold text-dark">
          <i class="fas fa-list-check text-primary me-1"></i> ${providers.length} Nearby ${serviceType === 'fuel' ? 'Fuel Station(s)' : 'Provider(s)'} (${radiusKm} km radius)
        </span>
        <span class="badge bg-light text-secondary border small">Sorted by Proximity</span>
      </div>
      <div class="provider-cards-stack d-flex flex-column gap-2" style="max-height: 340px; overflow-y: auto;">
    `;

    providers.forEach(p => {
      const isPartner = p.is_partner === true;
      const partnerBadge = isPartner
        ? `<span class="badge bg-success-subtle text-success border border-success-subtle small"><i class="fas fa-certificate me-1"></i>Verified Partner</span>`
        : `<span class="badge bg-light text-secondary border small"><i class="fas fa-map-pin me-1"></i>OSM Mapped</span>`;

      const brandBadge = p.brand ? `<span class="badge bg-warning-subtle text-dark border small"><i class="fas fa-gas-pump text-warning me-1"></i>${escapeHtml(p.brand)}</span>` : '';

      html += `
        <div class="provider-item-card p-3 rounded-3 border bg-white shadow-sm transition-all" id="provider-card-${p.id}" style="cursor: pointer;">
          <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
            <div>
              <h6 class="fw-bold text-dark mb-0">${escapeHtml(p.business_name || p.name)}</h6>
              <div class="mt-1 d-flex flex-wrap gap-1 align-items-center">${partnerBadge} ${brandBadge}</div>
            </div>
            <div class="text-end">
              <span class="badge bg-primary text-white fw-bold px-2 py-1">${p.formatted_distance}</span>
              <div class="text-muted" style="font-size: 0.72rem;">straight-line</div>
            </div>
          </div>
          <div class="small text-muted text-truncate mb-2"><i class="fas fa-location-dot me-1"></i>${escapeHtml(p.address || '')}</div>
          <div class="d-flex justify-content-between align-items-center pt-2 border-top">
            <span class="text-secondary small" style="font-size: 0.75rem;">
              ${p.phone ? `<i class="fas fa-phone me-1"></i>${p.phone}` : '<i class="fas fa-circle-info me-1"></i>Direct Dispatch'}
            </span>
            <button type="button" class="btn btn-sm btn-outline-primary fw-semibold btn-select-card" data-pid="${p.id}">
              <i class="fas fa-check me-1"></i>Select
            </button>
          </div>
        </div>
      `;
    });

    html += `</div>`;
    providersContainer.innerHTML = html;

    // Attach click events to cards
    providers.forEach(p => {
      const card = document.getElementById(`provider-card-${p.id}`);
      if (card) {
        card.addEventListener('click', function () {
          selectProvider(p);
          if (p._marker) {
            p._marker.openPopup();
            map.panTo([p.lat, p.lng]);
          }
        });
      }
    });
  }

  // Render Empty State
  function renderEmptyState(radiusKm) {
    if (!providersContainer) return;
    providersContainer.innerHTML = `
      <div class="text-center py-4 px-3 bg-light rounded-3 border">
        <i class="fas fa-map-location-dot text-muted fs-2 mb-2"></i>
        <h6 class="fw-bold text-dark mb-1">No ${serviceType} providers found in ${radiusKm} km</h6>
        <p class="small text-muted mb-3">Try expanding your search radius to discover stations in surrounding areas.</p>
        <div class="d-flex justify-content-center gap-2">
          <button type="button" class="btn btn-sm btn-outline-primary fw-semibold" id="btn-expand-20">
            <i class="fas fa-maximize me-1"></i>Search 20 km
          </button>
          <button type="button" class="btn btn-sm btn-outline-primary fw-semibold" id="btn-expand-30">
            <i class="fas fa-maximize me-1"></i>Search 30 km
          </button>
        </div>
      </div>
    `;

    const btn20 = document.getElementById('btn-expand-20');
    if (btn20) {
      btn20.onclick = function () {
        currentRadius = 20;
        updateRadiusButtons(20);
        loadNearbyProviders(activeLat, activeLng, 20);
      };
    }
    const btn30 = document.getElementById('btn-expand-30');
    if (btn30) {
      btn30.onclick = function () {
        currentRadius = 30;
        updateRadiusButtons(30);
        loadNearbyProviders(activeLat, activeLng, 30);
      };
    }
  }

  // Handle Provider Selection
  function selectProvider(p) {
    const isPartner = p.is_partner === true;

    if (providerIdInput) {
      providerIdInput.value = isPartner && p.id && !String(p.id).startsWith('osm') ? p.id : '';
    }
    if (providerNameInput) providerNameInput.value = p.business_name || p.name;
    if (providerLatInput) providerLatInput.value = p.lat;
    if (providerLngInput) providerLngInput.value = p.lng;
    if (providerAddressInput) providerAddressInput.value = p.address || '';
    if (providerSourceInput) providerSourceInput.value = isPartner ? 'registered' : 'osm';

    // Highlight selected card
    document.querySelectorAll('.provider-item-card').forEach(c => {
      c.classList.remove('border-primary', 'bg-primary-subtle');
    });
    const card = document.getElementById(`provider-card-${p.id}`);
    if (card) {
      card.classList.add('border-primary', 'bg-primary-subtle');
    }

    // Update banner in form
    if (selectedProviderCard) {
      selectedProviderCard.classList.remove('d-none');
    }
    if (selectedProviderNameText) {
      selectedProviderNameText.innerText = p.business_name || p.name;
    }
    if (selectedProviderMetaText) {
      const typeLabel = isPartner ? 'Verified MotoServe Partner' : 'OpenStreetMap Verified Station';
      const brandBadge = p.brand ? `<span class="badge bg-warning-subtle text-dark border me-1"><i class="fas fa-gas-pump text-warning me-1"></i>${escapeHtml(p.brand)}</span>` : '';
      selectedProviderMetaText.innerHTML = `${brandBadge}<span class="badge ${isPartner ? 'bg-success' : 'bg-secondary'} me-1">${typeLabel}</span> Straight-line: <strong>${p.formatted_distance}</strong>`;
    }
  }

  // Clear Selected Provider
  if (btnClearProvider) {
    btnClearProvider.addEventListener('click', function () {
      if (providerIdInput) providerIdInput.value = '';
      if (providerNameInput) providerNameInput.value = '';
      if (providerLatInput) providerLatInput.value = '';
      if (providerLngInput) providerLngInput.value = '';
      if (providerAddressInput) providerAddressInput.value = '';
      if (providerSourceInput) providerSourceInput.value = 'registered';

      if (selectedProviderCard) selectedProviderCard.classList.add('d-none');
      document.querySelectorAll('.provider-item-card').forEach(c => {
        c.classList.remove('border-primary', 'bg-primary-subtle');
      });
    });
  }

  // Radius Buttons Toolbar
  function updateRadiusButtons(activeR) {
    document.querySelectorAll('.btn-radius-choice').forEach(btn => {
      const r = parseInt(btn.getAttribute('data-radius'));
      if (r === activeR) {
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-primary', 'text-white');
      } else {
        btn.classList.remove('btn-primary', 'text-white');
        btn.classList.add('btn-outline-secondary');
      }
    });
  }

  document.querySelectorAll('.btn-radius-choice').forEach(btn => {
    btn.addEventListener('click', function () {
      const r = parseInt(this.getAttribute('data-radius')) || 10;
      currentRadius = r;
      updateRadiusButtons(r);
      loadNearbyProviders(activeLat, activeLng, r);
    });
  });

  // User Marker Drag & Map Click
  userMarker.on('dragend', function (e) {
    const coord = e.target.getLatLng();
    setLocation(coord.lat, coord.lng);
  });

  map.on('click', function (e) {
    setLocation(e.latlng.lat, e.latlng.lng);
  });

  // Location Toolbar (GPS auto-detection, Pincode, Address Search, City Presets)
  setupEnhancedLocationToolbar(map, setLocation);

  // Auto-request Geolocation on page load if user hasn't chosen coordinates yet
  autoDetectGeolocation(setLocation);
}

// Helper: Escape HTML
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Enhanced Location Toolbar Setup
function setupEnhancedLocationToolbar(map, setLocationCallback) {
  const btnCurrentLoc = document.getElementById('btn-current-location');
  const pincodeInput = document.getElementById('map-pincode-input');
  const btnPincodeSearch = document.getElementById('btn-pincode-search');
  const manualInput = document.getElementById('map-manual-input');
  const btnManualSearch = document.getElementById('btn-manual-search');

  const btnPresetMysuru = document.getElementById('btn-preset-mysuru');
  const btnPresetBengaluru = document.getElementById('btn-preset-bengaluru');

  const feedbackAlert = document.getElementById('location-feedback-alert');
  const feedbackText = document.getElementById('feedback-text');
  const feedbackIcon = document.getElementById('feedback-icon');

  function showFeedback(type, message) {
    if (!feedbackAlert || !feedbackText) return;
    feedbackAlert.className = `alert alert-${type} py-2 px-3 mt-2 mb-0 d-flex align-items-center gap-2 small`;
    feedbackAlert.classList.remove('d-none');
    feedbackText.innerText = message;
    if (feedbackIcon) {
      if (type === 'success') feedbackIcon.className = 'fas fa-circle-check text-success flex-shrink-0';
      else if (type === 'danger') feedbackIcon.className = 'fas fa-circle-xmark text-danger flex-shrink-0';
      else if (type === 'warning') feedbackIcon.className = 'fas fa-triangle-exclamation text-warning flex-shrink-0';
      else feedbackIcon.className = 'fas fa-circle-info text-info flex-shrink-0';
    }
  }

  // 1. Current Location Button
  if (btnCurrentLoc) {
    btnCurrentLoc.addEventListener('click', function (e) {
      e.preventDefault();
      triggerGeolocation(btnCurrentLoc, setLocationCallback, showFeedback);
    });
  }

  // 2. City Shortcuts for Testing & Quick Switching
  if (btnPresetMysuru) {
    btnPresetMysuru.addEventListener('click', function (e) {
      e.preventDefault();
      setLocationCallback(12.2958, 76.6394, 'Mysuru, Karnataka', true);
      showFeedback('success', 'Location set to Mysuru, Karnataka (12.2958, 76.6394). Nearby providers loaded!');
    });
  }
  if (btnPresetBengaluru) {
    btnPresetBengaluru.addEventListener('click', function (e) {
      e.preventDefault();
      setLocationCallback(12.9716, 77.5946, 'Bengaluru, Karnataka', true);
      showFeedback('success', 'Location set to Bengaluru, Karnataka (12.9716, 77.5946). Nearby providers loaded!');
    });
  }

  // 3. Pincode Search
  function executePincode() {
    if (!pincodeInput) return;
    const pincode = pincodeInput.value.trim();
    if (!pincode) {
      showFeedback('warning', 'Please enter a pincode/postal code.');
      pincodeInput.focus();
      return;
    }

    const originalBtn = btnPincodeSearch.innerHTML;
    btnPincodeSearch.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
    btnPincodeSearch.disabled = true;

    fetch(`/api/location/search?q=${encodeURIComponent(pincode + ', India')}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.results && data.results.length > 0) {
          const item = data.results[0];
          setLocationCallback(item.lat, item.lng, item.display_name, true);
          showFeedback('success', `Pincode ${pincode} located: ${item.display_name}`);
        } else {
          showFeedback('danger', `No location found for pincode "${pincode}". Try place name search.`);
        }
      })
      .catch(err => {
        showFeedback('danger', 'Error resolving pincode. Please try again.');
      })
      .finally(() => {
        btnPincodeSearch.innerHTML = originalBtn;
        btnPincodeSearch.disabled = false;
      });
  }

  if (btnPincodeSearch) btnPincodeSearch.addEventListener('click', executePincode);
  if (pincodeInput) {
    pincodeInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); executePincode(); }
    });
  }

  // 4. Manual Address Search
  function executeAddressSearch() {
    if (!manualInput) return;
    const query = manualInput.value.trim();
    if (!query) {
      showFeedback('warning', 'Please type a location name, landmark, or street.');
      manualInput.focus();
      return;
    }

    const originalBtn = btnManualSearch.innerHTML;
    btnManualSearch.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
    btnManualSearch.disabled = true;

    fetch(`/api/location/search?q=${encodeURIComponent(query)}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.results && data.results.length > 0) {
          const item = data.results[0];
          setLocationCallback(item.lat, item.lng, item.display_name, true);
          showFeedback('success', `Location found: ${item.display_name}`);
        } else {
          showFeedback('info', `Could not find exact coordinates for "${query}". You can drag or click the map pin.`);
        }
      })
      .catch(err => {
        showFeedback('danger', 'Error searching location. Please check connection.');
      })
      .finally(() => {
        btnManualSearch.innerHTML = originalBtn;
        btnManualSearch.disabled = false;
      });
  }

  if (btnManualSearch) btnManualSearch.addEventListener('click', executeAddressSearch);
  if (manualInput) {
    manualInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); executeAddressSearch(); }
    });
  }
}

// Trigger Geolocation API
function triggerGeolocation(btnEl, setLocationCallback, feedbackCallback) {
  if (!navigator.geolocation) {
    if (feedbackCallback) feedbackCallback('danger', 'Geolocation is not supported by your browser.');
    return;
  }

  const origHtml = btnEl ? btnEl.innerHTML : '';
  if (btnEl) {
    btnEl.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Detecting GPS...';
    btnEl.disabled = true;
  }

  navigator.geolocation.getCurrentPosition(
    function (position) {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      setLocationCallback(lat, lng, null, true);
      if (feedbackCallback) {
        feedbackCallback('success', `Actual GPS location detected (${lat.toFixed(4)}, ${lng.toFixed(4)}). Map and nearby providers updated!`);
      }
      if (btnEl) {
        btnEl.innerHTML = origHtml;
        btnEl.disabled = false;
      }
    },
    function (error) {
      let msg = "Could not access GPS.";
      if (error.code === 1) msg = "Location permission denied. Please allow location access or choose a city/search below.";
      else if (error.code === 2) msg = "GPS position unavailable. Please search by pincode or click on the map.";
      else if (error.code === 3) msg = "Location request timed out. Please try again or search manually.";

      if (feedbackCallback) feedbackCallback('warning', msg);
      if (btnEl) {
        btnEl.innerHTML = origHtml;
        btnEl.disabled = false;
      }
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
  );
}

// Automatically attempt Geolocation on initial page load
function autoDetectGeolocation(setLocationCallback) {
  if (!navigator.geolocation) return;

  navigator.geolocation.getCurrentPosition(
    function (position) {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      setLocationCallback(lat, lng, null, true);
    },
    function (err) {
      // Permission denied or unavailable on page load:
      // Leave map at current pin and fetch nearby providers for current coordinates
      const latEl = document.getElementById('pickup_lat');
      const lngEl = document.getElementById('pickup_lng');
      const currentLat = latEl && latEl.value ? parseFloat(latEl.value) : 12.2958;
      const currentLng = lngEl && lngEl.value ? parseFloat(lngEl.value) : 76.6394;
      setLocationCallback(currentLat, currentLng, null, false);
    },
    { enableHighAccuracy: false, timeout: 5000, maximumAge: 60000 }
  );
}

// Form Double-Submit Protection
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function () {
      const submitBtn = this.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        const text = submitBtn.innerHTML;
        setTimeout(() => {
          submitBtn.disabled = true;
          submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Submitting Booking...`;
        }, 50);
      }
    });
  });
});
