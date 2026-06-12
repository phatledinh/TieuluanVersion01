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
  updateCartBadge();
  if (document.getElementById('product-grid')) {
    fetchProducts();
    fetchHomeRecommendations();
  }
  if (document.getElementById('product-detail-view')) {
    initProductDetail();
  }
  setupChatView();
  setupSearch();
  setupCategoryPills();
});

// Update Auth UI
function updateAuthUI() {
  const authLink = document.getElementById('auth-link');
  const navUsername = document.getElementById('nav-username');
  if (token) {
    if(authLink) {
      authLink.textContent = 'Đăng xuất';
      authLink.href = '#';
      authLink.addEventListener('click', (e) => {
        e.preventDefault();
        localStorage.removeItem('jwt_token');
        token = null;
        updateAuthUI();
        window.location.href = '/';
      });
    }
    if (navUsername) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        navUsername.textContent = payload.username || `user_${payload.user_id || payload.id || 1}`;
        navUsername.style.display = 'inline-block';
      } catch (e) {
        navUsername.textContent = 'Người dùng';
        navUsername.style.display = 'inline-block';
      }
    }
  } else {
    if(authLink) {
      authLink.textContent = 'Đăng nhập';
      authLink.href = '/login.html';
    }
    if (navUsername) navUsername.style.display = 'none';
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
    cacheProducts(productsArray);
    renderProducts(productsArray);
    renderCategoryPills(productsArray);
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

// Render Products for the Main Grid
function renderProducts(products) {
  const grid = document.getElementById('product-grid');
  if (!grid) return;
  if (!products || products.length === 0) {
    grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center;">Không tìm thấy sản phẩm nào.</div>';
    return;
  }

  grid.innerHTML = products.map((product, index) => {
    const price = product.price ? parseInt(product.price).toLocaleString('vi-VN') + ' ₫' : '0 ₫';
    const catName = product.category_name || product.category || 'Danh mục';
    const imageUrl = product.image_url || `https://picsum.photos/seed/${product.id}/400/400`;
    
    return `
    <div class="product-card" style="cursor: pointer; animation: fadeIn 0.5s ease forwards; animation-delay: ${index * 0.04}s; opacity: 0; background: white; border-radius: 8px; border: 1px solid #eee; overflow: hidden; display: flex; flex-direction: column;" onclick="window.location.href='/product-detail.html?id=${product.id}'">
      <div class="product-image" style="height: 220px; width: 100%; overflow: hidden; border-bottom: none; background: #f8f9fa;">
        <img src="${imageUrl}" alt="${product.name}" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy" />
      </div>
      <div class="product-details" style="padding: 1rem; flex: 1; display: flex; flex-direction: column;">
        <div style="margin-bottom: 0.5rem;">
          <span style="background: rgba(99, 102, 241, 0.08); color: var(--primary-color); font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 12px;">${catName}</span>
        </div>
        <h3 class="product-title" style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.5rem; color: #1e293b;">${product.name || product.title || 'Sản phẩm'}</h3>
        <p class="product-price" style="font-size: 1.1rem; font-weight: 700; margin-top: auto; margin-bottom: 0.8rem; background: none; -webkit-text-fill-color: #1e293b; color: #1e293b;">$${(product.price / 25000).toFixed(2)}</p>
      </div>
    </div>
  `;
  }).join('');
}

// Category Filtering logic
function renderCategoryPills(products) {
  const container = document.getElementById('category-pills-container');
  if (!container) return;

  const categories = ['Tất cả'];
  products.forEach(p => {
    const cat = p.category_name || '';
    if (cat && !categories.includes(cat)) {
      categories.push(cat);
    }
  });

  container.innerHTML = categories.map((cat, i) => 
    `<button class="pill ${i === 0 ? 'active' : ''}">${cat}</button>`
  ).join('');

  setupCategoryPills();
}

function setupCategoryPills() {
  const pills = document.querySelectorAll('.pill');
  pills.forEach(pill => {
    pill.addEventListener('click', (e) => {
      pills.forEach(p => p.classList.remove('active'));
      e.target.classList.add('active');
      const cat = e.target.textContent;
      if (cat === 'Tất cả') {
        renderProducts(allProductsCache);
      } else {
        const filtered = allProductsCache.filter(p => (p.category_name || '').toLowerCase() === cat.toLowerCase());
        renderProducts(filtered.length > 0 ? filtered : allProductsCache.slice(0, 5)); // fallback if no match
      }
    });
  });
}

// Add to Cart — PDF 3.8.1: Khi add-to-cart → show recommendations
window.addToCart = async (productId, productName) => {
  if (!token) {
    alert('Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng.');
    window.location.href = '/login.html';
    return;
  }
  
  try {
    // Track behavior: add_to_cart (PDF 3.3)
    trackBehavior(productId, 'add_to_cart');

    // Calling cart-service via API Gateway
    const response = await fetch(`${API_BASE_URL}/carts/add/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ product_id: productId, quantity: 1 })
    });
    
    if (response.status === 401) {
       localStorage.removeItem('jwt_token');
       alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
       window.location.href = '/login.html';
       return;
    }
    
    if (response.ok) {
       // Redirect to cart page after adding to cart
       window.location.href = '/cart.html';
    } else {
       alert('Không thể thêm vào giỏ hàng. Vui lòng kiểm tra lại dịch vụ giỏ hàng.');
    }
  } catch (err) {
    console.error('Error adding to cart', err);
    alert('Lỗi kết nối. Không thể thêm vào giỏ hàng lúc này.');
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
    
    if (response.status === 401) {
       localStorage.removeItem('jwt_token');
       alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
       window.location.href = '/login.html';
       return;
    }
    
    if (!response.ok) throw new Error('Cart API failed');
    const data = await response.json();
    const cartItems = data.items || [];

    // Update cart badge
    const totalQty = cartItems.reduce((sum, item) => sum + item.quantity, 0);
    const cartCountEl = document.getElementById('cart-count');
    if (cartCountEl) cartCountEl.textContent = totalQty;

    if (cartItems.length === 0) {
      renderCartItems([], 0);
      return;
    }

    // Cart API only returns product_id + quantity → fetch product details
    let productMap = {};
    try {
      const prodResp = await fetch(`${API_BASE_URL}/products/`);
      if (prodResp.ok) {
        const prodData = await prodResp.json();
        const products = prodData.results || prodData;
        if (Array.isArray(products)) {
          products.forEach(p => { productMap[p.id] = p; });
        }
      }
    } catch (e) {
      console.warn('Could not fetch product details for cart', e);
    }

    // Enrich cart items with product name and price
    const enrichedItems = cartItems.map(item => {
      const product = productMap[item.product_id] || {};
      return {
        id: item.product_id,
        name: product.name || `Sản phẩm #${item.product_id}`,
        price: parseFloat(product.price) || 0,
        quantity: item.quantity,
      };
    });

    const total = enrichedItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    renderCartItems(enrichedItems, total);

    // Show AI recommendations on cart page (PDF 3.8.1: Khi add-to-cart)
    fetchCartPageRecommendations();
  } catch (err) {
    console.warn('Cart API error, showing empty cart', err);
    renderCartItems([], 0);
  }
}

