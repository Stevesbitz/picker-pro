(() => {
  const form = document.getElementById('adminLoginForm');
  if (!form) return;
  const input = document.getElementById('adminKeyInput');
  const status = document.getElementById('adminAuthStatus');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const passkey = input.value.trim();
    if (!passkey) return;
    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passkey })
      });
      if (response.ok) window.location.href = '/admin';
      else {
        status.textContent = 'Invalid passkey.';
        window.showErrorToast(Object.assign(new Error(), { status: response.status }), 'Invalid passkey.');
      }
    } catch (error) {
      status.textContent = 'Login failed.';
      window.showErrorToast(error, 'Login failed. Please try again.');
    }
  });
})();
