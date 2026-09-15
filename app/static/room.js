(() => {
  const roomId = document.body.dataset.roomId;
  if (!roomId) return;

  const api = (path) => `/api/rooms/${roomId}${path}`;
  const withPool = (path) => `${path}?pool_id=${encodeURIComponent(activePoolId)}`;
  let activePoolId = 'default';
  let cachedUsers = [];
  let shuffleInterval = null;
  let isPicking = false;

  const userList = document.getElementById('userList');
  const emptyState = document.getElementById('emptyState');
  const newUserInput = document.getElementById('newUserInput');
  const status = document.getElementById('status');
  const pickButton = document.getElementById('pickBtn');
  const notifySlackButton = document.getElementById('notifySlackBtn');
  const resultContainer = document.getElementById('resultContainer');
  const resultName = document.getElementById('resultName');
  const resultTime = document.getElementById('resultTime');
  const modal = document.getElementById('thinkingModal');
  const shufflingName = document.getElementById('shufflingName');
  const poolSelect = document.getElementById('poolSelect');
  const newPoolInput = document.getElementById('newPoolInput');
  const rosterCount = document.getElementById('rosterCount');
  const slackChannelInput = document.getElementById('slackChannelInput');
  const saveSlackChannelButton = document.getElementById('saveSlackChannelBtn');

  async function request(path, options) {
    const response = await fetch(api(path), options);
    if (!response.ok) throw Object.assign(new Error(`Request failed: ${response.status}`), { status: response.status });
    return response;
  }

  async function fetchPools() {
    const pools = await (await request('/pools')).json();
    poolSelect.innerHTML = '';
    pools.forEach((pool) => {
      const option = document.createElement('option');
      option.value = pool.id;
      option.textContent = pool.name;
      poolSelect.appendChild(option);
    });
    if (!pools.some((pool) => pool.id === activePoolId)) activePoolId = pools[0]?.id || 'default';
    poolSelect.value = activePoolId;
  }

  async function fetchState() {
    if (isPicking) return;
    try {
      const state = await (await request(withPool('/state'))).json();
      cachedUsers = state.users;
      render(state);
    } catch (error) {
      console.error('Failed to sync state:', error);
      window.showErrorToast(error, 'Unable to refresh the room. Please try again.');
    }
  }

  function render(state) {
    const { users, last_picked_user: lastPickedUser } = state;
    if (lastPickedUser) {
      resultName.textContent = lastPickedUser.name;
      resultTime.textContent = `Picked on ${new Date(lastPickedUser.picked_at).toLocaleString()}`;
      resultTime.style.display = 'block';
      resultContainer.classList.remove('empty');
      notifySlackButton.disabled = false;
    } else {
      resultName.textContent = 'No one picked yet';
      resultTime.style.display = 'none';
      resultContainer.classList.add('empty');
      notifySlackButton.disabled = true;
    }

    userList.innerHTML = '';
    emptyState.style.display = users.length ? 'none' : 'block';
    rosterCount.textContent = `${users.length} ${users.length === 1 ? 'person' : 'people'}`;
    const eligible = users.filter((user) => user.checked && !user.is_ooo);
    const remaining = eligible.filter((user) => !user.pickedThisRound);
    pickButton.disabled = !eligible.length;
    status.textContent = eligible.length
      ? `${remaining.length} of ${eligible.length} eligible user(s) remaining in round.`
      : 'Check at least one available user to enable selection.';
    pickButton.textContent = remaining.length ? (remaining.length === 1 ? 'Pick last user' : 'Pick next user') : 'Start next round';

    users.forEach((user) => {
      const item = document.createElement('li');
      if (user.pickedThisRound) item.classList.add('picked-round');

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = user.checked;
      checkbox.disabled = user.is_ooo;
      checkbox.id = `chk-${user.id}`;
      checkbox.title = user.is_ooo ? 'Unavailable while out of office' : 'Include in picker';
      checkbox.addEventListener('change', () => updateUser(user.id, { checked: checkbox.checked }));

      const label = document.createElement('label');
      label.htmlFor = checkbox.id;
      label.textContent = user.name;
      if (user.is_ooo) label.classList.add('user-ooo');

      const badge = document.createElement('span');
      badge.className = `badge${user.pickedThisRound ? ' done' : ''}${user.is_ooo ? ' ooo' : ''}`;
      badge.textContent = user.is_ooo ? 'OOO' : (user.pickedThisRound ? 'picked' : 'eligible');

      const oooButton = document.createElement('button');
      oooButton.className = 'btn-secondary ooo-btn';
      oooButton.textContent = user.is_ooo ? 'Return' : 'OOO';
      oooButton.title = user.is_ooo ? 'Mark available' : 'Mark out of office';
      oooButton.addEventListener('click', () => updateUser(user.id, { is_ooo: !user.is_ooo }, '/ooo'));

      const removeButton = document.createElement('button');
      removeButton.className = 'remove-btn';
      removeButton.textContent = '✕';
      removeButton.addEventListener('click', async () => {
        try {
          await request(withPool(`/users/${user.id}`), { method: 'DELETE' });
          fetchState();
        } catch (error) { window.showErrorToast(error, 'Unable to remove this user. Please try again.'); }
      });

      item.append(checkbox, label, badge, oooButton, removeButton);
      userList.appendChild(item);
    });
  }

  async function updateUser(userId, body, suffix = '') {
    try {
      await request(withPool(`/users/${userId}${suffix}`), {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      fetchState();
    } catch (error) {
      window.showErrorToast(error, 'Unable to update this user. Please try again.');
      console.error('Failed to update user:', error);
    }
  }

  function startShuffleAnimation() {
    const names = cachedUsers.filter((user) => user.checked && !user.is_ooo).map((user) => user.name);
    if (!names.length) return;
    modal.classList.add('active');
    shuffleInterval = setInterval(() => { shufflingName.textContent = names[Math.floor(Math.random() * names.length)]; }, 70);
  }

  function stopShuffleAnimation() {
    clearInterval(shuffleInterval);
    modal.classList.remove('active');
  }

  async function addUser() {
    const name = newUserInput.value.trim();
    if (!name) return;
    try {
      await request(withPool('/users'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name })
      });
      newUserInput.value = '';
      fetchState();
    } catch (error) { window.showErrorToast(error, 'Unable to add this user. Please try again.'); }
  }

  async function pickUser() {
    isPicking = true;
    const remaining = cachedUsers.filter((user) => user.checked && !user.is_ooo && !user.pickedThisRound);
    if (remaining.length !== 1) startShuffleAnimation();
    try { await request(withPool('/pick'), { method: 'POST' }); }
    catch (error) { window.showErrorToast(error, 'Unable to choose a user. Please try again.'); }
    finally { stopShuffleAnimation(); isPicking = false; fetchState(); }
  }

  async function addPool() {
    const name = newPoolInput.value.trim();
    if (!name) return;
    try {
      const pool = await (await request('/pools', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name })
      })).json();
      newPoolInput.value = '';
      activePoolId = pool.id;
      await fetchPools();
      fetchState();
    } catch (error) { window.showErrorToast(error, 'Unable to add this task pool. Please try again.'); }
  }

  async function saveSlackChannel() {
    saveSlackChannelButton.disabled = true;
    try {
      await request('/slack-channel', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_id: slackChannelInput.value.trim() })
      });
      status.textContent = slackChannelInput.value.trim() ? 'Slack channel saved.' : 'Room Slack channel cleared.';
    } catch (error) {
      status.textContent = 'Unable to save the Slack channel.';
      window.showErrorToast(error, 'Unable to save the Slack channel. Please try again.');
    } finally {
      saveSlackChannelButton.disabled = false;
    }
  }

  document.getElementById('addUserBtn').addEventListener('click', addUser);
  newUserInput.addEventListener('keydown', (event) => { if (event.key === 'Enter') addUser(); });
  pickButton.addEventListener('click', pickUser);
  document.getElementById('resetRoundBtn').addEventListener('click', async () => {
    try {
      await request(withPool('/reset'), { method: 'POST' });
      fetchState();
    } catch (error) { window.showErrorToast(error, 'Unable to reset the round. Please try again.'); }
  });
  notifySlackButton.addEventListener('click', async () => {
    notifySlackButton.disabled = true;
    try {
      await request(withPool('/notify-slack'), { method: 'POST' });
      status.textContent = 'Slack notification sent.';
    } catch (error) {
      status.textContent = error.message.includes('503')
        ? 'Slack notifications are not configured.'
        : 'Unable to send the Slack notification.';
      window.showErrorToast(error, status.textContent);
      notifySlackButton.disabled = false;
    }
  });
  document.getElementById('copyLinkBtn').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(document.getElementById('shareLink').value);
      document.getElementById('copyLinkBtn').textContent = 'Copied';
    } catch (error) { window.showErrorToast(error, 'Unable to copy the room link. Please try again.'); }
  });
  poolSelect.addEventListener('change', () => { activePoolId = poolSelect.value; fetchState(); });
  document.getElementById('addPoolBtn').addEventListener('click', addPool);
  newPoolInput.addEventListener('keydown', (event) => { if (event.key === 'Enter') addPool(); });
  saveSlackChannelButton.addEventListener('click', saveSlackChannel);

  fetchPools().then(fetchState).catch((error) => { status.textContent = 'Unable to load task pools.'; console.error(error); });
  setInterval(fetchState, 2500);
})();
