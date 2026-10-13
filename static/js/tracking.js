/* MotoServe 360 - Live Provider & Customer Tracking Integration */

function startLiveTracking(requestId, mapId) {
  const mapContainer = document.getElementById(mapId);
  if (!mapContainer) return;

  let map = null;
  const customerIcon = createCustomIcon('fas fa-street-view', '#2563eb');

  let custMarker = null;
  let provMarker = null;
  let polyline = null;
  let hasCentered = false;

  function pollTrackingData() {
    fetch(`/customer/tracking/status/${requestId}`)
      .then(res => res.json())
      .then(data => {
        // Update Status Badge
        const statusBadge = document.getElementById('tracking-status-badge');
        if (statusBadge && data.status) {
          statusBadge.innerText = data.status.toUpperCase();
          statusBadge.className = `badge badge-status badge-${data.status} fs-6`;
        }

        const pLat = data.pickup_lat;
        const pLng = data.pickup_lng;
        if (!pLat || !pLng) return;

        // Initialize Map centered on customer's actual coordinates
        if (!map) {
          map = initMap(mapId, pLat, pLng, 14);
        }

        if (!custMarker) {
          custMarker = L.marker([pLat, pLng], { icon: customerIcon })
            .addTo(map)
            .bindPopup(`<strong>Your Service Location</strong><br><small>${data.pickup_address || ''}</small>`);
          if (!hasCentered) {
            map.setView([pLat, pLng], 14);
            hasCentered = true;
          }
        } else {
          custMarker.setLatLng([pLat, pLng]);
        }

        // When provider/station data is connected
        if (data.provider && data.provider.lat && data.provider.lng) {
          const provLat = data.provider.lat;
          const provLng = data.provider.lng;
          const provName = data.provider.business_name || data.provider.name;
          const provDist = data.distance_km ? `${Number(data.distance_km).toFixed(1)} km away` : '';
          const sType = data.service_type || 'fuel';

          // Select appropriate icon and color based on service
          const iconClass = sType === 'fuel' ? 'fas fa-gas-pump' : sType === 'repair' ? 'fas fa-wrench' : 'fas fa-truck-pickup';
          const iconColor = sType === 'fuel' ? '#f59e0b' : sType === 'repair' ? '#0284c7' : '#ef4444';
          const isRegistered = data.provider.source === 'registered';
          const providerIcon = createCustomIcon(iconClass, iconColor, isRegistered);

          const badgeLabel = sType === 'fuel' ? 'Connected Fuel Station' : sType === 'repair' ? 'Connected Garage' : 'Connected Tow Truck';

          if (!provMarker) {
            provMarker = L.marker([provLat, provLng], { icon: providerIcon })
              .addTo(map)
              .bindPopup(`
                <div style="min-width: 180px;">
                  <strong style="color: #1e293b;">${provName}</strong><br>
                  <span class="badge ${isRegistered ? 'bg-success' : 'bg-warning text-dark'} my-1">${badgeLabel}</span><br>
                  <span class="small text-muted"><i class="fas fa-location-dot me-1"></i>${data.provider.phone || 'Location on map'}</span><br>
                  <strong class="text-primary small">${provDist}</strong>
                </div>
              `);
          } else {
            provMarker.setLatLng([provLat, provLng]);
          }

          // Draw Connecting Route Polyline between Customer and Station
          if (polyline) map.removeLayer(polyline);
          polyline = L.polyline([[pLat, pLng], [provLat, provLng]], {
            color: iconColor,
            weight: 4,
            dashArray: '8, 8',
            opacity: 0.9
          }).addTo(map);

          // Fit map bounds so both customer and station are clearly visible
          try {
            const bounds = L.latLngBounds([ [pLat, pLng], [provLat, provLng] ]);
            map.fitBounds(bounds, { padding: [60, 60], maxZoom: 15 });
          } catch (e) {}

          // Dynamically update right sidebar card if it was showing the searching spinner
          const providerBox = document.getElementById('assigned-provider-box');
          const searchingPlaceholder = document.getElementById('provider-searching-state');
          if (providerBox && searchingPlaceholder) {
            providerBox.innerHTML = `
              <div class="d-flex align-items-start gap-3 mb-3">
                <div class="rounded-circle ${sType === 'fuel' ? 'bg-warning text-dark' : sType === 'repair' ? 'bg-primary text-white' : 'bg-danger text-white'} bg-opacity-25 p-3 fs-3 d-flex align-items-center justify-content-center" style="width: 52px; height: 52px;">
                  <i class="${iconClass}"></i>
                </div>
                <div>
                  <h6 class="fw-bold text-dark mb-1">${provName}</h6>
                  <span class="badge bg-success-subtle text-success border border-success-subtle small mb-1">
                    <i class="fas fa-link me-1"></i>${badgeLabel}
                  </span>
                  <div class="small text-muted mt-1"><i class="fas fa-location-dot me-1"></i>${data.provider.phone || 'Location on map'}</div>
                  ${provDist ? `<div class="small text-primary fw-semibold mt-1"><i class="fas fa-route me-1"></i>Distance: ${provDist}</div>` : ''}
                </div>
              </div>
              <div class="alert alert-info py-2 px-3 small mb-0">
                <i class="fas fa-satellite-dish me-1"></i>
                Connected via OpenStreetMap. Route polyline displayed on live map.
              </div>
            `;
          }
        }
      })
      .catch(err => console.error("Tracking poll error:", err));
  }

  pollTrackingData();
  setInterval(pollTrackingData, 4000);
}
