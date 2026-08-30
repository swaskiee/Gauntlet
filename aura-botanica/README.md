# ☕ Nitanshu’s Kafé

## 🚀 Project Overview
Nitanshu’s Kafé is a premium-grade coffee landing page engineered using pure HTML, CSS, and JavaScript. This project focuses on high-end UI/UX design, smooth animation systems, and performance-oriented frontend architecture.

---

## 🧠 Engineering Goals
- Build a visually immersive experience without frameworks
- Implement scalable and modular frontend architecture
- Use performant animation strategies (GPU-friendly transforms)
- Maintain semantic HTML and accessibility awareness

---

## 🏗️ System Architecture

### Frontend Stack
- HTML5 → Semantic structure
- CSS3 → Layout, animations, theming
- JavaScript → DOM manipulation, interaction logic

### Design Patterns
- Component-based sectioning
- Utility-first styling approach
- Observer-driven animation system

---

## ⚙️ Core Features

### 1. Animation System
- IntersectionObserver-based reveal animations
- Staggered transitions for product cards
- Smooth cubic-bezier timing functions

### 2. Navigation System
- Dynamic navbar (scroll-based state change)
- Side menu with controlled body scroll lock
- Overlay-based UI interactions

### 3. UI Components
- Product cards with hover states
- Modal popup system
- Newsletter interaction UI
- Toast notification feedback

---

## 🧩 Code Highlights

### Intersection Observer
```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
});
```

### CSS Animation
```css
transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
```

---

## 📱 Responsiveness
- Fully responsive layout using Flexbox & Grid
- Fluid typography scaling
- Mobile-first spacing adjustments

---

## ⚡ Performance Optimization
- Minimal DOM reflows
- GPU-accelerated transforms
- Lazy animation triggering
- Optimized asset loading

---

## 📂 Project Structure
```
NITANSHU-KAFE/
├── index.html
├── style.css
├── script.js
```

---

## 🌐 Deployment
GitHub Pages:
https://nitanshu715.github.io/NITANSHU-KAFE/

---

## 🔮 Future Enhancements
- Backend integration (newsletter)
- Dark mode toggle
- API-driven product system
- Performance audits (Lighthouse optimization)

---

## 👤 Author
Nitanshu  
B.Tech Computer Science Engineering  
Cloud Computing & Virtualization

