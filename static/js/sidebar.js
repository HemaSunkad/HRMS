/**
 * Sidebar Module
 * Handles sidebar functionality for all pages
 */

(function() {
  'use strict';

  let sidebarOpen = false;
  let unreadCount = 0;

  function initSidebar() {
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const backdrop = document.getElementById('mobileBackdrop');
    const sidebar = document.getElementById('sidebar');
    const collapseToggle = document.getElementById('collapseBtn');

    if (mobileToggle) {
      mobileToggle.addEventListener('click', toggleSidebar);
    }

    if (backdrop) {
      backdrop.addEventListener('click', closeSidebar);
    }

    if (collapseToggle) {
      collapseToggle.addEventListener('click', toggleCollapse);
    }

    loadCompanyName();
    loadUnreadCount();
    setInterval(loadUnreadCount, 10000);
    window.addEventListener('company-name-updated', loadCompanyName);
  }

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    const backdrop = document.getElementById('mobileBackdrop');
    const sidebar = document.getElementById('sidebar');
    const body = document.body;

    if (sidebarOpen) {
      if (backdrop) backdrop.classList.remove('hidden');
      if (sidebar) {
        sidebar.classList.remove('-translate-x-full');
        sidebar.classList.add('translate-x-0');
      }
      body.style.overflow = 'hidden';
    } else {
      closeSidebar();
    }
  }

  function closeSidebar() {
    sidebarOpen = false;
    const backdrop = document.getElementById('mobileBackdrop');
    const sidebar = document.getElementById('sidebar');
    const body = document.body;

    if (backdrop) backdrop.classList.add('hidden');
    if (sidebar) {
      sidebar.classList.add('-translate-x-full');
      sidebar.classList.remove('translate-x-0');
    }
    body.style.overflow = '';
  }

  function toggleCollapse() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.toggle('collapsed');
    }
  }

  function loadCompanyName() {
    const companyName = localStorage.getItem('company_name') || 'HAEGL';
    const initials = companyName.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();

    document.querySelectorAll('[data-company-name]').forEach(el => {
      el.textContent = companyName;
    });

    document.querySelectorAll('[data-company-initials]').forEach(el => {
      el.textContent = initials;
    });
  }

  async function loadUnreadCount() {
    const badge = document.getElementById('sidebar-chat-badge');
    if (!badge) return;

    try {
      const response = await fetch('/api/chat/unread-count/', {
        headers: {
          'Authorization': `Token ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.total_unread > 0) {
          badge.style.display = 'inline-flex';
          badge.textContent = data.total_unread > 99 ? '99+' : data.total_unread;
        } else {
          badge.style.display = 'none';
        }
      }
    } catch (error) {
      // Silent fail
    }
  }

  async function handleLogout() {
    if (!confirm('Are you sure you want to logout?')) return;

    try {
      await fetch('/api/logout/', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
    } catch (error) {
      console.error('Logout failed:', error);
    }

    localStorage.clear();
    window.location.href = '/';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
  } else {
    initSidebar();
  }

  window.handleLogout = handleLogout;
  window.WT_SIDEBAR = {
    initSidebar,
    toggleSidebar,
    closeSidebar,
    loadCompanyName,
    loadUnreadCount
  };
})();
