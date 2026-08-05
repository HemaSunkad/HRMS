/**
 * Auth Guard Module
 * Exposes WT_AUTH global for authentication guards
 */

(function() {
  'use strict';

  // Check if user is authenticated
  function isAuthenticated() {
    const token = localStorage.getItem('token');
    return !!token;
  }

  // Get current user
  function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch (e) {
        return null;
      }
    }
    return null;
  }

  // Check if current user is admin
  function isAdmin() {
    return localStorage.getItem('is_admin') === 'true';
  }

  // Guard: Require authentication
  function requireAuth() {
    if (!isAuthenticated()) {
      window.location.href = '/';
      return false;
    }
    return true;
  }

  // Guard: Require admin role
  function requireAdmin() {
    if (!isAuthenticated()) {
      window.location.href = '/';
      return false;
    }
    if (!isAdmin()) {
      window.location.href = '/employee/worklog/';
      return false;
    }
    return true;
  }

  // Guard: Require employee role
  function requireEmployee() {
    if (!isAuthenticated()) {
      window.location.href = '/';
      return false;
    }
    if (isAdmin()) {
      window.location.href = '/admin/worklog/';
      return false;
    }
    return true;
  }

  /**
   * Pull a company name out of the /api/me/ response no matter how it's
   * nested. Tries the most likely field paths in order, then falls back
   * to 'HAEGL' only if nothing at all is found.
   */
  function extractCompanyName(user) {
    if (!user) return null;
    const candidates = [
      user.company_name,
      user.companyName,
      user.company?.name,
      user.company?.company_name,
      user.organization,
      user.organization_name,
      user.business_name,
      user.admin_profile?.company_name,
      user.profile?.company_name,
      user.employer?.company_name,
      user.employer_name,
    ];
    for (const c of candidates) {
      if (typeof c === 'string' && c.trim().length > 0) return c.trim();
    }
    return null;
  }

  // Verify authentication and dispatch ready event
  async function verifyAndDispatch() {
    const checkingEl = document.getElementById('auth-checking');
    const contentEl = document.getElementById('auth-content');

    if (!checkingEl || !contentEl) {
      // Elements not found, dispatch event anyway
      window.dispatchEvent(new Event('wt-auth-ready'));
      return;
    }

    if (!requireAuth()) {
      return;
    }

    try {
      const response = await fetch('/api/me/', {
        headers: {
          'Authorization': `Token ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const user = await response.json();
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('is_admin', user.is_admin);

        // Store the real company name so the sidebar/hero show the
        // employee's own company instead of the generic fallback.
        const companyName = extractCompanyName(user);
        if (companyName) {
          localStorage.setItem('company_name', companyName);
        }
        window.dispatchEvent(new Event('company-name-updated'));

        // Hide checking, show content
        checkingEl.style.display = 'none';
        contentEl.style.display = 'block';

        // Dispatch ready event
        window.dispatchEvent(new Event('wt-auth-ready'));
      } else {
        // Invalid token
        localStorage.clear();
        window.location.href = '/';
      }
    } catch (error) {
      console.error('Auth verification failed:', error);
      localStorage.clear();
      window.location.href = '/';
    }
  }

  // Expose WT_AUTH global
  window.WT_AUTH = {
    isAuthenticated,
    getCurrentUser,
    isAdmin,
    requireAuth,
    requireAdmin,
    requireEmployee,
    verifyAndDispatch,
    extractCompanyName
  };

  // Auto-verify when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', verifyAndDispatch);
  } else {
    verifyAndDispatch();
  }
})();