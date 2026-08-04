/* MotoServe 360 - In-App Chat Messenger */

function initChatWindow(requestId, currentUserId) {
  const chatMessagesBox = document.getElementById('chat-messages-box');
  const chatForm = document.getElementById('chat-form');
  const messageInput = document.getElementById('chat-input');

  if (!chatMessagesBox || !chatForm) return;

  function loadMessages() {
    fetch(`/customer/chat/${requestId}?json=true`)
      .then(res => res.json())
      .then(messages => {
        chatMessagesBox.innerHTML = '';
        messages.forEach(msg => {
          const isSelf = msg.sender_id === currentUserId;
          const msgClass = isSelf ? 'chat-msg-self' : 'chat-msg-other';
          const alignClass = isSelf ? 'text-end' : 'text-start';

          const bubble = `
            <div class="${alignClass} mb-3">
              <div class="d-inline-block p-3 rounded-3 ${msgClass}" style="max-width: 75%; text-align: left;">
                <div class="fw-bold small mb-1">${msg.sender_name}</div>
                <div>${msg.message}</div>
                <div class="text-end small opacity-75 mt-1" style="font-size: 0.75rem;">${msg.time}</div>
              </div>
            </div>
          `;
          chatMessagesBox.insertAdjacentHTML('beforeend', bubble);
        });
        chatMessagesBox.scrollTop = chatMessagesBox.scrollHeight;
      });
  }

  chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;

    const formData = new FormData();
    formData.append('message', text);

    fetch(`/customer/chat/${requestId}`, {
      method: 'POST',
      body: formData
    }).then(res => res.json()).then(data => {
      if (data.status === 'success') {
        messageInput.value = '';
        loadMessages();
      }
    });
  });

  loadMessages();
  setInterval(loadMessages, 3000);
}
