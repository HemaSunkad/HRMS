/**
 * Site-wide chat notification widget.
 * Include this (after api.js and auth.js) on every authenticated page
 * EXCEPT the chat pages themselves — it polls in the background and pops
 * a WhatsApp-style toast + updates the sidebar chat badge no matter what
 * page the user is currently looking at.
 */
(function () {
  if (window.location.pathname.includes('/chat/')) return; // chat page has its own live view

  const token = localStorage.getItem('token');
  if (!token) return;

  let lastCheck = new Date().toISOString();
  const notified = new Set();
  let queue = [];
  let visible = false;

  function isAdminUser() {
    return localStorage.getItem('is_admin') === 'true';
  }

  function chatUrl() {
    return isAdminUser() ? '/admin/chat/' : '/employee/chat/';
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  function injectStyles() {
    if (document.getElementById('wtChatToastStyles')) return;
    const style = document.createElement('style');
    style.id = 'wtChatToastStyles';
    style.textContent = `
      .wt-chat-toast{position:fixed;top:20px;right:20px;z-index:99999;max-width:340px;background:#fff;
        border-radius:12px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,.18);
        animation:wtSlideIn .25s ease-out;font-family:inherit;}
      @keyframes wtSlideIn{from{opacity:0;transform:translateX(80px)}to{opacity:1;transform:translateX(0)}}
      @keyframes wtSlideOut{from{opacity:1;transform:translateX(0)}to{opacity:0;transform:translateX(80px)}}
      .wt-chat-toast-head{background:linear-gradient(135deg,#8b5cf6,#d946ef);color:#fff;padding:10px 14px;
        display:flex;align-items:center;justify-content:space-between;font-size:13px;font-weight:600;}
      .wt-chat-toast-head button{background:rgba(255,255,255,.2);border:none;color:#fff;width:22px;height:22px;
        border-radius:50%;cursor:pointer;}
      .wt-chat-toast-body{padding:12px 14px;display:flex;gap:10px;}
      .wt-chat-toast-avatar{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#8b5cf6,#d946ef);
        color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0;}
      .wt-chat-toast-sender{font-weight:600;font-size:13px;color:#1f2937;}
      .wt-chat-toast-msg{font-size:12.5px;color:#6b7280;margin-top:2px;
        display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
      .wt-chat-toast-actions{display:flex;gap:8px;padding:0 14px 12px;}
      .wt-chat-toast-actions button{flex:1;padding:6px 10px;border-radius:6px;font-size:12px;cursor:pointer;}
      .wt-chat-toast-actions .wt-primary{background:linear-gradient(135deg,#8b5cf6,#d946ef);color:#fff;border:none;}
      .wt-chat-toast-actions .wt-secondary{background:#fff;border:1px solid #e5e7eb;color:#1f2937;}
    `;
    document.head.appendChild(style);
  }

  function showToast(msg) {
    if (visible) { queue.push(msg); return; }
    visible = true;
    injectStyles();

    const el = document.createElement('div');
    el.className = 'wt-chat-toast';
    el.innerHTML = `
      <div class="wt-chat-toast-head">
        <span>New Message</span>
        <button aria-label="Close">×</button>
      </div>
      <div class="wt-chat-toast-body">
        <div class="wt-chat-toast-avatar">${escapeHtml((msg.sender_name || '?').slice(0, 2).toUpperCase())}</div>
        <div>
          <div class="wt-chat-toast-sender">${escapeHtml(msg.sender_name || 'User')}</div>
          <div class="wt-chat-toast-msg">${escapeHtml(msg.content || '📎 Attachment')}</div>
        </div>
      </div>
      <div class="wt-chat-toast-actions">
        <button class="wt-secondary">Dismiss</button>
        <button class="wt-primary">Reply</button>
      </div>
    `;
    document.body.appendChild(el);

    const dismiss = () => {
      el.style.animation = 'wtSlideOut .25s ease-out forwards';
      setTimeout(() => {
        el.remove();
        visible = false;
        if (queue.length) showToast(queue.shift());
      }, 250);
    };

    el.querySelector('.wt-chat-toast-head button').onclick = dismiss;
    el.querySelector('.wt-secondary').onclick = dismiss;
    el.querySelector('.wt-primary').onclick = () => {
      window.location.href = chatUrl();
    };

    setTimeout(dismiss, 7000);
  }

  function updateBadge(count) {
    const badge = document.getElementById('chatBadge');
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : count;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }

  async function poll() {
    try {
      const res = await fetch('/api/chat/unread-count/', {
        headers: { Authorization: `Token ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        updateBadge(data.total_unread || 0);
      }
    } catch (e) { /* ignore */ }

    const checkedAt = new Date().toISOString();
    try {
      const res = await fetch(`/api/chat/recent/?since=${encodeURIComponent(lastCheck)}`, {
        headers: { Authorization: `Token ${token}` }
      });
      lastCheck = checkedAt;
      if (!res.ok) return;
      const recent = await res.json();
      if (!Array.isArray(recent)) return;
      recent.forEach((msg) => {
        if (!notified.has(msg.id)) {
          notified.add(msg.id);
          showToast(msg);
        }
      });
      if (notified.size > 300) {
        Array.from(notified).slice(0, 100).forEach((id) => notified.delete(id));
      }
    } catch (e) {
      lastCheck = checkedAt;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    poll();
    setInterval(poll, 4000);
  });
})();