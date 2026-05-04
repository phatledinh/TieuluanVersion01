import './style.css';

// Base URL for API Gateway
const API_BASE_URL = 'http://localhost';

// State
let token = localStorage.getItem('jwt_token');

// DOM Elements
const authLink = document.getElementById('auth-link');
const productGrid = document.getElementById('product-grid');
const chatbotToggle = document.getElementById('chatbot-toggle');
const chatbotWindow = document.getElementById('chatbot-window');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  if (productGrid) fetchProducts();
  setupChatbot();
});

// Update Auth UI
function updateAuthUI() {
  if (token) {
    if(authLink) {
      authLink.textContent = 'Logout';
      authLink.href = '#';
      authLink.addEventListener('click', (e) => {
        e.preventDefault();
        localStorage.removeItem('jwt_token');
        token = null;
        updateAuthUI();
        window.location.reload();
      });
    }
  } else {
    if(authLink) {
      authLink.textContent = 'Login';
      authLink.href = '/login.html';
    }
  }
}

// Fetch Products
async function fetchProducts() {
  try {
    const response = await fetch(`${API_BASE_URL}/products/`);
    if (!response.ok) throw new Error('Failed to fetch products');
    const data = await response.json();
    
    // Handle Django Rest Framework pagination format { count, next, previous, results: [...] }
    const productsArray = data.results ? data.results : data;
    renderProducts(productsArray);
  } catch (error) {
    console.error('Error fetching products:', error);
    if(productGrid) {
      productGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; color: var(--danger);">
          Không thể tải sản phẩm. Vui lòng kiểm tra API Gateway.
        </div>
      `;
    }
  }
}

// Render Products
function renderProducts(products) {
  if (!productGrid) return;
  if (!products || products.length === 0) {
    productGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center;">Không tìm thấy sản phẩm nào.</div>';
    return;
  }

  productGrid.innerHTML = products.map((product, index) => {
    const price = product.price ? parseInt(product.price).toLocaleString('vi-VN') + ' ₫' : '0 ₫';
    const catName = product.category_name || product.category || '';
    return `
    <div class="product-card" style="animation: fadeIn 0.5s ease forwards; animation-delay: ${index * 0.08}s; opacity: 0;">
      <div class="product-image">
        <span style="font-size: 3rem;">🛍️</span>
      </div>
      <div class="product-details">
        <h3 class="product-title">${product.name || product.title || 'Sản phẩm'}</h3>
        <p class="product-category" style="font-size: 0.85rem;">${catName}</p>
        <p class="product-price">${price}</p>
        <button class="btn btn-primary" style="width: 100%" onclick="window.addToCart(${product.id})">Thêm vào giỏ</button>
      </div>
    </div>
  `;
  }).join('');
}

// Add to Cart
window.addToCart = async (productId) => {
  if (!token) {
    alert('Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng.');
    window.location.href = '/login.html';
    return;
  }
  
  try {
    // Calling cart-service via API Gateway
    const response = await fetch(`${API_BASE_URL}/carts/add/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ product_id: productId, quantity: 1 })
    });
    
    if (response.ok) {
      alert(`Đã thêm sản phẩm vào giỏ hàng!`);
    } else {
      console.warn('Cart API not ready, simulating add.');
      alert(`Đã thêm sản phẩm vào giỏ hàng (mô phỏng).`);
    }
  } catch (err) {
    console.error('Error adding to cart', err);
    alert('Đã thêm sản phẩm vào giỏ hàng (mô phỏng).');
  }
};

