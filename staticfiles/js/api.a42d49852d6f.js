/**
 * API Module
 * All API calls to the Django backend
 */

const BASE_URL = '/api';

/**
 * Get authentication token from localStorage
 */
function getToken() {
  return localStorage.getItem('token');
}

/**
 * Get authentication headers for API requests
 */
function authHeaders() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Token ${token}` })
  };
}

/**
 * Get multipart headers for file uploads
 */
function authHeadersMultipart() {
  const token = getToken();
  const headers = {};
  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }
  return headers;
}

// ========================================
// AUTHENTICATION ENDPOINTS
// ========================================

/**
 * Login with email and password
 */
async function loginAPI(email, password) {
  const res = await fetch(`${BASE_URL}/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return await res.json();
}

/**
 * Register a new user
 */
async function registerAPI(email, password, full_name, is_admin, admin_code) {
  const res = await fetch(`${BASE_URL}/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name, is_admin, admin_code })
  });
  return await res.json();
}

/**
 * Login with Google credential (admin only)
 */
async function googleLoginAPI(credential, admin_code) {
  const res = await fetch(`${BASE_URL}/admin/google-login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential, admin_code })
  });
  return await res.json();
}

/**
 * Logout user
 */
async function logoutAPI() {
  try {
    await fetch(`${BASE_URL}/logout/`, {
      method: 'POST',
      headers: authHeaders()
    });
  } catch (error) {
    console.error('Logout failed:', error);
  } finally {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('is_admin');
  }
}

/**
 * Verify admin code
 */
