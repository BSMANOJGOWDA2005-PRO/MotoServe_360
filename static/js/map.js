/* MotoServe 360 - Leaflet Map Integration & Marker Handler */

let mainMap = null;
let userMarker = null;
let providerMarker = null;

function initMap(mapElementId, defaultLat = 12.9716, defaultLng = 77.5946, zoom = 14) {
  const mapContainer = document.getElementById(mapElementId);
  if (!mapContainer) return null;

  mainMap = L.map(mapElementId).setView([defaultLat, defaultLng], zoom);

  // OpenStreetMap Tile Layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(mainMap);

  return mainMap;
}

// Create Custom Icon
function createCustomIcon(iconClass, color) {
  return L.divIcon({
    html: `<div style="background-color: ${color}; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.4); border: 2px solid white;"><i class="${iconClass}"></i></div>`,
    className: 'custom-leaflet-icon',
    iconSize: [36, 36],
    iconAnchor: [18, 18]
  });
}

function fetchPlaceName(lat, lng, addressInputId, manualInputId = 'map-manual-input') {
  if (!addressInputId) return;
  const addressInput = document.getElementById(addressInputId);
  const manualInput = manualInputId ? document.getElementById(manualInputId) : null;
  if (!addressInput && !manualInput) return;

  if (addressInput) addressInput.value = "📍 Fetching location name...";
  if (manualInput) manualInput.value = "📍 Fetching location name...";

  fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`)
    .then(response => response.json())
    .then(data => {
      let resolvedAddress = "";
      if (data && data.display_name) {
        resolvedAddress = data.display_name;
      } else {
        resolvedAddress = `GPS Location: (${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)})`;
      }
      if (addressInput) addressInput.value = resolvedAddress;
      if (manualInput) manualInput.value = resolvedAddress;
    })
    .catch(err => {
      console.warn("Reverse geocoding error:", err);
      const fallback = `GPS Location: (${Number(lat).toFixed(4)}, ${Number(lng).toFixed(4)})`;
      if (addressInput) addressInput.value = fallback;
      if (manualInput) manualInput.value = fallback;
    });
}

function setupLocationToolbar(map, latInputId, lngInputId, addressInputId, marker) {
  const btnCurrentLoc = document.getElementById('btn-current-location');
  const pincodeInput = document.getElementById('map-pincode-input');
  const btnPincodeSearch = document.getElementById('btn-pincode-search');
  const manualInput = document.getElementById('map-manual-input');
  const btnManualSearch = document.getElementById('btn-manual-search');
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

  function updateMapAndInputs(lat, lng, addressName, zoomLevel = 15) {
    marker.setLatLng([lat, lng]);
    map.setView([lat, lng], zoomLevel);

    const latEl = document.getElementById(latInputId);
    const lngEl = document.getElementById(lngInputId);
    const addrEl = document.getElementById(addressInputId);

    if (latEl) latEl.value = Number(lat).toFixed(6);
    if (lngEl) lngEl.value = Number(lng).toFixed(6);

    if (addressName) {
      if (addrEl) addrEl.value = addressName;
      if (manualInput) manualInput.value = addressName;
    } else {
      fetchPlaceName(lat, lng, addressInputId, 'map-manual-input');
    }
  }

  // 1. Current Location Button (GPS Geolocation)
  if (btnCurrentLoc) {
    btnCurrentLoc.addEventListener('click', function(e) {
      e.preventDefault();
      if (!navigator.geolocation) {
        showFeedback('danger', 'Geolocation is not supported by your browser.');
        return;
      }

      const originalHtml = btnCurrentLoc.innerHTML;
      btnCurrentLoc.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Detecting GPS...';
      btnCurrentLoc.disabled = true;

      navigator.geolocation.getCurrentPosition(
        function(position) {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          updateMapAndInputs(lat, lng, null, 16);
          showFeedback('success', `Current GPS location detected (${lat.toFixed(4)}, ${lng.toFixed(4)}). Map & address updated!`);
          btnCurrentLoc.innerHTML = originalHtml;
          btnCurrentLoc.disabled = false;
        },
        function(error) {
          let errDetail = "Permission denied or unavailable.";
          if (error.code === 1) errDetail = "Location access was denied. Please allow location permissions in your browser.";
          else if (error.code === 2) errDetail = "Position unavailable. Please search by Pincode or type your address.";
          else if (error.code === 3) errDetail = "Location request timed out. Please try again.";
          
          showFeedback('warning', `Could not detect GPS: ${errDetail}`);
          btnCurrentLoc.innerHTML = originalHtml;
          btnCurrentLoc.disabled = false;
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });
  }

  // 2. Search by Pincode
  function executePincodeSearch() {
    if (!pincodeInput) return;
    const pincode = pincodeInput.value.trim();
    if (!pincode) {
      showFeedback('warning', 'Please enter a valid pincode/postal code.');
      pincodeInput.focus();
      return;
    }

    const originalBtnHtml = btnPincodeSearch ? btnPincodeSearch.innerHTML : '';
    if (btnPincodeSearch) {
      btnPincodeSearch.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
      btnPincodeSearch.disabled = true;
    }

    const indiaUrl = `https://nominatim.openstreetmap.org/search?postalcode=${encodeURIComponent(pincode)}&countrycodes=in&format=json&limit=1`;
    fetch(indiaUrl)
      .then(res => res.json())
      .then(data => {
        if (data && data.length > 0) {
          const item = data[0];
          const lat = parseFloat(item.lat);
          const lng = parseFloat(item.lon);
          updateMapAndInputs(lat, lng, item.display_name, 15);
          showFeedback('success', `Pincode ${pincode} located: ${item.display_name}`);
        } else {
          // Global fallback
          return fetch(`https://nominatim.openstreetmap.org/search?postalcode=${encodeURIComponent(pincode)}&format=json&limit=1`)
            .then(res => res.json())
            .then(fallbackData => {
              if (fallbackData && fallbackData.length > 0) {
                const item = fallbackData[0];
                const lat = parseFloat(item.lat);
                const lng = parseFloat(item.lon);
                updateMapAndInputs(lat, lng, item.display_name, 15);
                showFeedback('success', `Pincode ${pincode} located: ${item.display_name}`);
              } else {
                showFeedback('danger', `No location found for pincode "${pincode}". Try manual location search or click on the map.`);
              }
            });
        }
      })
      .catch(err => {
        console.error("Pincode search error:", err);
        showFeedback('danger', 'Error searching pincode. Please check network connection or try again.');
      })
      .finally(() => {
        if (btnPincodeSearch) {
          btnPincodeSearch.innerHTML = originalBtnHtml;
          btnPincodeSearch.disabled = false;
        }
      });
  }

  if (btnPincodeSearch) {
    btnPincodeSearch.addEventListener('click', function(e) {
      e.preventDefault();
      executePincodeSearch();
    });
  }
  if (pincodeInput) {
    pincodeInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        executePincodeSearch();
      }
    });
  }

  // 3. Manual Location Entry
  function executeManualSearch() {
    if (!manualInput) return;
    const query = manualInput.value.trim();
    if (!query) {
      showFeedback('warning', 'Please enter a location name, landmark, or street.');
      manualInput.focus();
      return;
    }

    const originalBtnHtml = btnManualSearch ? btnManualSearch.innerHTML : '';
    if (btnManualSearch) {
      btnManualSearch.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
      btnManualSearch.disabled = true;
    }

    const searchUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`;
    fetch(searchUrl)
      .then(res => res.json())
      .then(data => {
        if (data && data.length > 0) {
          const item = data[0];
          const lat = parseFloat(item.lat);
          const lng = parseFloat(item.lon);
          updateMapAndInputs(lat, lng, item.display_name, 15);
          showFeedback('success', `Location pinned: ${item.display_name}`);
        } else {
          // If Nominatim cannot resolve exact GPS, still update the delivery address with user's manual input
          const addrEl = document.getElementById(addressInputId);
          if (addrEl) addrEl.value = query;
          showFeedback('info', `Address set to "${query}". You can also click on the map to place the exact pin.`);
        }
      })
      .catch(err => {
        console.error("Manual geocoding error:", err);
        const addrEl = document.getElementById(addressInputId);
        if (addrEl) addrEl.value = query;
        showFeedback('info', `Address set to "${query}". You can adjust the pin by clicking the map.`);
      })
      .finally(() => {
        if (btnManualSearch) {
          btnManualSearch.innerHTML = originalBtnHtml;
          btnManualSearch.disabled = false;
        }
      });
  }

  if (btnManualSearch) {
    btnManualSearch.addEventListener('click', function(e) {
      e.preventDefault();
      executeManualSearch();
    });
  }
  if (manualInput) {
    manualInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        executeManualSearch();
      }
    });

    // Keep pickup_address in sync as the user types
    manualInput.addEventListener('input', function() {
      const addrEl = document.getElementById(addressInputId);
      if (addrEl) addrEl.value = manualInput.value;
    });
  }

  // Also sync changes from form address input to manualInput
  const formAddrInput = document.getElementById(addressInputId);
  if (formAddrInput && manualInput) {
    formAddrInput.addEventListener('input', function() {
      manualInput.value = formAddrInput.value;
    });
  }
}

function setPickupLocationPicker(map, latInputId, lngInputId, addressInputId) {
  const customerIcon = createCustomIcon('fas fa-user-pin', '#3b82f6');
  
  const latEl = document.getElementById(latInputId);
  const lngEl = document.getElementById(lngInputId);
  const addrElem = document.getElementById(addressInputId);

  let currentLat = (latEl && parseFloat(latEl.value)) || 12.9716;
  let currentLng = (lngEl && parseFloat(lngEl.value)) || 77.5946;

  userMarker = L.marker([currentLat, currentLng], { icon: customerIcon, draggable: true }).addTo(map);

  const manualInput = document.getElementById('map-manual-input');
  if (manualInput && addrElem && addrElem.value) {
    manualInput.value = addrElem.value;
  }

  // Fetch initial address if not already populated or if placeholder
  if (addrElem && (!addrElem.value || addrElem.value.includes('GPS Location'))) {
    fetchPlaceName(currentLat, currentLng, addressInputId, 'map-manual-input');
  }

  userMarker.on('dragend', function (e) {
    const coord = e.target.getLatLng();
    if (latEl) latEl.value = coord.lat.toFixed(6);
    if (lngEl) lngEl.value = coord.lng.toFixed(6);
    fetchPlaceName(coord.lat, coord.lng, addressInputId, 'map-manual-input');
  });

  map.on('click', function (e) {
    userMarker.setLatLng(e.latlng);
    if (latEl) latEl.value = e.latlng.lat.toFixed(6);
    if (lngEl) lngEl.value = e.latlng.lng.toFixed(6);
    fetchPlaceName(e.latlng.lat, e.latlng.lng, addressInputId, 'map-manual-input');
  });

  // Attach Location Toolbar (Current Location, Pincode, Manual Entry)
  setupLocationToolbar(map, latInputId, lngInputId, addressInputId, userMarker);
}
