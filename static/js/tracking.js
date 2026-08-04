/* MotoServe 360 - Live Provider Tracking Simulation */

function startLiveTracking(requestId, mapId) {
  const map = initMap(mapId, 12.9716, 77.5946, 14);
  if (!map) return;

  const customerIcon = createCustomIcon('fas fa-street-view', '#3b82f6');
  const providerIcon = createCustomIcon('fas fa-truck-monster', '#f59e0b');

  let custMarker = null;
  let provMarker = null;
  let polyline = null;

  function pollTrackingData() {
    fetch(`/customer/tracking/status/${requestId}`)
      .then(res => res.json())
      .then(data => {
        // Update Status Badge
        const statusBadge = document.getElementById('tracking-status-badge');
        if (statusBadge) {
          statusBadge.innerText = data.status.toUpperCase();
          statusBadge.className = `badge badge-status badge-${data.status}`;
        }

        const pLat = data.pickup_lat;
        const pLng = data.pickup_lng;

        if (!custMarker) {
          custMarker = L.marker([pLat, pLng], { icon: customerIcon }).addTo(map).bindPopup("Your Location");
          map.setView([pLat, pLng], 14);
        }

        if (data.provider) {
          const provLat = data.provider.lat;
          const provLng = data.provider.lng;

          if (!provMarker) {
            provMarker = L.marker([provLat, provLng], { icon: providerIcon }).addTo(map).bindPopup(`Provider: ${data.provider.business_name}`);
          } else {
            provMarker.setLatLng([provLat, provLng]);
          }

          // Draw Route Line
          if (polyline) map.removeLayer(polyline);
          polyline = L.polyline([[pLat, pLng], [provLat, provLng]], { color: '#3b82f6', weight: 4, dashArray: '8, 8' }).addTo(map);
        }
      })
      .catch(err => console.error("Tracking poll error:", err));
  }

  pollTrackingData();
  setInterval(pollTrackingData, 4000);
}