async function verifyAdminCodeAPI(admin_code) {
  const res = await fetch(`${BASE_URL}/verify-admin-code/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_code })
  });
  return await res.json();
}

/**
 * Get current user info
 */
async function getMe() {
  const res = await fetch(`${BASE_URL}/me/`, {
    headers: authHeaders()
  });
  return await res.json();
}

// ========================================
// EMPLOYEE ENDPOINTS
// ========================================

/**
 * Get employee statistics
 */
async function getEmployeeStats() {
  const res = await fetch(`${BASE_URL}/employee/stats/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get employee analytics data
 */
async function getEmployeeAnalytics(period) {
  let url = `${BASE_URL}/employee/analytics/`;
  if (period) url += `?period=${period}`;
  const res = await fetch(url, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get employee's reports
 */
async function getMyReports() {
  const res = await fetch(`${BASE_URL}/reports/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Submit a new report
 */
async function submitReport(data) {
  const res = await fetch(`${BASE_URL}/reports/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  return await res.json();
}

/**
 * Update a report
 */
async function updateReport(id, data) {
  const res = await fetch(`${BASE_URL}/reports/${id}/`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  return await res.json();
}

/**
 * Delete a report
 */
async function deleteReport(id) {
  const res = await fetch(`${BASE_URL}/reports/${id}/`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get work entries
 */
async function getWorkEntries() {
  const res = await fetch(`${BASE_URL}/employee/entries/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Add a work entry
 */
async function addWorkEntry(data) {
  const res = await fetch(`${BASE_URL}/employee/entries/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  return await res.json();
}

/**
 * Update a work entry
 */
async function updateWorkEntry(id, data) {
  const res = await fetch(`${BASE_URL}/employee/entries/${id}/`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  return await res.json();
}

/**
 * Delete a work entry
 */
async function deleteWorkEntry(id) {
  const res = await fetch(`${BASE_URL}/employee/entries/${id}/`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get assigned tasks
 */
async function getAssignedTasks() {
  const res = await fetch(`${BASE_URL}/employee/assigned-tasks/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Start an assigned task
 */
async function startAssignedTask(id) {
  const res = await fetch(`${BASE_URL}/employee/assigned-tasks/${id}/action/`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ action: 'start' })
  });
  return await res.json();
}

/**
 * Complete an assigned task
 */
async function completeAssignedTask(id) {
  const res = await fetch(`${BASE_URL}/employee/assigned-tasks/${id}/action/`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ action: 'complete' })
  });
  return await res.json();
}

// ========================================
// ADMIN ENDPOINTS
// ========================================

/**
 * Get admin statistics
 */
async function getAdminStats() {
  const res = await fetch(`${BASE_URL}/admin/stats/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get admin analytics data
 */
async function getAdminAnalytics(period) {
  let url = `${BASE_URL}/admin/analytics/`;
  if (period) url += `?period=${period}`;
  const res = await fetch(url, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get all admin reports with optional filters
 */
async function getAdminReports(status, search) {
  let url = `${BASE_URL}/admin/reports/`;
  const params = [];
  if (status) params.push(`status=${status}`);
  if (search) params.push(`search=${search}`);
  if (params.length) url += '?' + params.join('&');

  const res = await fetch(url, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Review a report
 */
async function reviewReport(id, status, manager_comment) {
  const res = await fetch(`${BASE_URL}/admin/reports/${id}/review/`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ status, manager_comment })
  });
  return await res.json();
}

/**
 * Get admin's employees
 */
async function getAdminEmployees() {
  const res = await fetch(`${BASE_URL}/admin/employees/`, {
    headers: authHeaders()
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    console.error('getAdminEmployees failed:', res.status, data);
    return { __error: true, status: res.status, ...data };
  }
  return data;
}

/**
 * Create a new employee
 */
async function createEmployeeAPI(data) {
  const res = await fetch(`${BASE_URL}/admin/employees/create/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  return await res.json();
}

/**
 * Delete an employee
 */
async function deleteEmployee(id) {
  const res = await fetch(`${BASE_URL}/admin/employees/${id}/delete/`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get employee work entries
 */
async function getEmployeeEntries(employeeId) {
  const res = await fetch(`${BASE_URL}/admin/employees/${employeeId}/entries/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Review a work entry
 */
async function reviewWorkEntry(id, review_status, admin_comment) {
  const res = await fetch(`${BASE_URL}/admin/entries/${id}/review/`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ review_status, admin_comment })
  });
  return await res.json();
}

/**
 * Assign a task to an employee
 */
async function assignTask(data) {
  const res = await fetch(`${BASE_URL}/admin/assign-task/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data)
  });
  return await res.json();
}

/**
 * Send co-admin invite
 */
async function sendCoAdminInvite(email) {
  const res = await fetch(`${BASE_URL}/admin/invite/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ email })
  });
  return await res.json();
}

// ========================================
// REASSIGNMENT ENDPOINTS
// ========================================

/**
 * Get all employees for reassignment
 */
async function getAllEmployeesForReassign() {
  const res = await fetch(`${BASE_URL}/employees/all/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Reassign a work entry
 */
async function reassignWorkEntry(id, to_employee_id) {
  const res = await fetch(`${BASE_URL}/work-entries/${id}/reassign/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ to_employee_id })
  });
  return await res.json();
}

/**
 * Reassign an assigned task
 */
async function reassignAssignedTask(id, to_employee_id) {
  const res = await fetch(`${BASE_URL}/assigned-tasks/${id}/reassign/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ to_employee_id })
  });
  return await res.json();
}

// ========================================
// PROFILE ENDPOINTS
// ========================================

/**
 * Update user profile
 */
async function updateProfile(formData) {
  const res = await fetch(`${BASE_URL}/profile/update/`, {
    method: 'PUT',
    headers: authHeadersMultipart(),
    body: formData
  });
  return await res.json();
}

/**
 * Change password
 */
async function changePassword(current_password, new_password) {
  const res = await fetch(`${BASE_URL}/profile/change-password/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ current_password, new_password })
  });
  return await res.json();
}

// ========================================
// CHAT ENDPOINTS
// ========================================

/**
 * Get chat rooms
 */
async function getChatRooms() {
  const res = await fetch(`${BASE_URL}/chat/rooms/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Create a DM room
 */
async function createDMRoom(other_user_id) {
  const res = await fetch(`${BASE_URL}/chat/rooms/dm/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ other_user_id })
  });
  return await res.json();
}

/**
 * Get chat messages for a room
 */
async function getChatMessages(room_id, since) {
  let url = `${BASE_URL}/chat/rooms/${room_id}/messages/`;
  if (since) url += `?since=${encodeURIComponent(since)}`;
  const res = await fetch(url, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Send a chat message
 */
async function sendChatMessage(room_id, content, file) {
  let res;
  if (file) {
    const formData = new FormData();
    formData.append('content', content);
    formData.append('attachment', file);
    res = await fetch(`${BASE_URL}/chat/rooms/${room_id}/messages/`, {
      method: 'POST',
      headers: authHeadersMultipart(),
      body: formData
    });
  } else {
    res = await fetch(`${BASE_URL}/chat/rooms/${room_id}/messages/`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ content })
    });
  }

  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }

  if (!res.ok) {
    throw new Error((data && data.error) || `Failed to send message (${res.status})`);
  }
  return data;
}

/**
 * Delete a chat message
 */
async function deleteChatMessage(message_id) {
  const res = await fetch(`${BASE_URL}/chat/messages/${message_id}/delete/`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get all users for chat
 */
async function getAllUsersForChat() {
  const res = await fetch(`${BASE_URL}/chat/users/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get recent messages
 */
async function getRecentMessages(since) {
  let url = `${BASE_URL}/chat/recent/`;
  if (since) url += `?since=${encodeURIComponent(since)}`;
  const res = await fetch(url, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Get unread message count
 */
async function getUnreadCount() {
  const res = await fetch(`${BASE_URL}/chat/unread-count/`, {
    headers: authHeaders()
  });
  return await res.json();
}

/**
 * Mark a room as read
 */
async function markRoomRead(room_id) {
  const res = await fetch(`${BASE_URL}/chat/rooms/${room_id}/read/`, {
    method: 'POST',
    headers: authHeaders()
  });
  return await res.json();
}
/**
 * Get when other participants last read this room
 */
async function getRoomReadStatus(room_id) {
  const res = await fetch(`${BASE_URL}/chat/rooms/${room_id}/read-status/`, {
    headers: authHeaders()
  });
  return await res.json();
}
/**
 * Delete a chat room
 */
async function deleteChatRoom(room_id) {
  const res = await fetch(`${BASE_URL}/chat/rooms/${room_id}/delete/`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  return await res.json();
}

// ========================================
// PUSH NOTIFICATIONS
// ========================================

/**
 * Save push subscription
 */
async function savePushSubscription(subscription) {
  const res = await fetch(`${BASE_URL}/push-subscriptions/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(subscription)
  });
  return await res.json();
}

// ========================================
// SUPERADMIN ENDPOINTS
// ========================================

/**
 * Superadmin fetch wrapper with 403 handling
 */
async function saFetch(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: authHeaders()
  });

  if (res.status === 403) {
    window.location.href = '/';
    throw new Error('Forbidden');
  }

  return res;
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    loginAPI,
    registerAPI,
    googleLoginAPI,
    logoutAPI,
    verifyAdminCodeAPI,
    getMe,
    getEmployeeStats,
    getMyReports,
    submitReport,
    updateReport,
    deleteReport,
    getWorkEntries,
    addWorkEntry,
    updateWorkEntry,
    deleteWorkEntry,
    getAssignedTasks,
    startAssignedTask,
    completeAssignedTask,
    getAdminStats,
    getAdminAnalytics,
    getAdminReports,
    reviewReport,
    getAdminEmployees,
    createEmployeeAPI,
    deleteEmployee,
    getEmployeeEntries,
    reviewWorkEntry,
    assignTask,
    sendCoAdminInvite,
    getAllEmployeesForReassign,
    reassignWorkEntry,
    reassignAssignedTask,
    updateProfile,
    changePassword,
    getChatRooms,
    createDMRoom,
    getChatMessages,
    sendChatMessage,
    deleteChatMessage,
    getAllUsersForChat,
    getRecentMessages,
    getUnreadCount,
    markRoomRead,
    deleteChatRoom,
    savePushSubscription,
    saFetch,
    getToken,
    authHeaders,
    authHeadersMultipart
  };
}

