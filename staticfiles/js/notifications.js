/**
 * Notifications Module
 * Handles toast notifications and push notifications
 */

(function() {
  'use strict';

  /**
   * Show a toast notification
   * @param {string} message - The message to display
   * @param {string} type - The type of notification (success, error, warning, info)
   * @param {number} duration - How long to show the notification (ms)
   */
  function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    // Icon based on type
    let icon = '';
    switch (type) {
      case 'success':
        icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
        break;
      case 'error':
        icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
        break;
      case 'warning':
        icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
        break;
      default:
        icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
    }

    toast.innerHTML = `
      <div class="toast-icon">${icon}</div>
      <span class="toast-message">${message}</span>
      <button class="toast-close" onclick="this.parentElement.remove()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    `;

    container.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  }

  /**
   * Request notification permission
   */
  async function requestNotificationPermission() {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return false;
  }

  /**
   * Show a browser notification
   * @param {string} title - Notification title
   * @param {string} body - Notification body
   * @param {string} icon - URL to notification icon
   */
  function showNotification(title, body, icon = '/static/assets/apple-icon.jpeg') {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body, icon });
    }
  }

  /**
   * Subscribe to push notifications
   * @param {PushSubscription} subscription - The push subscription object
   */
  async function subscribeToPush(subscription) {
    try {
      const response = await fetch('/api/push-subscriptions/', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(subscription)
      });
      return response.ok;
    } catch (error) {
      console.error('Push subscription failed:', error);
      return false;
    }
  }

  // Expose functions globally
  window.WT_NOTIFICATIONS = {
    showToast,
    showNotification,
    requestNotificationPermission,
    subscribeToPush
  };

  // Also expose convenience function
  window.showToast = showToast;
})();