export function renderCartItems(items, total) {
  const cartContent = document.getElementById('cart-content');
  const cartSubtotal = document.getElementById('cart-subtotal');
  const cartTax = document.getElementById('cart-tax');
  const cartTotal = document.getElementById('cart-total');
  
  if (!cartContent) return;

  if (items.length === 0) {
    cartContent.innerHTML = '<p style="text-align:center; padding: 2rem 0; color: var(--text-muted);">Giỏ hàng trống. <a href="/" style="color: var(--primary-color); text-decoration: none; font-weight: 600;">Mua sắm ngay →</a></p>';
    if(cartSubtotal) cartSubtotal.textContent = '0 ₫';
    if(cartTax) cartTax.textContent = '0 ₫';
    if(cartTotal) cartTotal.textContent = '0 ₫';
    return;
  }

  cartContent.innerHTML = items.map(item => {
    const price = item.price ? parseInt(item.price).toLocaleString('vi-VN') + ' ₫' : '0 ₫';
    const subtotal = (item.price * item.quantity);
    const subtotalStr = subtotal ? parseInt(subtotal).toLocaleString('vi-VN') + ' ₫' : '0 ₫';
    return `
    <div class="cart-item" data-product-id="${item.id}">
      <div class="cart-item-img">📦</div>
      <div class="cart-item-details">
        <div class="cart-item-title">${item.name}</div>
        <div class="cart-item-price">${price} × ${item.quantity} = <strong>${subtotalStr}</strong></div>
      </div>
      <div class="cart-item-actions">
        <div class="quantity-control">
          <button class="qty-btn" onclick="window.updateCartQty(${item.id}, ${item.quantity - 1})">−</button>
          <span>${item.quantity}</span>
          <button class="qty-btn" onclick="window.updateCartQty(${item.id}, ${item.quantity + 1})">+</button>
        </div>
        <button class="remove-btn" onclick="window.removeCartItem(${item.id})">Xóa</button>
      </div>
    </div>
  `;
  }).join('');

  const formatVND = (value) => parseInt(value || 0).toLocaleString('vi-VN') + ' ₫';
  const tax = total * 0.1;
  const grandTotal = total + tax;
  
  if(cartSubtotal) cartSubtotal.textContent = formatVND(total);
  if(cartTax) cartTax.textContent = formatVND(tax);
  if(cartTotal) cartTotal.textContent = formatVND(grandTotal);
}

