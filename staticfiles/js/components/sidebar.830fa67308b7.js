/**
 * Sidebar Component
 * Handles sidebar functionality including mobile toggle, company name, chat badge, and logout
 */

// State
let sidebarOpen = false;
let unreadCount = 0;

// Initialize sidebar
function initSidebar() {
  const mobileToggle = document.getElementById('mobileMenuToggle');
  const backdrop = document.getElementById('mobileBackdrop');
  const sidebar = document.getElementById('sidebar');
  const collapseBtn = document.getElementById('collapseBtn');

  if (mobileToggle) {
    mobileToggle.addEventListener('click', toggleSidebar);
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }

  if (collapseBtn) {
    collapseBtn.addEventListener('click', toggleCollapse);
  }

  // Load company name
  loadCompanyName();

  // Load unread count
  loadUnreadCount();

  // Set up interval to check for unread messages
  setInterval(loadUnreadCount, 5000);

  // Listen for company name updates
  window.addEventListener('company-name-updated', loadCompanyName);
}

// Toggle sidebar
function toggleSidebar() {
  sidebarOpen = !sidebarOpen;
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('mobileBackdrop');

  if (!sidebar) return;

  sidebar.classList.toggle('open');
  sidebar.classList.toggle('-translate-x-full');
  sidebar.classList.toggle('translate-x-0');

  if (sidebarOpen) {
    if (backdrop) backdrop.classList.add('show');
    if (backdrop) backdrop.classList.remove('hidden');
  } else {
    if (backdrop) backdrop.classList.remove('show');
    if (backdrop) backdrop.classList.add('hidden');
  }
}

// Close sidebar
function closeSidebar() {
  sidebarOpen = false;
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('mobileBackdrop');

  if (!sidebar) return;

  sidebar.classList.remove('open');
  sidebar.classList.add('-translate-x-full');
  sidebar.classList.remove('translate-x-0');
  if (backdrop) {
    backdrop.classList.remove('show');
    backdrop.classList.add('hidden');
  }
}

// Toggle sidebar collapse
function toggleCollapse() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  sidebar.classList.toggle('collapsed');
}

// Load company name
function loadCompanyName() {
  const companyName = getCompanyName();
  const initials = getUserInitials(companyName);
  const sidebarLogo = document.getElementById('sidebarLogo');
  const sidebarCompanyName = document.getElementById('sidebarCompanyName');

  if (sidebarLogo && companyName) {
    sidebarLogo.textContent = initials;
  }

  if (sidebarCompanyName && companyName) {
    sidebarCompanyName.textContent = companyName;
  }

  document.querySelectorAll('[data-company-name]').forEach((el) => {
    el.textContent = companyName;
  });

  document.querySelectorAll('[data-company-initials]').forEach((el) => {
    el.textContent = initials;
  });

  document.querySelectorAll('[data-company-title]').forEach((el) => {
    el.title = companyName;
  });

  const logoInitials = document.getElementById('logoInitials');
  if (logoInitials) {
    logoInitials.textContent = initials;
  }
}

// Load unread count
async function loadUnreadCount() {
  try {
    const data = await getUnreadCount();
    if (typeof data.total_unread === 'number') {
      unreadCount = data.total_unread;
      updateChatBadge();
    }
  } catch (error) {
    // Silent fail
  }
}

// Update chat badge
function updateChatBadge() {
  const badge = document.getElementById('chatBadge');
  if (!badge) return;

  if (unreadCount > 0) {
    badge.classList.remove('hidden');
    badge.classList.add('flex');
    badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
  } else {
    badge.classList.add('hidden');
    badge.classList.remove('flex');
  }
}

// Handle logout
async function handleLogout() {
  if (!confirm('Are you sure you want to logout?')) return;

  try {
    await logoutAPI();
  } catch (error) {
    console.error('Logout failed:', error);
  }

  // Always redirect to home
  window.location.href = '/';
}

// Export functions
if (typeof window !== 'undefined') {
  window.initSidebar = initSidebar;
  window.toggleSidebar = toggleSidebar;
  window.closeSidebar = closeSidebar;
  window.handleLogout = handleLogout;
}

// Auto-initialize when DOM is ready
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
  } else {
    initSidebar();
  }
}