// --- CART LOGIC ---
export async function fetchCart() {
  const cartContent = document.getElementById('cart-content');
  if (!cartContent) return;

  try {
    const response = await fetch(`${API_BASE_URL}/carts/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (!response.ok) throw new Error('Cart API failed');
    const data = await response.json();
    // Expected data format: { items: [...], total: 100 }
    renderCartItems(data.items || [], data.total || 0);
  } catch (err) {
    console.warn('Simulating cart items due to API error', err);
    // Mock data for UI demonstration
    const mockItems = [
      { id: 1, name: 'Wireless Headphones', price: 99.99, quantity: 1 },
      { id: 2, name: 'Mechanical Keyboard', price: 149.50, quantity: 2 }
    ];
    renderCartItems(mockItems, 398.99);
  }
}

export function renderCartItems(items, total) {
  const cartContent = document.getElementById('cart-content');
  const cartSubtotal = document.getElementById('cart-subtotal');
  const cartTax = document.getElementById('cart-tax');
  const cartTotal = document.getElementById('cart-total');
  
  if (!cartContent) return;

  if (items.length === 0) {
    cartContent.innerHTML = '<p style="text-align:center; padding: 2rem 0;">Your cart is empty.</p>';
    return;
  }

  cartContent.innerHTML = items.map(item => `
    <div class="cart-item">
      <div class="cart-item-img">📦</div>
      <div class="cart-item-details">
        <div class="cart-item-title">${item.name || 'Product ' + item.id}</div>
        <div class="cart-item-price">$${parseFloat(item.price).toFixed(2)}</div>
      </div>
      <div class="cart-item-actions">
        <div class="quantity-control">
          <button class="qty-btn">-</button>
          <span>${item.quantity}</span>
          <button class="qty-btn">+</button>
        </div>
        <button class="remove-btn">Remove</button>
      </div>
    </div>
  `).join('');

  const tax = total * 0.1;
  const grandTotal = total + tax;
  
  if(cartSubtotal) cartSubtotal.textContent = `$${parseFloat(total).toFixed(2)}`;
  if(cartTax) cartTax.textContent = `$${parseFloat(tax).toFixed(2)}`;
  if(cartTotal) cartTotal.textContent = `$${parseFloat(grandTotal).toFixed(2)}`;
}

// --- CHECKOUT LOGIC ---
export function handleCheckout() {
  const shippingForm = document.getElementById('shipping-form');
  const paymentForm = document.getElementById('payment-form');
  const stepShipping = document.getElementById('step-shipping');
  const stepPayment = document.getElementById('step-payment');
  const stepSuccess = document.getElementById('step-success');
  const displayName = document.getElementById('display-name');

  if (shippingForm) {
    shippingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('fullName').value;
      if(displayName) displayName.textContent = name.toUpperCase() || 'JOHN DOE';
      
      const btn = document.getElementById('continue-btn');
      btn.textContent = 'Processing...';
      btn.disabled = true;

      // Simulate Order Creation API call (POST /orders/)
      try {
        await fetch(`${API_BASE_URL}/orders/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ name, address: document.getElementById('address').value })
        });
      } catch (err) {
        console.warn('Order API skipped/mocked');
      }

      setTimeout(() => {
        stepShipping.style.display = 'none';
        stepPayment.style.display = 'block';
      }, 800);
    });
  }

  if (paymentForm) {
    paymentForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('pay-btn');
      btn.textContent = 'Processing Payment...';
      btn.disabled = true;

      // Simulate Payment Gateway API call (POST /payments/)
      try {
        await fetch(`${API_BASE_URL}/payments/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ amount: 100, method: 'CREDIT_CARD' }) // Mock amount
        });
      } catch (err) {
        console.warn('Payment API skipped/mocked');
      }

      setTimeout(() => {
        stepPayment.style.display = 'none';
        stepSuccess.style.display = 'block';
        document.getElementById('success-order-id').textContent = '#ORD-' + Math.floor(Math.random() * 1000000);
      }, 1500);
    });
  }
}

// Chatbot Logic
function setupChatbot() {
  if (!chatbotToggle || !chatbotWindow || !chatForm) return;

  chatbotToggle.addEventListener('click', () => {
    chatbotWindow.classList.toggle('active');
    if (chatbotWindow.classList.contains('active')) chatInput.focus();
  });

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    appendMessage('user', message);
    chatInput.value = '';

    const loadingId = 'msg-' + Date.now();
    appendMessage('bot', '<div class="loading-spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>', loadingId);

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const response = await fetch(`${API_BASE_URL}/ai/chat/`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ message: message })
      });

      const data = await response.json();
      document.getElementById(loadingId)?.remove();
      appendMessage('bot', data.response || data.reply || 'Không nhận được phản hồi.');
    } catch (error) {
      console.error('Chat error:', error);
      document.getElementById(loadingId)?.remove();
      appendMessage('bot', 'Xin lỗi, dịch vụ AI hiện không khả dụng. Vui lòng thử lại sau.');
    }
  });
}

function appendMessage(sender, text, id = null) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;
  if (id) msgDiv.id = id;
  msgDiv.innerHTML = text;
  if(chatMessages) {
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}