// Update cart item quantity — PUT /carts/update/
window.updateCartQty = async (productId, newQty) => {
  if (newQty < 1) {
    // If quantity is 0, remove the item
    window.removeCartItem(productId);
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/carts/update/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ product_id: productId, quantity: newQty })
    });

    if (!response.ok) throw new Error('Update failed');
  } catch (err) {
    console.error('Error updating cart quantity:', err);
  }

  // Refresh cart
  fetchCart();
};

// Remove cart item — DELETE /carts/remove/
window.removeCartItem = async (productId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/carts/remove/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ product_id: productId })
    });

    if (!response.ok) throw new Error('Remove failed');
    showToast('Đã xóa sản phẩm khỏi giỏ hàng');
  } catch (err) {
    console.error('Error removing cart item:', err);
  }

  // Refresh cart
  fetchCart();
};

// Fetch AI recommendations for cart page (PDF 3.8.1)
async function fetchCartPageRecommendations() {
  const section = document.getElementById('cart-recommendations');
  const grid = document.getElementById('cart-rec-grid');
  if (!section || !grid) return;

  const userId = getUserIdFromToken() || 1;

  grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem;"><div class="loading-spinner" style="margin: 0 auto;"></div><p style="margin-top: 0.5rem; color: var(--text-muted); font-size: 0.85rem;">AI đang tìm sản phẩm phù hợp...</p></div>';
  section.style.display = 'block';

  try {
    const response = await fetch(`${API_BASE_URL}/ai/recommend?user_id=${userId}&k=4`);
    if (!response.ok) throw new Error('Recommend API failed');
    const productIds = await response.json();

    if (productIds && productIds.length > 0) {
      const products = await fetchProductsByIds(productIds);
      renderRecommendationGrid(grid, products, 'cart');
    } else {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; color: var(--text-muted);">Thêm vào giỏ hàng nhiều hơn để AI gợi ý chính xác hơn!</div>';
    }
  } catch (err) {
    console.error('Cart recommendations error:', err);
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; color: var(--text-muted);">AI Service đang khởi động...</div>';
  }
}

