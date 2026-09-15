(() => {
  const toastContainer = document.getElementById('toastContainer');

  window.showToast = (message, type = 'error') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.textContent = message;
    toastContainer.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('visible'));
    window.setTimeout(() => {
      toast.classList.remove('visible');
      window.setTimeout(() => toast.remove(), 200);
    }, 4500);
  };

  window.showErrorToast = (error, fallback) => {
    const status = error?.status;
    const messages = {
      400: 'Please check the information and try again.',
      401: 'Your session has expired. Please sign in again.',
      404: 'That item could not be found.',
      429: 'Too many requests. Please wait a moment and try again.',
      503: 'This integration is not configured yet.',
    };
    window.showToast(messages[status] || fallback || 'Something went wrong. Please try again.');
  };

  const logout = document.getElementById('adminLogoutBtn');
  if (!logout) return;
  logout.addEventListener('click', async () => {
    try {
      const response = await fetch('/api/admin/logout', { method: 'POST' });
      if (!response.ok) throw Object.assign(new Error(), { status: response.status });
      window.location.href = '/';
    } catch (error) {
      window.showErrorToast(error, 'Unable to log out. Please try again.');
    }
  });
})();
