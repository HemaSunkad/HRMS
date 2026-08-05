/**
 * Utility Functions Module
 * Common utility functions for DOM manipulation, formatting, etc.
 */

// ========================================
// DOM MANIPULATION
// ========================================

/**
 * Create element with attributes and content
 */
function createElement(tag, options = {}) {
  const el = document.createElement(tag);

  // Set attributes
  if (options.id) el.id = options.id;
  if (options.className) el.className = options.className;
  if (options.attributes) {
    Object.entries(options.attributes).forEach(([key, value]) => {
      el.setAttribute(key, value);
    });
  }

  // Set content
  if (options.text) el.textContent = options.text;
  if (options.html) el.innerHTML = options.html;

  // Set styles
  if (options.styles) {
    Object.entries(options.styles).forEach(([key, value]) => {
      el.style[key] = value;
    });
  }

  // Add event listeners
  if (options.events) {
    Object.entries(options.events).forEach(([event, handler]) => {
      el.addEventListener(event, handler);
    });
  }

  // Append children
  if (options.children) {
    options.children.forEach(child => {
      if (typeof child === 'string') {
        el.appendChild(document.createTextNode(child));
      } else if (child instanceof Node) {
        el.appendChild(child);
      }
    });
  }

  return el;
}

/**
 * Query selector wrapper
 */
function $(selector, context = document) {
  return context.querySelector(selector);
}

/**
 * Query selector all wrapper
 */
function $$(selector, context = document) {
  return Array.from(context.querySelectorAll(selector));
}

/**
 * Add class to element
 */
function addClass(el, className) {
  if (el && className) el.classList.add(...className.split(' '));
}

/**
 * Remove class from element
 */
function removeClass(el, className) {
  if (el && className) el.classList.remove(...className.split(' '));
}

/**
 * Toggle class on element
 */
function toggleClass(el, className) {
  if (el && className) el.classList.toggle(className);
}

/**
 * Check if element has class
 */
function hasClass(el, className) {
  return el && el.classList.contains(className);
}

/**
 * Show element
 */
function show(el, display = 'block') {
  if (el) {
    el.style.display = display;
    addClass(el, 'animate-fadeIn');
  }
}

/**
 * Hide element
 */
function hide(el) {
  if (el) el.style.display = 'none';
}

/**
 * Remove element from DOM
 */
function remove(el) {
  if (el && el.parentNode) {
    el.parentNode.removeChild(el);
  }
}

/**
 * Empty element (remove all children)
 */
function empty(el) {
  if (el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }
}

// ========================================
// HTML TEMPLATES
// ========================================

/**
 * Create HTML from template string
 */
function html(strings, ...values) {
  return strings.reduce((result, string, i) => {
    const value = values[i - 1];
    return result + string + (value !== undefined ? value : '');
  }, '');
}

/**
 * Render template string with data
 */
function renderTemplate(template, data) {
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return data[key] !== undefined ? data[key] : '';
  });
}

// ========================================
// FORMATTING FUNCTIONS
// ========================================

/**
 * Format minutes to hours and minutes
 */
function formatMinutes(mins) {
  if (mins === null || mins === undefined || isNaN(mins)) return '—';
  const m = Math.round(mins);
  const h = Math.floor(m / 60);
  const rem = m % 60;
  if (h === 0) return `${rem}m`;
  if (rem === 0) return `${h}h`;
  return `${h}h ${rem}m`;
}

/**
 * Format elapsed time in ms to HH:MM:SS
 */
function formatElapsed(ms) {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
}

/**
 * Format date to readable string
 */
