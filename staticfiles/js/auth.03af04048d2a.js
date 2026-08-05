/**
 * Authentication Module
 * Handles user authentication, session management, and role-based access control
 */

// ========================================
// TOKEN & SESSION MANAGEMENT
// ========================================

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
  const token = localStorage.getItem('token');
  return !!token;
}

/**
 * Get stored token
 */
function getStoredToken() {
  return localStorage.getItem('token');
}

/**
 * Set authentication data
 */
function setAuthData(token, user, is_admin, company_name) {
  localStorage.setItem('token', token);
  localStorage.setItem('user', JSON.stringify(user));
  localStorage.setItem('is_admin', is_admin);
  if (company_name) {
    localStorage.setItem('company_name', company_name);
  }
}

/**
 * Clear all authentication data
 */
function clearAuthData() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  localStorage.removeItem('is_admin');
  localStorage.removeItem('company_name');
}

/**
 * Get current user
 */
function getCurrentUser() {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch (e) {
      console.error('Error parsing user data:', e);
      return null;
    }
  }
  return null;
}

/**
 * Check if current user is admin
 */
function isAdmin() {
  return localStorage.getItem('is_admin') === 'true';
}

/**
 * Check if current user is superuser
 */
function isSuperuser() {
  const user = getCurrentUser();
  return user && user.is_superuser;
}

/**
 * Get company name
 */
function getCompanyName() {
  return localStorage.getItem('company_name') || 'HAEGL';
}

/**
 * Set company name
 */
function setCompanyName(name) {
  localStorage.setItem('company_name', name);
  // Dispatch event for cross-tab sync
  window.dispatchEvent(new Event('company-name-updated'));
}

/**
 * Directly patch the common sidebar DOM elements used across every
 * admin/employee page (id="sidebarCompanyName", id="logoInitials",
 * id="companyLabel"), in addition to dispatching the event. This is a
 * belt-and-braces fix: some pages listen for 'company-name-updated' via
 * setupCompanyNameListener(), but not every page wires that up, so we
 * update the DOM directly wherever these elements exist.
 */
function applyCompanyNameToSidebar(name) {
  if (!name) return;

  const sidebarNameEl = document.getElementById('sidebarCompanyName');
  if (sidebarNameEl) sidebarNameEl.textContent = name;

  const logoInitialsEl = document.getElementById('logoInitials');
  if (logoInitialsEl) {
    logoInitialsEl.textContent = name
      .split(' ')
      .map(w => w[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();
  }

  const companyLabelEl = document.getElementById('companyLabel');
  if (companyLabelEl) {
    // Preserve whatever suffix a page already uses (e.g. "· ADMIN CONSOLE"),
    // by only replacing the part before the first "·" if present.
    const existing = companyLabelEl.textContent || '';
    const dotIndex = existing.indexOf('·');
    if (dotIndex !== -1) {
      companyLabelEl.textContent = `${name} ${existing.substring(dotIndex)}`;
    } else {
      companyLabelEl.textContent = name;
    }
  }
}

/**
 * Fetches the current user's real company name from the server and
 * repairs localStorage + the visible sidebar if it was stale, missing,
 * or wrong. This runs automatically from requireAdmin()/requireEmployee()
 * on every protected page load, so the sidebar can no longer get stuck
 * showing a stale or default company name — it self-corrects every time.
 * This is fire-and-forget: it does not block page rendering.
 */
function refreshCompanyNameFromServer() {
  const token = getStoredToken();
  if (!token) return;

  fetch('/api/me/', {
    headers: {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    }
  })
    .then(res => (res.ok ? res.json() : null))
    .then(user => {
      if (!user) return;
      const companyName = user.company_name || (user.profile && user.profile.company_name) || '';
      const current = localStorage.getItem('company_name');

      if (companyName && companyName !== current) {
        setCompanyName(companyName); // updates localStorage + dispatches event
      }

      // Always sync the DOM directly too, regardless of whether the
      // stored value already matched, since the page may have rendered
      // with the OLD value before this fetch resolved.
      if (companyName) {
        applyCompanyNameToSidebar(companyName);
      }
    })
    .catch(err => {
      console.error('refreshCompanyNameFromServer failed:', err);
    });
}

// ========================================
// AUTHENTICATION GUARDS
// ========================================

/**
 * Guard: Require authentication
 * Redirects to login if not authenticated
 */
function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = '/';
    return false;
  }
  return true;
}

