(() => {
  const input = document.getElementById('newRoomInput');
  const button = document.getElementById('createRoomBtn');
  const status = document.getElementById('status');
  if (!button) return;

  async function createRoom() {
    const name = input.value.trim();
    if (!name) {
      status.textContent = 'Enter a team name to create a room.';
      window.showToast('Enter a team name to create a room.');
      return;
    }
    button.disabled = true;
    try {
      const response = await fetch('/api/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      if (!response.ok) throw new Error('Unable to create room');
      window.location.assign((await response.json()).share_url);
    } catch (error) {
      status.textContent = 'Unable to create the room. Please try again.';
      window.showErrorToast(error, 'Unable to create the room. Please try again.');
      button.disabled = false;
    }
  }

  button.addEventListener('click', createRoom);
  input.addEventListener('keydown', (event) => { if (event.key === 'Enter') createRoom(); });
})();
