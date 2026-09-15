(() => {
  const list = document.getElementById('adminSessionsList');
  if (!list) return;
  const totalRooms = document.getElementById('statTotalRooms');
  const totalUsers = document.getElementById('statTotalUsers');
  const activeSessions = document.getElementById('statActiveSessions');
  const slackStatus = document.getElementById('slackStatus');
  const storageStatus = document.getElementById('storageStatus');
  const databaseStatus = document.getElementById('databaseStatus');

  document.querySelectorAll('.admin-nav-item').forEach((item) => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.admin-nav-item').forEach((navItem) => navItem.classList.remove('active'));
      document.querySelectorAll('.admin-section').forEach((section) => section.classList.remove('active'));
      item.classList.add('active');
      document.getElementById(item.dataset.section).classList.add('active');
    });
  });

  async function fetchAdminData() {
    try {
      const response = await fetch('/api/admin/sessions');
      if (response.status === 401) {
        window.location.href = '/admin/login';
        return;
      }
      if (!response.ok) throw Object.assign(new Error(), { status: response.status });
      const data = await response.json();
      totalRooms.textContent = data.rooms.length;
      totalUsers.textContent = data.rooms.reduce((total, room) => total + room.user_count, 0);
      activeSessions.textContent = data.active_sessions || data.rooms.length;
      list.innerHTML = '';
      if (!data.rooms.length) {
        list.innerHTML = '<tr><td colspan="5" class="empty-state">No active sessions found.</td></tr>';
        return;
      }
      data.rooms.forEach((room) => {
        const row = document.createElement('tr');
        row.innerHTML = `<td><code>${room.id}</code></td><td><strong>${room.name}</strong></td><td>${room.user_count}</td><td>${room.last_picked || '—'}</td><td><a href="/rooms/${room.id}" class="btn-secondary join-link">Join</a></td>`;
        list.appendChild(row);
      });
    } catch (error) {
      window.showErrorToast(error, 'Unable to load room sessions. Please try again.');
      console.error('Error fetching admin data:', error);
    }
  }

  async function fetchSystemStatus() {
    try {
      const response = await fetch('/api/admin/system');
      if (response.status === 401) {
        window.location.href = '/admin/login';
        return;
      }
      if (!response.ok) throw Object.assign(new Error(), { status: response.status });
      const data = await response.json();
      slackStatus.textContent = data.slack_configured ? 'Connected' : 'Not configured';
      slackStatus.className = `status-pill ${data.slack_configured ? 'status-good' : 'status-neutral'}`;
      storageStatus.textContent = data.storage_backend.replace('RoomStore', ' storage').replace('Memory', 'Memory');
      storageStatus.className = 'status-pill status-good';
      databaseStatus.textContent = data.database_configured ? 'Configured' : 'In-memory mode';
      databaseStatus.className = `status-pill ${data.database_configured ? 'status-good' : 'status-neutral'}`;
    } catch (error) {
      window.showErrorToast(error, 'Unable to load system status. Please try again.');
    }
  }

  fetchAdminData();
  fetchSystemStatus();
  setInterval(fetchAdminData, 5000);
  setInterval(fetchSystemStatus, 15000);
})();
