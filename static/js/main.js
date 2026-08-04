/* MotoServe 360 - Global Utilities & Toast Notifications */

document.addEventListener("DOMContentLoaded", function () {
  console.log("🚀 MotoServe 360 Core initialized.");

  // Auto-dismiss Flash Alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });
});

// Toast notification helper
function showToast(title, message, type = 'info') {
  const toastContainer = document.getElementById('toast-container');
  if (!toastContainer) return;

  const toastId = 'toast-' + Date.now();
  const toastHtml = `
    <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">
          <strong>${title}</strong><br>${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;
  toastContainer.insertAdjacentHTML('beforeend', toastHtml);
  const toastElem = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastElem, { delay: 4000 });
  toast.show();
}
