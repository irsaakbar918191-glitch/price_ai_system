const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatMessages = document.getElementById('chatMessages');
const searchResults = document.getElementById('searchResults');

function appendMessage(role, text) {
  const message = document.createElement('div');
  message.className = `chat-message ${role === 'user' ? 'chat-user' : 'chat-ai'}`;
  message.textContent = text;
  chatMessages.appendChild(message);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderProducts(products) {
  if (!searchResults) return;
  searchResults.innerHTML = '';

  products.forEach((product) => {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.innerHTML = `
      <div class="flex justify-between items-center">
        <h3 class="text-lg font-semibold text-white">${product.product_name}</h3>
        <span class="price-pill bg-green-500/20 text-green-300">${product.currency} ${Number(product.price || 0).toFixed(2)}</span>
      </div>
      <div class="mt-2 text-sm text-slate-300">
        <p>Model: ${product.model || 'N/A'}</p>
        <p>Supplier: ${product.supplier || 'N/A'}</p>
        <p>Date: ${product.date || 'N/A'}</p>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        ${(product.history || []).slice(0, 5).map((item) => `
          <span class="price-pill bg-slate-700 text-slate-200">${item.currency || product.currency} ${Number(item.price || 0).toFixed(2)}</span>
        `).join('')}
      </div>
    `;
    searchResults.appendChild(card);
  });
}

if (chatForm && chatInput && chatMessages) {
  chatForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    appendMessage('user', query);
    chatInput.value = '';

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('price_ai_token') || ''}`
        },
        body: JSON.stringify({ query })
      });

      if (response.status === 401) {
        handleAuthFailure();
        return;
      }

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Search failed');
      appendMessage('ai', data.answer || 'No answer found.');
      renderProducts(data.products || []);
    } catch (error) {
      appendMessage('ai', error.message);
    }
  });
}
