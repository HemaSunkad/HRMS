/**
 * Company Name Module
 * Handles company name display and updates across the application
 */

(function() {
  'use strict';

  // Get company name from localStorage
  function getCompanyName() {
    return localStorage.getItem('company_name') || 'HAEGL';
  }

  // Get user initials from company name
  function getCompanyInitials(name) {
    if (!name) return 'CO';
    const words = name.trim().split(/\s+/).filter(Boolean);
    if (words.length === 0) return 'CO';
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[1][0]).toUpperCase();
  }

  // Update all company name elements on the page
  function updateCompanyNames() {
    const companyName = getCompanyName();
    const initials = getCompanyInitials(companyName);

    // Update elements with data-company-name attribute
    document.querySelectorAll('[data-company-name]').forEach(el => {
      el.textContent = companyName;
    });

    // Update elements with data-company-initials attribute
    document.querySelectorAll('[data-company-initials]').forEach(el => {
      el.textContent = initials;
    });

    // Update elements with data-company-title attribute
    document.querySelectorAll('[data-company-title]').forEach(el => {
      el.title = companyName;
    });
  }

  // Listen for company name updates
  function setupListeners() {
    // Listen for storage events (cross-tab sync)
    window.addEventListener('storage', (e) => {
      if (e.key === 'company_name') {
        updateCompanyNames();
      }
    });

    // Listen for custom events
    window.addEventListener('company-name-updated', updateCompanyNames);
  }

  // Initialize on DOM ready
  function init() {
    updateCompanyNames();
    setupListeners();
  }

  // Auto-initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose functions globally
  window.WT_COMPANY_NAME = {
    getCompanyName,
    getCompanyInitials,
    updateCompanyNames
  };
})();
