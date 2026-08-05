/**
 * Central Configuration File
 * All API URLs and configuration settings should be defined here
 * to avoid hardcoded values throughout the application
 */

// API Configuration
const API_CONFIG = {
  // Backend API URL - Use relative path for production, or set explicit URL for development
  // Empty string means use the same domain as the frontend (works for both dev and prod)
  BASE_URL: '',  // For development with separate backend, use: 'http://127.0.0.1:8001'

  // API Endpoints (automatically prefixed with BASE_URL)
  ENDPOINTS: {
    // Auth
    LOGIN: '/api/login/',
    LOGOUT: '/api/logout/',
    REGISTER: '/api/register/',
    ME: '/api/me/',
    GOOGLE_LOGIN: '/api/admin/google-login/',
    VERIFY_ADMIN_CODE: '/api/verify-admin-code/',
    SIGNUP_COMPANY: '/api/admin/signup-company/',

    // Profile
    UPDATE_PROFILE: '/api/profile/update/',
    CHANGE_PASSWORD: '/api/profile/change-password/',

    // Employee
    EMPLOYEE_STATS: '/api/employee/stats/',
    EMPLOYEE_ENTRIES: '/api/employee/entries/',
    EMPLOYEE_ENTRY_DETAIL: (id) => `/api/employee/entries/${id}/`,
    ASSIGNED_TASKS: '/api/employee/assigned-tasks/',
    ASSIGNED_TASK_ACTION: (id) => `/api/employee/assigned-tasks/${id}/action/`,

    // Admin
    ADMIN_STATS: '/api/admin/stats/',
    ADMIN_ANALYTICS: '/api/admin/analytics/',
    ADMIN_REPORTS: '/api/admin/reports/',
    ADMIN_REPORT_DETAIL: (id) => `/api/admin/reports/${id}/`,
    ADMIN_REPORT_REVIEW: (id) => `/api/admin/reports/${id}/review/`,
    ADMIN_EMPLOYEES: '/api/admin/employees/',
    ADMIN_EMPLOYEE_ENTRIES: (id) => `/api/admin/employees/${id}/entries/`,
    ADMIN_EMPLOYEE_DELETE: (id) => `/api/admin/employees/${id}/delete/`,
    ADMIN_ENTRY_REVIEW: (id) => `/api/admin/entries/${id}/review/`,
    ADMIN_ASSIGN_TASK: '/api/admin/assign-task/',
    ADMIN_INVITE: '/api/admin/invite/',

    // Reassignment
    ALL_EMPLOYEES_REASSIGN: '/api/employees/all/',
    REASSIGN_WORK_ENTRY: (id) => `/api/work-entries/${id}/reassign/`,
    REASSIGN_ASSIGNED_TASK: (id) => `/api/assigned-tasks/${id}/reassign/`,

    // Chat
    CHAT_ROOMS: '/api/chat/rooms/',
    CHAT_DM_ROOM: '/api/chat/rooms/dm/',
    CHAT_MESSAGES: (id) => `/api/chat/rooms/${id}/messages/`,
    CHAT_ROOM_READ: (id) => `/api/chat/rooms/${id}/read/`,
    CHAT_ROOM_DELETE: (id) => `/api/chat/rooms/${id}/delete/`,
    CHAT_USERS: '/api/chat/users/',
    CHAT_RECENT: '/api/chat/recent/',
    CHAT_UNREAD_COUNT: '/api/chat/unread-count/',
    CHAT_MESSAGE_DELETE: (id) => `/api/chat/messages/${id}/delete/`,

    // Push notifications
    PUSH_SUBSCRIBE: '/api/push-subscriptions/',

    // Superadmin
    SUPERADMIN_STATS: '/api/superadmin/dashboard-stats/',
    SUPERADMIN_FILTER_OPTIONS: '/api/superadmin/filter-options/',
    SUPERADMIN_COMPANIES: '/api/superadmin/companies/',
    SUPERADMIN_COMPANY_CREATE: '/api/superadmin/companies/create/',
    SUPERADMIN_COMPANY_DETAIL: (id) => `/api/superadmin/companies/${id}/`,
    SUPERADMIN_EMPLOYEES: '/api/superadmin/employees/',
    SUPERADMIN_EMPLOYEE_DETAIL: (id) => `/api/superadmin/employees/${id}/`,
    SUPERADMIN_WORK_ENTRIES: '/api/superadmin/work-entries/',
    SUPERADMIN_DELETE_WORK_ENTRY: (id) => `/api/superadmin/work-entries/${id}/`,
    SUPERADMIN_TASKS: '/api/superadmin/tasks/',
    SUPERADMIN_DELETE_TASK: (id) => `/api/superadmin/tasks/${id}/`,
    SUPERADMIN_INVITES: '/api/superadmin/invites/',
    SUPERADMIN_DELETE_INVITE: (id) => `/api/superadmin/invites/${id}/`,
    SUPERADMIN_INVITE_DETAIL: (id) => `/api/superadmin/invites/${id}/`,
    SUPERADMIN_REPORTS: '/api/superadmin/reports/',
    SUPERADMIN_REPORT_DETAIL: (id) => `/api/superadmin/reports/${id}/`,
    SUPERADMIN_USERS: '/api/superadmin/users/',
    SUPERADMIN_USER_CREATE: '/api/superadmin/users/create/',
    SUPERADMIN_USER_DETAIL: (id) => `/api/superadmin/users/${id}/`,
  },

  // Get full URL for an endpoint
  getUrl(endpointKey, ...args) {
    const endpoint = this.ENDPOINTS[endpointKey];
    const path = typeof endpoint === 'function' ? endpoint(...args) : endpoint;
    return this.BASE_URL + path;
  },

  // Get authentication headers
  getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Token ${token}` })
    };
  },

  // Get multipart headers for file uploads
  getMultipartHeaders() {
    const token = localStorage.getItem('token');
    const headers = {};
    if (token) {
      headers['Authorization'] = `Token ${token}`;
    }
    return headers;
  }
};

// App Configuration
const APP_CONFIG = {
  // App name
  NAME: 'WorkTrack',

  // Default company name
  DEFAULT_COMPANY_NAME: 'HAEGL',

  // Token storage key
  TOKEN_KEY: 'token',

  // User storage key
  USER_KEY: 'user',

  // Admin flag key
  IS_ADMIN_KEY: 'is_admin',

  // Company name key
  COMPANY_NAME_KEY: 'company_name',

  // Toast duration (ms)
  TOAST_DURATION: 3000,

  // Refresh interval for chat (ms)
  CHAT_REFRESH_INTERVAL: 5000,

  // Session timeout (ms) - optional
  SESSION_TIMEOUT: null // No timeout by default
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { API_CONFIG, APP_CONFIG };
}