// --- CHECKOUT LOGIC ---
export function handleCheckout() {
  const shippingForm = document.getElementById('shipping-form');
  const paymentForm = document.getElementById('payment-form');
  const stepShipping = document.getElementById('step-shipping');
  const stepPayment = document.getElementById('step-payment');
  const stepSuccess = document.getElementById('step-success');
  const displayName = document.getElementById('display-name');
  
  let currentOrderId = null;
  let currentOrderAmount = 0;
  let currentAddress = '';

  // Load Cart Summary for Checkout Page
  const loadCheckoutSummary = async () => {
    const summaryContainer = document.getElementById('checkout-order-items');
    if (!summaryContainer) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/carts/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Fetch cart failed');
      const data = await response.json();
      
      const items = data.items || [];
      if (items.length === 0) {
        summaryContainer.innerHTML = '<div style="color: var(--text-muted);">Giỏ hàng của bạn đang trống.</div>';
        return;
      }

      // We need product details, so we fetch them
      const productIds = items.map(item => item.product_id);
      const productsData = await fetchProductsByIds(productIds);
      const productMap = {};
      productsData.forEach(p => { productMap[p.id] = p; });

      let total = 0;
      summaryContainer.innerHTML = items.map(item => {
        const product = productMap[item.product_id];
        if (!product) return '';
        const itemTotal = product.price * item.quantity;
        total += itemTotal;
        return `
          <div style="display: flex; gap: 1rem; margin-bottom: 1rem; align-items: center;">
            <img src="${product.image_url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;">
            <div style="flex: 1;">
              <div style="font-weight: 500; font-size: 0.9rem;">${product.name}</div>
              <div style="color: var(--text-muted); font-size: 0.8rem;">SL: ${item.quantity}</div>
            </div>
            <div style="font-weight: bold; font-size: 0.9rem;">${parseInt(itemTotal).toLocaleString('vi-VN')} ₫</div>
          </div>
        `;
      }).join('');

      const formatVND = (value) => parseInt(value).toLocaleString('vi-VN') + ' ₫';
      const tax = total * 0.1;
      const grandTotal = total + tax;

      document.getElementById('checkout-subtotal').textContent = formatVND(total);
      document.getElementById('checkout-tax').textContent = formatVND(tax);
      document.getElementById('checkout-total').textContent = formatVND(grandTotal);
      
    } catch (err) {
      console.error('Error loading checkout summary:', err);
      summaryContainer.innerHTML = '<div style="color: var(--danger);">Không thể tải thông tin đơn hàng.</div>';
    }
  };

  loadCheckoutSummary();

  if (shippingForm) {
    shippingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('fullName').value;
      currentAddress = document.getElementById('address').value;
      if(displayName) displayName.textContent = name.toUpperCase() || 'NGUYEN VAN A';
      
      const btn = document.getElementById('continue-btn');
      btn.textContent = 'Đang xử lý...';
      btn.disabled = true;

      try {
        // 1. Create Order API call (POST /orders/)
        const orderResponse = await fetch(`${API_BASE_URL}/orders/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
        });

        if (!orderResponse.ok) {
          throw new Error('Failed to create order');
        }

        const orderData = await orderResponse.json();
        currentOrderId = orderData.id;
        currentOrderAmount = orderData.total_price || 0;

        // Proceed to Payment Step
        stepShipping.style.display = 'none';
        stepPayment.style.display = 'block';

      } catch (err) {
        console.error('Order API error:', err);
        alert('Có lỗi xảy ra khi tạo đơn hàng. Giỏ hàng của bạn có thể trống.');
        btn.textContent = 'Tiếp tục thanh toán';
        btn.disabled = false;
      }
    });
  }

  if (paymentForm) {
    paymentForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('pay-btn');
      btn.textContent = 'Đang xử lý thanh toán...';
      btn.disabled = true;

      try {
        // 2. Simulate Payment Gateway API call (POST /payments/)
        const paymentResponse = await fetch(`${API_BASE_URL}/payments/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ order_id: currentOrderId, amount: currentOrderAmount })
        });

        if (!paymentResponse.ok) {
          throw new Error('Payment failed');
        }

        // 3. Initiate Shipping (POST /shipping/create)
        const shippingResponse = await fetch(`${API_BASE_URL}/shipping/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ order_id: currentOrderId, address: currentAddress })
        });

        if (!shippingResponse.ok) {
          throw new Error('Shipping creation failed');
        }

        // Success Step
        stepPayment.style.display = 'none';
        stepSuccess.style.display = 'block';
        document.getElementById('success-order-id').textContent = '#ORD-' + currentOrderId;
        
        // Clear cart badge
        const cartCountEl = document.getElementById('cart-count');
        if (cartCountEl) cartCountEl.textContent = '0';

      } catch (err) {
        console.error('Checkout error:', err);
        const errorEl = document.getElementById('payment-error');
        if (errorEl) {
          errorEl.textContent = 'Thanh toán hoặc tạo đơn vận chuyển thất bại. Vui lòng thử lại.';
          errorEl.style.display = 'block';
        }
        btn.textContent = 'Thanh toán & Đặt hàng';
        btn.disabled = false;
      }
    });
  }
}

// Chatbot View Logic (Full screen chat)
function setupChatView() {
  const navHome = document.getElementById('nav-home');
  const navChat = document.getElementById('nav-chat');
  const mainView = document.getElementById('main-view');
  const chatView = document.getElementById('chat-view');
  
  if (navHome && navChat && mainView && chatView) {
    navHome.addEventListener('click', (e) => {
      e.preventDefault();
      navHome.classList.add('active');
      navChat.classList.remove('active');
      mainView.style.display = 'block';
      chatView.style.display = 'none';
    });
    
    navChat.addEventListener('click', (e) => {
      e.preventDefault();
      navChat.classList.add('active');
      navHome.classList.remove('active');
      mainView.style.display = 'none';
      chatView.style.display = 'block';
      document.getElementById('chat-input')?.focus();
    });
  }

  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  
  if (!chatForm) return;

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
      
      // Parse if response contains recommended products format
      let replyText = data.response || data.reply || 'Không nhận được phản hồi.';
      let recommendedProducts = [];
      
      // Basic mock parsing - if bot mentions products or we have them in data
      if (data.recommended_product_ids && data.recommended_product_ids.length > 0) {
         recommendedProducts = await fetchProductsByIds(data.recommended_product_ids);
      } else if (message.toLowerCase().includes('gợi ý') && allProductsCache.length > 0) {
         // mock recommendations for the demo if AI doesn't return them properly
         recommendedProducts = allProductsCache.slice(10, 14);
      }

      appendMessage('bot', replyText, null, recommendedProducts);
    } catch (error) {
      console.error('Chat error:', error);
      document.getElementById(loadingId)?.remove();
      appendMessage('bot', 'Xin lỗi, dịch vụ AI hiện không khả dụng. Vui lòng thử lại sau.');
    }
  });
}

function appendMessage(sender, text, id = null, products = []) {
  const chatMessages = document.getElementById('chat-messages');
  if (!chatMessages) return;

  const msgWrapper = document.createElement('div');
  msgWrapper.className = `message-wrapper ${sender}`;
  if (id) msgWrapper.id = id;
  
  let contentHtml = '';
  if (sender === 'user') {
    contentHtml = `<div class="msg-text user-bubble">${text}</div>`;
  } else {
    let productsHtml = '';
    if (products && products.length > 0) {
       productsHtml = `
         <div class="chat-carousel" style="margin-top: 1rem; display: flex; gap: 10px; overflow-x: auto; padding-bottom: 5px;">
           ${products.map(product => {
             const imageUrl = product.image_url || `https://picsum.photos/seed/${product.id}/400/400`;
             return `
               <div class="chat-product-card" style="min-width: 160px; max-width: 160px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; flex-shrink: 0;">
                 <img src="${imageUrl}" alt="${product.name}" style="width: 100%; height: 120px; object-fit: cover;" />
                 <div style="padding: 0.5rem;">
                   <h4 style="font-size: 0.8rem; margin: 0 0 0.2rem 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #1e293b;">${product.name}</h4>
                   <p style="font-size: 0.8rem; color: #64748b; margin: 0 0 0.2rem 0;">${product.category_name || ''}</p>
                   <p style="font-size: 0.85rem; font-weight: bold; color: var(--primary-color); margin: 0;">$${(product.price / 25000).toFixed(2)}</p>
                 </div>
               </div>
             `;
           }).join('')}
         </div>
       `;
    }
  
    contentHtml = `
      <div class="msg-avatar"><svg viewBox="0 0 24 24" fill="var(--primary-color)" width="20" height="20" style="margin-top:2px;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></div>
      <div class="msg-content bot-bubble">
         <div class="msg-text">${text}</div>
         ${productsHtml}
      </div>
    `;
  }
  
  msgWrapper.innerHTML = contentHtml;
  chatMessages.appendChild(msgWrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ─────────────────────────────────────────────
// SEARCH + RECOMMENDATIONS — PDF 3.8.1
// ─────────────────────────────────────────────

// All products cache for lookup
let allProductsCache = [];

// Store all products for recommendation lookup
function cacheProducts(products) {
  allProductsCache = products;
}

// Get user ID from JWT token
function getUserIdFromToken() {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.user_id || payload.id || 1;
  } catch {
    return 1;
  }
}

// Setup search — PDF 3.8.1: Khi search
function setupSearch() {
  const searchForm = document.getElementById('search-form');
  const searchInput = document.getElementById('search-input');
  if (!searchForm || !searchInput) return;

  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = searchInput.value.trim();
    if (!query) return;

    // Track search behavior (PDF 3.3)
    const userId = getUserIdFromToken();
    if (userId) trackBehavior(0, 'search');

    // Filter products locally by search query
    if (allProductsCache.length > 0) {
      const filtered = allProductsCache.filter(p => {
        const text = `${p.name || ''} ${p.category_name || ''} ${p.description || ''}`.toLowerCase();
        return text.includes(query.toLowerCase());
      });
      renderProducts(filtered.length > 0 ? filtered : allProductsCache);
    }

    // Fetch AI recommendations for search query (PDF 3.8.1)
    await fetchSearchRecommendations(query);
  });
}

// PDF 3.8.1: GET /recommend?user_id=X&query=từ_khóa (Khi search)
async function fetchSearchRecommendations(query) {
  const section = document.getElementById('search-recommendations');
  const grid = document.getElementById('search-rec-grid');
  if (!section || !grid) return;

  const userId = getUserIdFromToken() || 1;

  grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem;"><div class="loading-spinner" style="margin: 0 auto;"></div><p style="margin-top: 0.5rem; color: var(--text-muted); font-size: 0.85rem;">AI đang phân tích...</p></div>';
  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  try {
    const response = await fetch(`${API_BASE_URL}/ai/recommend?user_id=${userId}&query=${encodeURIComponent(query)}&k=6`);
    if (!response.ok) throw new Error('Recommend API failed');
    const productIds = await response.json();

    if (productIds && productIds.length > 0) {
      const products = await fetchProductsByIds(productIds);
      renderRecommendationGrid(grid, products, 'search');
    } else {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; color: var(--text-muted);">Chưa có dữ liệu gợi ý. Hãy tương tác thêm để AI học hành vi của bạn!</div>';
    }
  } catch (err) {
    console.error('Search recommendations error:', err);
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; color: var(--text-muted);">AI Service đang khởi động... Vui lòng thử lại sau.</div>';
  }
}

// PDF 3.8.1: GET /recommend?user_id=X (Khi add-to-cart)
async function fetchCartRecommendations() {
  const section = document.getElementById('cart-recommendations');
  const grid = document.getElementById('cart-rec-grid');
  if (!section || !grid) return;

  const userId = getUserIdFromToken() || 1;

  grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem;"><div class="loading-spinner" style="margin: 0 auto;"></div><p style="margin-top: 0.5rem; color: var(--text-muted); font-size: 0.85rem;">AI đang tìm sản phẩm phù hợp...</p></div>';
  section.style.display = 'block';
  section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  try {
    const response = await fetch(`${API_BASE_URL}/ai/recommend?user_id=${userId}&k=4`);
    if (!response.ok) throw new Error('Recommend API failed');
    const productIds = await response.json();

    if (productIds && productIds.length > 0) {
      const products = await fetchProductsByIds(productIds);
      renderRecommendationGrid(grid, products, 'cart');
    } else {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; color: var(--text-muted);">Thêm vào giỏ hàng nhiều hơn để AI gợi ý chính xác hơn!</div>';
    }
  } catch (err) {
    console.error('Cart recommendations error:', err);
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; color: var(--text-muted);">AI Service đang khởi động...</div>';
  }
}

// Default recommendations for Homepage
async function fetchHomeRecommendations() {
  const section = document.getElementById('search-recommendations');
  const grid = document.getElementById('search-rec-grid');
  if (!section || !grid) return;

  const userId = getUserIdFromToken() || 1;

  grid.innerHTML = '<div style="padding: 1.5rem;"><div class="loading-spinner" style="margin: 0 auto;"></div></div>';
  section.style.display = 'block';

  try {
    // Tạm thời gọi API lấy gợi ý chung, k=6 (hiển thị đủ một hàng ngang)
    const response = await fetch(`${API_BASE_URL}/ai/recommend?user_id=${userId}&k=6`);
    if (!response.ok) throw new Error('Recommend API failed');
    const productIds = await response.json();

    if (productIds && productIds.length > 0) {
      const products = await fetchProductsByIds(productIds);
      renderRecommendationGrid(grid, products, 'home');
    } else {
      // Fallback cho lần đầu nếu AI chưa có dữ liệu track: render mock data
      setTimeout(() => {
         if(allProductsCache.length > 0) {
            renderRecommendationGrid(grid, allProductsCache.slice(5, 11), 'home');
         } else {
            grid.innerHTML = '<div style="padding: 1.5rem; color: var(--text-muted);">Hãy duyệt thêm sản phẩm để AI gợi ý cho bạn.</div>';
         }
      }, 500);
    }
  } catch (err) {
    console.error('Home recommendations error:', err);
    // Nếu service lỗi hoặc chưa khởi động, dùng cache để show carousel cho đẹp
    setTimeout(() => {
       if(allProductsCache.length > 0) {
          renderRecommendationGrid(grid, allProductsCache.slice(0, 6), 'home');
       } else {
          grid.innerHTML = '<div style="padding: 1.5rem; color: var(--text-muted);">AI Service đang khởi động...</div>';
       }
    }, 500);
  }
}

// Fetch product details by IDs from product-service
async function fetchProductsByIds(ids) {
  // Try from cache first
  if (allProductsCache.length > 0) {
    const cached = ids.map(id => allProductsCache.find(p => p.id === id)).filter(Boolean);
    if (cached.length > 0) return cached;
  }

  // Fallback: fetch all products and filter
  try {
    const response = await fetch(`${API_BASE_URL}/products/`);
    if (!response.ok) throw new Error('Product API failed');
    const data = await response.json();
    const products = data.results || data;
    return ids.map(id => products.find(p => p.id === id)).filter(Boolean);
  } catch {
    return [];
  }
}

// Render recommendation product cards as Carousel
function renderRecommendationGrid(grid, products, type) {
  if (!products || products.length === 0) {
    grid.innerHTML = '<div style="padding: 1.5rem; color: var(--text-muted);">Không tìm thấy sản phẩm gợi ý.</div>';
    return;
  }

  grid.style.display = 'flex';
  grid.style.gap = '15px';
  grid.style.overflowX = 'auto';
  grid.style.paddingBottom = '10px';
  grid.style.scrollSnapType = 'x mandatory';

  grid.innerHTML = products.map((product, index) => {
    const price = product.price ? parseInt(product.price).toLocaleString('vi-VN') + ' ₫' : '0 ₫';
    const catName = product.category_name || product.category || '';
    const imageUrl = product.image_url || `https://picsum.photos/seed/${product.id}/400/400`;
    
    return `
    <div class="product-card rec-card" style="cursor: pointer; min-width: 200px; max-width: 200px; flex-shrink: 0; scroll-snap-align: start; background: white; border-radius: 8px; border: 1px solid #eee; overflow: hidden; display: flex; flex-direction: column;" onclick="window.location.href='/product-detail.html?id=${product.id}'">
      <div class="product-image" style="height: 160px; width: 100%; border-bottom: none;">
        <img src="${imageUrl}" alt="${product.name}" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy" />
      </div>
      <div class="product-details" style="padding: 0.8rem; flex: 1; display: flex; flex-direction: column;">
        <h3 class="product-title" style="font-size: 0.85rem; font-weight: 600; margin-bottom: 0.3rem; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${product.name || 'Sản phẩm'}</h3>
        <p class="product-price" style="font-size: 0.95rem; font-weight: 700; color: var(--primary-color); margin: 0; background: none; -webkit-text-fill-color: var(--primary-color);">$${(product.price / 25000).toFixed(2)}</p>
      </div>
    </div>
  `;
  }).join('');
}