function formatDate(dateStr, format = 'short') {
  if (!dateStr) return '—';
  const date = new Date(dateStr);

  if (format === 'short') {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  } else if (format === 'long') {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  } else if (format === 'time') {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  } else if (format === 'datetime') {
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  return date.toLocaleDateString();
}

/**
 * Format clock time from ISO string
 */
function formatClockTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Format number with commas
 */
function formatNumber(num) {
  if (num === null || num === undefined) return '—';
  return num.toLocaleString('en-US');
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'USD') {
  if (amount === null || amount === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount);
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength) {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

/**
 * Pluralize word
 */
function pluralize(count, singular, plural) {
  if (count === 1) return singular;
  return plural || singular + 's';
}

// ========================================
// TIME FUNCTIONS
// ========================================

/**
 * Get relative time (e.g., "2 hours ago")
 */
function getRelativeTime(dateStr) {
  if (!dateStr) return '—';

  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
  if (diffDay < 30) return `${Math.floor(diffDay / 7)} week${Math.floor(diffDay / 7) > 1 ? 's' : ''} ago`;
  if (diffDay < 365) return `${Math.floor(diffDay / 30)} month${Math.floor(diffDay / 30) > 1 ? 's' : ''} ago`;
  return `${Math.floor(diffDay / 365)} year${Math.floor(diffDay / 365) > 1 ? 's' : ''} ago`;
}

/**
 * Get today's date in YYYY-MM-DD format
 */
function getTodayDate() {
  return new Date().toISOString().split('T')[0];
}

/**
 * Check if date is today
 */
function isToday(dateStr) {
  if (!dateStr) return false;
  const date = new Date(dateStr);
  const today = new Date();
  return date.toDateString() === today.toDateString();
}

// ========================================
// VALIDATION FUNCTIONS
// ========================================

/**
 * Validate email format
 */
function isValidEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

/**
 * Validate password strength
 */
function validatePassword(password) {
  const checks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]~`]/.test(password)
  };

  const isValid = Object.values(checks).every(Boolean);

  return { checks, isValid };
}

/**
 * Validate required fields
 */
function validateRequired(fields) {
  const errors = {};

  fields.forEach(field => {
    if (!field.value || field.value.trim() === '') {
      errors[field.name] = `${field.label} is required`;
    }
  });

  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
}

// ========================================
// STORAGE FUNCTIONS
// ========================================

/**
 * Set item in localStorage with JSON stringify
 */
function setStorageItem(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (e) {
    console.error('Error saving to localStorage:', e);
    return false;
  }
}

/**
 * Get item from localStorage with JSON parse
 */
function getStorageItem(key, defaultValue = null) {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (e) {
    console.error('Error reading from localStorage:', e);
    return defaultValue;
  }
}

/**
 * Remove item from localStorage
 */
function removeStorageItem(key) {
  try {
    localStorage.removeItem(key);
    return true;
  } catch (e) {
    console.error('Error removing from localStorage:', e);
    return false;
  }
}

// ========================================
// URL & QUERY STRING FUNCTIONS
// ========================================

/**
 * Get query parameter value
 */
function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

/**
 * Get all query parameters as object
 */
function getQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const result = {};
  for (const [key, value] of params) {
    result[key] = value;
  }
  return result;
}

/**
 * Set query parameter
 */
function setQueryParam(name, value) {
  const url = new URL(window.location);
  url.searchParams.set(name, value);
  window.history.pushState({}, '', url);
}

/**
 * Remove query parameter
 */
function removeQueryParam(name) {
  const url = new URL(window.location);
  url.searchParams.delete(name);
  window.history.pushState({}, '', url);
}

// ========================================
// ARRAY & OBJECT UTILITIES
// ========================================

/**
 * Deep clone object
 */
function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Merge objects
 */
function mergeObjects(...objs) {
  return Object.assign({}, ...objs);
}

/**
 * Pick keys from object
 */
function pick(obj, keys) {
  return keys.reduce((result, key) => {
    if (obj.hasOwnProperty(key)) {
      result[key] = obj[key];
    }
    return result;
  }, {});
}

/**
 * Omit keys from object
 */
function omit(obj, keys) {
  const result = { ...obj };
  keys.forEach(key => delete result[key]);
  return result;
}

/**
 * Group array by key
 */
function groupBy(array, key) {
  return array.reduce((result, item) => {
    const group = item[key];
    if (!result[group]) {
      result[group] = [];
    }
    result[group].push(item);
    return result;
  }, {});
}

/**
 * Unique array values
 */
function unique(array) {
  return [...new Set(array)];
}

/**
 * Sort array by key
 */
function sortBy(array, key, order = 'asc') {
  return array.sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];

    if (aVal < bVal) return order === 'asc' ? -1 : 1;
    if (aVal > bVal) return order === 'asc' ? 1 : -1;
    return 0;
  });
}

// ========================================
// MATH UTILITIES
// ========================================

/**
 * Clamp number between min and max
 */
function clamp(num, min, max) {
  return Math.min(Math.max(num, min), max);
}

/**
 * Map value from one range to another
 */
function mapRange(value, inMin, inMax, outMin, outMax) {
  return (value - inMin) * (outMax - outMin) / (inMax - inMin) + outMin;
}

/**
 * Generate random number between min and max
 */
function random(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Round to decimal places
 */
function roundTo(num, decimals) {
  const factor = Math.pow(10, decimals);
  return Math.round(num * factor) / factor;
}

// ========================================
// COLOR UTILITIES
// ========================================

/**
 * Convert hex to RGB
 */
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

/**
 * Convert RGB to hex
 */
function rgbToHex(r, g, b) {
  return '#' + [r, g, b].map(x => {
    const hex = x.toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('');
}

/**
 * Lighten color
 */
function lightenColor(hex, percent) {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;

  const factor = 1 + percent / 100;
  const r = Math.min(255, Math.round(rgb.r * factor));
  const g = Math.min(255, Math.round(rgb.g * factor));
  const b = Math.min(255, Math.round(rgb.b * factor));

  return rgbToHex(r, g, b);
}

/**
 * Darken color
 */
function darkenColor(hex, percent) {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;

  const factor = 1 - percent / 100;
  const r = Math.round(rgb.r * factor);
  const g = Math.round(rgb.g * factor);
  const b = Math.round(rgb.b * factor);

  return rgbToHex(r, g, b);
}

// ========================================
// FILE UTILITIES
// ========================================

/**
 * Format file size
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Get file extension
 */
function getFileExtension(filename) {
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2);
}

/**
 * Check if file is image
 */
function isImageFile(filename) {
  const ext = getFileExtension(filename).toLowerCase();
  return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext);
}

/**
 * Check if file is PDF
 */
function isPdfFile(filename) {
  return getFileExtension(filename).toLowerCase() === 'pdf';
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    createElement,
    $,
    $$,
    addClass,
    removeClass,
    toggleClass,
    hasClass,
    show,
    hide,
    remove,
    empty,
    html,
    renderTemplate,
    formatMinutes,
    formatElapsed,
    formatDate,
    formatClockTime,
    formatNumber,
    formatCurrency,
    truncate,
    pluralize,
    getRelativeTime,
    getTodayDate,
    isToday,
    isValidEmail,
    validatePassword,
    validateRequired,
    setStorageItem,
    getStorageItem,
    removeStorageItem,
    getQueryParam,
    getQueryParams,
    setQueryParam,
    removeQueryParam,
    deepClone,
    mergeObjects,
    pick,
    omit,
    groupBy,
    unique,
    sortBy,
    clamp,
    mapRange,
    random,
    roundTo,
    hexToRgb,
    rgbToHex,
    lightenColor,
    darkenColor,
    formatFileSize,
    getFileExtension,
    isImageFile,
    isPdfFile
  };
}
