/**
 * Sidebar Module
 * Handles sidebar functionality for employee dashboard
 */

(function() {
  'use strict';

  let sidebarOpen = false;
  let unreadCount = 0;

  // Initialize sidebar
  
    function initSidebar() {
  const mobileToggle = document.getElementById('mobileMenuToggle');
  const backdrop = document.getElementById('mobileBackdrop');
  const sidebar = document.getElementById('sidebar');
  const collapseToggle = document.getElementById('collapseBtn');
  const logoutBtn = document.querySelector('.sidebar-footer button, aside button[onclick="handleLogout()"]');

    if (mobileToggle) {
      mobileToggle.addEventListener('click', toggleSidebar);
    }

    if (backdrop) {
      backdrop.addEventListener('click', closeSidebar);
    }

    if (collapseToggle) {
      collapseToggle.addEventListener('click', toggleCollapse);
    }

    if (logoutBtn) {
      logoutBtn.addEventListener('click', handleLogout);
    }

    // Load company name
    loadCompanyName();

    // Load unread count
    loadUnreadCount();

    // Set up interval to check for unread messages
    setInterval(loadUnreadCount, 10000);

    // Listen for company name updates
    window.addEventListener('company-name-updated', loadCompanyName);
  }

  // Toggle sidebar (mobile)
  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    const backdrop = document.getElementById('sidebar-backdrop');
    const sidebar = document.getElementById('wt-sidebar');

    if (backdrop) {
      backdrop.style.display = sidebarOpen ? 'block' : 'none';
    }

    if (sidebar) {
      if (sidebarOpen) {
        sidebar.classList.remove('-translate-x-full');
        sidebar.classList.add('translate-x-0');
      } else {
        sidebar.classList.add('-translate-x-full');
        sidebar.classList.remove('translate-x-0');
      }
    }
  }

  // Close sidebar
  function closeSidebar() {
    sidebarOpen = false;
    const backdrop = document.getElementById('sidebar-backdrop');
    const sidebar = document.getElementById('wt-sidebar');

    if (backdrop) {
      backdrop.style.display = 'none';
    }

    if (sidebar) {
      sidebar.classList.add('-translate-x-full');
      sidebar.classList.remove('translate-x-0');
    }
  }

  // Toggle sidebar collapse
  function toggleCollapse() {
    const sidebar = document.getElementById('wt-sidebar');
    if (sidebar) {
      sidebar.classList.toggle('collapsed');
    }
  }

  // Load company name
  function loadCompanyName() {
    const companyName = localStorage.getItem('company_name') || 'HAEGL';
    const initials = companyName.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();

    // Update company name elements
    document.querySelectorAll('[data-company-name]').forEach(el => {
      el.textContent = companyName;
    });

    // Update initials elements
    document.querySelectorAll('[data-company-initials]').forEach(el => {
      el.textContent = initials;
    });
  }

  // Load unread count
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

  // Handle logout
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

    // Clear localStorage and redirect
    localStorage.clear();
    window.location.href = '/';
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
  } else {
    initSidebar();
  }

  // Expose functions globally
  window.WT_SIDEBAR = {
    initSidebar,
    toggleSidebar,
    closeSidebar,
    loadCompanyName,
    loadUnreadCount
  };
})();
