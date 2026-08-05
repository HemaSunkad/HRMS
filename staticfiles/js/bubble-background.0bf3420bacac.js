/**
 * Bubble Background Animation
 * Creates animated bubble elements for the background
 */

const BUBBLES = [
  { size: 80, left: '10%', delay: 0, duration: 8 },
  { size: 60, left: '20%', delay: 2, duration: 10 },
  { size: 100, left: '35%', delay: 1, duration: 7 },
  { size: 40, left: '50%', delay: 3, duration: 9 },
  { size: 70, left: '65%', delay: 0.5, duration: 11 },
  { size: 90, left: '75%', delay: 2.5, duration: 8 },
  { size: 50, left: '85%', delay: 1.5, duration: 10 },
  { size: 65, left: '5%', delay: 4, duration: 9 },
  { size: 45, left: '45%', delay: 3.5, duration: 7 },
  { size: 75, left: '90%', delay: 0.8, duration: 12 },
  { size: 55, left: '30%', delay: 5, duration: 8 },
  { size: 85, left: '60%', delay: 1.2, duration: 10 },
  { size: 35, left: '15%', delay: 6, duration: 9 },
  { size: 95, left: '55%', delay: 2.2, duration: 11 },
  { size: 48, left: '78%', delay: 3.8, duration: 8 },
];

/**
 * Initialize bubble background
 */
function initBubbles() {
  const container = document.getElementById('bubbleContainer');
  if (!container) return;

  // Clear existing bubbles
  container.innerHTML = '';

  // Create bubble elements
  BUBBLES.forEach((bubble) => {
    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'bubble';
    bubbleEl.style.cssText = `
      width: ${bubble.size}px;
      height: ${bubble.size}px;
      left: ${bubble.left};
      animation-delay: ${bubble.delay}s;
      animation-duration: ${bubble.duration}s;
    `;
    container.appendChild(bubbleEl);
  });
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBubbles);
} else {
  initBubbles();
}

// Export for use in base templates
if (typeof window !== 'undefined') {
  window.initBubbles = initBubbles;
}