// Track user behavior — PDF 3.3 (POST /track-behavior)
async function trackBehavior(productId, action) {
  try {
    await fetch(`${API_BASE_URL}/ai/track-behavior`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: getUserIdFromToken() || 1,
        product_id: productId,
        action: action,
        timestamp: new Date().toISOString()
      })
    });
  } catch (err) {
    console.warn('Behavior tracking failed:', err);
  }
}

// Toast notification (replaces alert)
function showToast(message) {
  // Remove existing toast
  document.getElementById('toast-notification')?.remove();

  const toast = document.createElement('div');
  toast.id = 'toast-notification';
  toast.className = 'toast-notification';
  toast.textContent = message;
  document.body.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => toast.classList.add('show'));

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// --- PRODUCT DETAIL LOGIC ---
async function initProductDetail() {
  const urlParams = new URLSearchParams(window.location.search);
  const productId = urlParams.get('id');
  const detailView = document.getElementById('product-detail-view');

  if (!productId) {
    detailView.innerHTML = '<div style="text-align: center; padding: 3rem;">Không tìm thấy sản phẩm.</div>';
    return;
  }

  // Track behavior view (PDF 3.3)
  trackBehavior(productId, 'view');

  try {
    const response = await fetch(`${API_BASE_URL}/products/${productId}/`);
    if (!response.ok) {
       // fallback, fetch all and find
       const allResp = await fetch(`${API_BASE_URL}/products/`);
       const allData = await allResp.json();
       const products = allData.results || allData;
       const product = products.find(p => p.id == productId);
       if (!product) throw new Error('Product not found');
       renderProductDetail(product);
    } else {
       const product = await response.json();
       renderProductDetail(product);
    }
  } catch (error) {
    console.error('Error fetching product details:', error);
    detailView.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--danger);">Lỗi khi tải thông tin sản phẩm.</div>';
  }
}

