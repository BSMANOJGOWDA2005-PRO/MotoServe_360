/* MotoServe 360 - Chart.js Visualizations */

function initAdminCharts() {
  const servicePieCanvas = document.getElementById('servicesPieChart');
  const revenueLineCanvas = document.getElementById('revenueLineChart');

  if (!servicePieCanvas || !revenueLineCanvas) return;

  fetch('/admin/analytics-data')
    .then(res => res.json())
    .then(data => {
      // 1. Services Distribution Donut Chart
      new Chart(servicePieCanvas, {
        type: 'doughnut',
        data: {
          labels: ['Fuel Delivery', 'Vehicle Repair', 'Towing Service'],
          datasets: [{
            data: [data.services.fuel, data.services.repair, data.services.tow],
            backgroundColor: ['#f59e0b', '#3b82f6', '#ef4444'],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom', labels: { color: '#94a3b8' } }
          }
        }
      });

      // 2. Revenue Growth Line Chart
      new Chart(revenueLineCanvas, {
        type: 'line',
        data: {
          labels: data.revenue.labels,
          datasets: [{
            label: 'Monthly Revenue (₹)',
            data: data.revenue.data,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.15)',
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
          },
          plugins: {
            legend: { labels: { color: '#94a3b8' } }
          }
        }
      });
    });
}