/**
 * Guard: Require admin role
 * Redirects to employee dashboard if not admin
 */
function requireAdmin() {
  if (!isAuthenticated()) {
    window.location.href = '/';
    return false;
  }
  if (!isAdmin()) {
    window.location.href = '/employee/worklog/';
    return false;
  }
  // Self-heal the sidebar's company name from the server on every load.
  refreshCompanyNameFromServer();
  return true;
}

/**
 * Guard: Require employee role
 * Redirects to admin dashboard if not employee
 */
function requireEmployee() {
  if (!isAuthenticated()) {
    window.location.href = '/';
    return false;
  }
  if (isAdmin()) {
    window.location.href = '/admin/worklog/';
    return false;
  }
  // Self-heal the sidebar's company name from the server on every load.
  refreshCompanyNameFromServer();
  return true;
}

/**
 * Guard: Require superuser role
 * Redirects to home if not superuser
 */
function requireSuperuser() {
  if (!isAuthenticated()) {
    window.location.href = '/';
    return false;
  }
  if (!isSuperuser()) {
    window.location.href = '/';
    return false;
  }
  return true;
}

// ========================================
// LOGIN / LOGOUT HANDLERS
// ========================================

/**
 * Handle login response
 */
async function handleLoginResponse(data, role) {
  if (data.error) {
    throw new Error(data.error);
  }

  // Store auth data
  setAuthData(
    data.token,
    data.user,
    data.is_admin,
    data.company_name || data.user?.company_name || data.user?.company || ''
  );

  // Redirect based on role and user type
  if (data.is_superuser) {
    window.location.href = '/superadmin/';
  } else if (role === 'admin' && !data.is_admin) {
    throw new Error('You do not have admin access.');
  } else if (role === 'employee' && data.is_admin) {
    throw new Error('Please use Admin Login.');
  } else {
    // Redirect to appropriate dashboard
    window.location.href = data.is_admin ? '/admin/worklog/' : '/employee/worklog/';
  }
}

/**
 * Handle logout
 */
async function handleLogout() {
  try {
    // Call logout API if available
    const response = await fetch('/api/logout/', {
      method: 'POST',
      headers: {
        'Authorization': `Token ${getStoredToken()}`,
        'Content-Type': 'application/json'
      }
    });
    // Don't throw on error, just continue with logout
  } catch (error) {
    console.error('Logout API failed:', error);
  } finally {
    // Always clear local data
    clearAuthData();
    window.location.href = '/';
  }
}

/**
 * Verify authentication with server
 */
async function verifyAuth() {
  try {
    const response = await fetch('/api/me/', {
      headers: {
        'Authorization': `Token ${getStoredToken()}`,
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const user = await response.json();
      // Update stored user data
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('is_admin', user.is_admin);
      return user;
    } else {
      // Invalid token, clear auth
      clearAuthData();
      return null;
    }
  } catch (error) {
    console.error('Auth verification failed:', error);
    clearAuthData();
    return null;
  }
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

/**
 * Get user initials from name
 */
function getUserInitials(name) {
  if (!name) return 'CO';
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return 'CO';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

/**
 * Get greeting based on time of day
 */
function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return { text: 'Good morning', emoji: '🌅' };
  if (hour < 17) return { text: 'Good afternoon', emoji: '☀️' };
  return { text: 'Good evening', emoji: '🌙' };
}

/**
 * Format date for display
 */
function formatDate(dateStr) {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Format time for display
 */
function formatTime(dateStr) {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });
}

// ========================================
// EVENT LISTENERS
// ========================================

/**
 * Listen for company name updates from other tabs
 */
function setupCompanyNameListener(callback) {
  window.addEventListener('company-name-updated', () => {
    const newName = getCompanyName();
    if (callback) callback(newName);
  });

  // Also listen for storage events (cross-tab)
  window.addEventListener('storage', (e) => {
    if (e.key === 'company_name' && e.newValue) {
      if (callback) callback(e.newValue);
    }
  });
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    isAuthenticated,
    getStoredToken,
    setAuthData,
    clearAuthData,
    getCurrentUser,
    isAdmin,
    isSuperuser,
    getCompanyName,
    setCompanyName,
    requireAuth,
    requireAdmin,
    requireEmployee,
    requireSuperuser,
    handleLoginResponse,
    handleLogout,
    verifyAuth,
    getUserInitials,
    getGreeting,
    formatDate,
    formatTime,
    setupCompanyNameListener
  };
}