function renderProductDetail(product) {
  const detailView = document.getElementById('product-detail-view');
  const imageUrl = product.image_url || `https://picsum.photos/seed/${product.id}/600/600`;
  const catName = product.category_name || product.category || 'Danh mục';
  const priceUSD = (product.price / 25000).toFixed(2);
  const safeName = product.name ? product.name.replace(/'/g, "\\'") : 'Sản phẩm';

  detailView.innerHTML = `
    <div class="product-detail-container" style="display: flex; flex-wrap: wrap; gap: 2rem; background: white; padding: 2rem; border-radius: 12px; border: 1px solid #eee; margin-bottom: 3rem; animation: fadeIn 0.5s ease forwards;">
      <div class="product-detail-image" style="flex: 1; min-width: 300px; border-radius: 8px; overflow: hidden; background: #f8f9fa; display: flex; align-items: center; justify-content: center;">
        <img src="${imageUrl}" alt="${product.name}" style="max-width: 100%; max-height: 500px; object-fit: contain;" loading="lazy" />
      </div>
      <div class="product-detail-info" style="flex: 1; min-width: 300px; display: flex; flex-direction: column;">
        <div style="margin-bottom: 1rem;">
          <span style="background: rgba(99, 102, 241, 0.1); color: var(--primary-color); font-size: 0.85rem; font-weight: 600; padding: 4px 12px; border-radius: 16px;">${catName}</span>
        </div>
        <h1 style="font-size: 2rem; font-weight: 700; margin-bottom: 1rem; color: #0f172a;">${product.name || product.title || 'Sản phẩm'}</h1>
        <div style="font-size: 2rem; font-weight: 800; color: var(--primary-color); margin-bottom: 1.5rem;">$${priceUSD} <span style="font-size: 1rem; color: #64748b; font-weight: normal; text-decoration: line-through; margin-left: 10px;">$${(priceUSD * 1.2).toFixed(2)}</span></div>
        
        <p style="color: #475569; line-height: 1.6; margin-bottom: 2rem; font-size: 1.05rem;">
          ${product.description || 'Sản phẩm tuyệt vời với chất lượng đảm bảo. Thiết kế hiện đại, phù hợp với xu hướng mới nhất. Sự lựa chọn hoàn hảo cho nhu cầu của bạn.'}
        </p>

        <div style="display: flex; gap: 1rem; margin-top: auto;">
          <button class="btn btn-primary" style="flex: 1; padding: 1rem; font-size: 1.1rem; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 8px;" onclick="window.addToCart(${product.id}, '${safeName}')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
            Thêm vào giỏ hàng
          </button>
        </div>
      </div>
    </div>
    
    <section id="detail-recommendations" class="recommendations-section animate-fade-in" style="margin-bottom: 2.5rem;">
      <div class="section-header" style="display: flex; align-items: center; gap: 8px; margin-bottom: 1rem;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary-color)" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
        <h3 style="margin: 0; font-size: 1.2rem;">Sản phẩm tương tự</h3>
      </div>
      <div class="carousel-container">
        <div id="detail-rec-grid" class="carousel-track"></div>
      </div>
    </section>
  `;

  fetchDetailRecommendations(product.id);
}

async function updateCartBadge() {
  const cartCountEl = document.getElementById('cart-count');
  if (!cartCountEl || !token) return;

  try {
    const response = await fetch(`${API_BASE_URL}/carts/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.ok) {
      const data = await response.json();
      const cartItems = data.items || [];
      const totalQty = cartItems.reduce((sum, item) => sum + item.quantity, 0);
      cartCountEl.textContent = totalQty;
    } else if (response.status === 401) {
      localStorage.removeItem('jwt_token');
      token = null;
      updateAuthUI();
      cartCountEl.textContent = '0';
    }
  } catch (err) {
    console.warn('Could not update cart badge:', err);
  }
}

async function fetchDetailRecommendations(productId) {
  const grid = document.getElementById('detail-rec-grid');
  if (!grid) return;

  const userId = getUserIdFromToken() || 1;
  grid.innerHTML = '<div style="padding: 1.5rem;"><div class="loading-spinner" style="margin: 0 auto;"></div></div>';

  try {
    const response = await fetch(`${API_BASE_URL}/ai/recommend?user_id=${userId}&k=6`);
    if (!response.ok) throw new Error('Recommend API failed');
    const productIds = await response.json();

    if (productIds && productIds.length > 0) {
      const products = await fetchProductsByIds(productIds);
      const filtered = products.filter(p => p.id != productId);
      renderRecommendationGrid(grid, filtered, 'detail');
    } else {
       throw new Error('No recommendations');
    }
  } catch (err) {
    console.error('Detail recommendations error:', err);
    try {
        const allResp = await fetch(`${API_BASE_URL}/products/`);
        const allData = await allResp.json();
        const allProds = allData.results || allData;
        const filtered = allProds.filter(p => p.id != productId).slice(0, 6);
        renderRecommendationGrid(grid, filtered, 'detail');
    } catch {
        grid.innerHTML = '<div style="padding: 1.5rem; color: var(--text-muted);">Không thể tải sản phẩm gợi ý.</div>';
    }
  }
}
