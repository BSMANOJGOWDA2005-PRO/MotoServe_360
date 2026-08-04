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

function fetchPlaceName(lat, lng, addressInputId) {
  if (!addressInputId) return;
  const addressInput = document.getElementById(addressInputId);
  if (!addressInput) return;

  addressInput.value = "📍 Fetching location name...";

  fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`)
    .then(response => response.json())
    .then(data => {
      if (data && data.display_name) {
        addressInput.value = data.display_name;
      } else {
        addressInput.value = `GPS Location: (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
      }
    })
    .catch(err => {
      console.warn("Reverse geocoding error:", err);
      addressInput.value = `GPS Location: (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
    });
}

function setPickupLocationPicker(map, latInputId, lngInputId, addressInputId) {
  const customerIcon = createCustomIcon('fas fa-user-pin', '#3b82f6');
  
  let currentLat = parseFloat(document.getElementById(latInputId).value) || 12.9716;
  let currentLng = parseFloat(document.getElementById(lngInputId).value) || 77.5946;

  userMarker = L.marker([currentLat, currentLng], { icon: customerIcon, draggable: true }).addTo(map);

  // Fetch initial address if not already populated
  const addrElem = document.getElementById(addressInputId);
  if (addrElem && (!addrElem.value || addrElem.value.includes('GPS Location'))) {
    fetchPlaceName(currentLat, currentLng, addressInputId);
  }

  userMarker.on('dragend', function (e) {
    const coord = e.target.getLatLng();
    document.getElementById(latInputId).value = coord.lat.toFixed(6);
    document.getElementById(lngInputId).value = coord.lng.toFixed(6);
    fetchPlaceName(coord.lat, coord.lng, addressInputId);
  });

  map.on('click', function (e) {
    userMarker.setLatLng(e.latlng);
    document.getElementById(latInputId).value = e.latlng.lat.toFixed(6);
    document.getElementById(lngInputId).value = e.latlng.lng.toFixed(6);
    fetchPlaceName(e.latlng.lat, e.latlng.lng, addressInputId);
  });
}
