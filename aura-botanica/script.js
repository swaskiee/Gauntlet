(function () {
  const modalOverlay = document.getElementById('modalOverlay');
  const modalClose = document.getElementById('modalClose');
  const menuBtn = document.getElementById('menuBtn');
  const sideMenu = document.getElementById('sideMenu');
  const sideMenuClose = document.getElementById('sideMenuClose');
  const navbar = document.getElementById('navbar');

  if (modalClose && modalOverlay) {
    modalClose.addEventListener('click', function () {
      modalOverlay.classList.add('hidden');
    });
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) {
        modalOverlay.classList.add('hidden');
      }
    });
  }

  if (menuBtn && sideMenu) {
    menuBtn.addEventListener('click', function () {
      sideMenu.classList.add('open');
      document.body.style.overflow = 'hidden';
    });
  }

  if (sideMenuClose && sideMenu) {
    sideMenuClose.addEventListener('click', function () {
      sideMenu.classList.remove('open');
      document.body.style.overflow = '';
    });
  }

  document.querySelectorAll('[data-close]').forEach(function (el) {
    el.addEventListener('click', function () {
      sideMenu.classList.remove('open');
      document.body.style.overflow = '';
    });
  });

  window.addEventListener('scroll', function () {
    if (window.scrollY > 60) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });

  const productCards = document.querySelectorAll('.product-card');

  const cardObserver = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const card = entry.target;
          const index = parseInt(card.getAttribute('data-index')) || 1;
          setTimeout(function () {
            card.classList.add('visible');
          }, (index - 1) * 120);
          cardObserver.unobserve(card);
        }
      });
    },
    { threshold: 0.1 }
  );

  productCards.forEach(function (card) {
    cardObserver.observe(card);
  });

  const revealEls = document.querySelectorAll(
    '.intro-heading, .intro-body, .story-title, .story-body, .origins-title, .origins-sub, .ritual-title, .ritual-body, .formats-title, .testimonials-title, .newsletter-title, .newsletter-sub, .origin-item, .format-card, .testimonial-card, .stat'
  );

  const revealObserver = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );

  revealEls.forEach(function (el) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(28px)';
    el.style.transition = 'opacity 0.7s ease, transform 0.7s ease';
    revealObserver.observe(el);
  });

  const newsletterBtn = document.querySelector('.newsletter-btn');
  const newsletterInput = document.querySelector('.newsletter-input');

  if (newsletterBtn && newsletterInput) {
    newsletterBtn.addEventListener('click', function () {
      const val = newsletterInput.value.trim();
      if (val && val.includes('@')) {
        newsletterBtn.textContent = 'Thank You';
        newsletterBtn.style.background = '#6b3f1f';
        newsletterBtn.style.color = '#f5f0e8';
        newsletterInput.value = '';
        setTimeout(function () {
          newsletterBtn.textContent = 'Join Now';
          newsletterBtn.style.background = '';
          newsletterBtn.style.color = '';
        }, 4000);
      } else {
        newsletterInput.style.borderColor = '#c8a96e';
        setTimeout(function () {
          newsletterInput.style.borderColor = '';
        }, 2000);
      }
    });
  }

  const modalBtn = document.querySelector('.modal-btn');
  const modalInput = document.querySelector('.modal-input');

  if (modalBtn && modalInput) {
    modalBtn.addEventListener('click', function () {
      const val = modalInput.value.trim();
      if (val && val.includes('@')) {
        modalBtn.textContent = 'Thank You';
        modalInput.value = '';
        setTimeout(function () {
          modalOverlay.classList.add('hidden');
        }, 1200);
      } else {
        modalInput.style.borderColor = '#c8a96e';
        setTimeout(function () {
          modalInput.style.borderColor = '';
        }, 2000);
      }
    });
  }

  // Interactive Cart Drawer & Order System
  window.cartItems = [];
  window.openCart = function () {
    let cartDrawer = document.getElementById('cartDrawer');
    if (!cartDrawer) {
      cartDrawer = document.createElement('div');
      cartDrawer.id = 'cartDrawer';
      cartDrawer.style.cssText = 'position:fixed;top:0;right:0;width:380px;max-width:90vw;height:100vh;background:#130e0b;color:#f5f0e8;z-index:99999;box-shadow:-5px 0 25px rgba(0,0,0,0.6);padding:2rem;display:flex;flex-direction:column;justify-content:space-between;border-left:1px solid rgba(200,169,110,0.3);';
      document.body.appendChild(cartDrawer);
    }
    renderCart();
    cartDrawer.style.display = 'flex';
  };

  window.closeCart = function () {
    const cartDrawer = document.getElementById('cartDrawer');
    if (cartDrawer) cartDrawer.style.display = 'none';
  };

  window.addToCart = function (productName, price) {
    window.cartItems.push({ name: productName, price: price });
    document.getElementById('cart-count').textContent = window.cartItems.length;
    
    // Toast notification
    const toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;bottom:32px;right:32px;background:#c8a96e;color:#1a1410;padding:12px 24px;font-family:Montserrat,sans-serif;font-size:11px;font-weight:700;letter-spacing:1.5px;z-index:99999;border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
    toast.textContent = `ADDED: ${productName.toUpperCase()}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
  };

  function renderCart() {
    const cartDrawer = document.getElementById('cartDrawer');
    if (!cartDrawer) return;
    const total = window.cartItems.reduce((acc, item) => acc + item.price, 0);
    
    let itemsHtml = window.cartItems.map((item, idx) => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:0.75rem 0;border-bottom:1px solid rgba(255,255,255,0.08);font-family:Montserrat,sans-serif;font-size:12px;">
        <span>${item.name}</span>
        <span style="color:#c8a96e;font-weight:600;">$${item.price.toFixed(2)}</span>
      </div>
    `).join('');

    if (!window.cartItems.length) {
      itemsHtml = '<p style="color:#94a3b8;font-family:Montserrat,sans-serif;font-size:12px;text-align:center;padding:3rem 0;">Your tasting bag is currently empty.</p>';
    }

    cartDrawer.innerHTML = `
      <div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid rgba(200,169,110,0.3);">
          <h3 style="font-family:'Playfair Display',serif;font-size:18px;letter-spacing:1px;color:#c8a96e;">Tasting Bag</h3>
          <button onclick="closeCart()" style="background:none;border:none;color:#f5f0e8;font-size:18px;cursor:pointer;">&#10005;</button>
        </div>
        <div style="max-height:60vh;overflow-y:auto;">
          ${itemsHtml}
        </div>
      </div>
      <div>
        <div style="display:flex;justify-content:space-between;padding:1rem 0;border-top:1px solid rgba(200,169,110,0.3);font-family:Montserrat,sans-serif;font-size:14px;font-weight:700;">
          <span>Subtotal</span>
          <span style="color:#c8a96e;">$${total.toFixed(2)}</span>
        </div>
        <button onclick="checkoutOrder()" style="width:100%;background:#c8a96e;color:#1a1410;border:none;padding:14px;font-family:Montserrat,sans-serif;font-size:12px;font-weight:700;letter-spacing:2px;cursor:pointer;text-transform:uppercase;transition:all 0.2s;">
          Proceed to Checkout
        </button>
      </div>
    `;
  }

  window.checkoutOrder = function () {
    if (!window.cartItems.length) {
      alert('Your tasting bag is empty!');
      return;
    }
    alert('✨ Thank you for choosing Aura Botanica! Your private tasting order has been placed.');
    window.cartItems = [];
    document.getElementById('cart-count').textContent = '0';
    closeCart();
  };

  // Wire product buttons to Add To Cart
  document.querySelectorAll('.product-card').forEach((card, i) => {
    const prices = [28.00, 24.00, 32.00, 26.00];
    const btn = card.querySelector('.product-btn');
    const nameEl = card.querySelector('.product-name');
    if (btn && nameEl) {
      btn.textContent = `Reserve ($${prices[i % prices.length]})`;
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        addToCart(nameEl.textContent, prices[i % prices.length]);
      });
    }
  });

})();