// Expose WT_API global for browser use
window.WT_API = {
  // Authentication
  loginAPI,
  registerAPI,
  googleLoginAPI,
  logoutAPI,
  verifyAdminCodeAPI,
  getMe,

  // Employee endpoints
  getEmployeeStats,
  getEmployeeAnalytics,
  getMyReports,
  submitReport,
  updateReport,
  deleteReport,
  getWorkEntries,
  addWorkEntry,
  updateWorkEntry,
  deleteWorkEntry,
  getAssignedTasks,
  startAssignedTask,
  completeAssignedTask,

  // Admin endpoints
  getAdminStats,
  getAdminAnalytics,
  getAdminReports,
  reviewReport,
  getAdminEmployees,
  createEmployeeAPI,
  deleteEmployee,
  getEmployeeEntries,
  reviewWorkEntry,
  assignTask,

  // Reassignment
  getAllEmployeesForReassign,
  reassignWorkEntry,
  reassignAssignedTask,

  // Profile
  updateProfile,
  changePassword,

  // Chat
  getChatRooms,
  createDMRoom,
  getChatMessages,
  sendChatMessage,
  deleteChatMessage,
  getAllUsersForChat,
  getRecentMessages,
  getUnreadCount,
  markRoomRead,
  deleteChatRoom,

  // Notifications
  savePushSubscription,
  sendCoAdminInvite,

  // Utilities
  saFetch,
  getToken,
  authHeaders,
  authHeadersMultipart
};
