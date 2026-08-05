/**
 * Superadmin Control Panel — shared JS
 * Loaded on every /superadmin/ page, after config.js and api.js.
 */

const SA_BASE = API_CONFIG.BASE_URL; // http://127.0.0.1:8001

/* ---------------------------------------------------------------- */
/* AUTH GUARD                                                        */
/* ---------------------------------------------------------------- */
function saRequireAuth() {
  const token = localStorage.getItem('token');
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  if (!token || !user.is_superuser) {
    window.location.href = '/admin-login/';
    return false;
  }
  return true;
}

function saLogout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  localStorage.removeItem('is_admin');
  window.location.href = '/admin-login/';
}

/* ---------------------------------------------------------------- */
/* FETCH WRAPPER                                                     */
/* ---------------------------------------------------------------- */
async function saFetchJSON(path, options = {}) {
  const res = await fetch(SA_BASE + path, {
    ...options,
    headers: { ...API_CONFIG.getAuthHeaders(), ...(options.headers || {}) }
  });

  if (res.status === 403) {
    saToast('Superadmin access required.', 'error');
    setTimeout(() => (window.location.href = '/admin-login/'), 1200);
    throw new Error('Forbidden');
  }

  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }

  if (!res.ok) {
    const message = (data && data.error) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

const saGet = (path) => saFetchJSON(path);
const saPost = (path, body) => saFetchJSON(path, { method: 'POST', body: JSON.stringify(body || {}) });
const saPut = (path, body) => saFetchJSON(path, { method: 'PUT', body: JSON.stringify(body || {}) });
const saDelete = (path) => saFetchJSON(path, { method: 'DELETE' });

/* ---------------------------------------------------------------- */
/* SIDEBAR                                                           */
/* ---------------------------------------------------------------- */
const SA_NAV = [
  { key: 'dashboard', label: 'Dashboard', href: '/superadmin/', icon: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z' },
  { key: 'companies', label: 'Companies', href: '/superadmin/companies/', icon: 'M4 2h16v20H4z|M9 2v20|M15 2v20|M4 8h16|M4 14h16' },
  { key: 'employees', label: 'Employee Profiles', href: '/superadmin/employees/', icon: 'people' },
  { key: 'work-entries', label: 'Work Entries', href: '/superadmin/work-entries/', icon: 'M9 11l3 3L22 4|M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11' },
  { key: 'tasks', label: 'Assigned Tasks', href: '/superadmin/tasks/', icon: 'M9 11l3 3L22 4|M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11' },
  { key: 'invites', label: 'Admin Invites', href: '/superadmin/invites/', icon: 'M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z|M22 6l-10 7L2 6' },
  { key: 'users', label: 'User Accounts', href: '/superadmin/users/', icon: 'circle-user' },
];

function saIconSvg(spec) {
  if (spec === 'people') {
    return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>';
  }
  if (spec === 'circle-user') {
    return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="10" r="3"></circle><path d="M6.5 19a6 6 0 0 1 11 0"></path></svg>';
  }
  const paths = spec.split('|').map((d) => `<path d="${d}"></path>`).join('');
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${paths}</svg>`;
}

function saRenderSidebar(activeKey) {
  const mount = document.getElementById('sa-sidebar-mount');
  if (!mount) return;

  const navHtml = SA_NAV.map((item) => `
    <a href="${item.href}" class="sa-nav-link ${item.key === activeKey ? 'active' : ''}">
      ${saIconSvg(item.icon)}
      <span>${item.label}</span>
    </a>
  `).join('');

  mount.innerHTML = `
    <button class="sa-mobile-toggle" id="saMobileToggle">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line>
      </svg>
    </button>
    <aside class="sa-sidebar" id="saSidebar">
      <div class="sa-sidebar-header">
        <div class="sa-logo-box">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
          </svg>
        </div>
        <div>
          <div class="sa-sidebar-title">Superadmin</div>
          <div class="sa-sidebar-sub">Full DB Access</div>
        </div>
      </div>
      <nav class="sa-nav">
        <div class="sa-nav-section-label">Overview</div>
        ${navHtml}
      </nav>
      <div class="sa-sidebar-footer">
        <button class="sa-logout-btn" onclick="saLogout()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          Logout
        </button>
      </div>
    </aside>
  `;

  const toggle = document.getElementById('saMobileToggle');
  const sidebar = document.getElementById('saSidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('sa-open'));
  }
}

/* ---------------------------------------------------------------- */
/* TOAST                                                              */
/* ---------------------------------------------------------------- */
function saToast(message, type = 'info') {
  let container = document.getElementById('saToastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'saToastContainer';
    container.className = 'sa-toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `sa-toast sa-toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

/* ---------------------------------------------------------------- */
/* MODAL HELPERS                                                      */
/* ---------------------------------------------------------------- */
function saOpenModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'flex';
}
function saCloseModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

/* ---------------------------------------------------------------- */
/* FORMAT HELPERS                                                     */
/* ---------------------------------------------------------------- */
function saEscape(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function saDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function saDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function saInitials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || name[0].toUpperCase();
}

function saDebounce(fn, wait) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

function saStatusBadgeClass(status) {
  const s = (status || '').toLowerCase();
  if (['approved', 'completed', 'active', 'accepted'].includes(s)) return 'sa-badge-green';
  if (['pending', 'not_started', 'assigned'].includes(s)) return 'sa-badge-amber';
  if (['rejected', 'inactive'].includes(s)) return 'sa-badge-red';
  if (['in_progress'].includes(s)) return 'sa-badge-blue';
  if (['reassigned'].includes(s)) return 'sa-badge-violet';
  return 'sa-badge-slate';
}

function saStatusLabel(status) {
  if (!status) return '—';
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ---------------------------------------------------------------- */
/* GENERIC ENTITY EDIT / DELETE ENGINE                                */
/* Drives the shared #saEditModal (see _partials/edit_modal.html)    */
/* ---------------------------------------------------------------- */
const SA_ENTITY_CONFIGS = {
  company: {
    title: 'Company',
    url: (id) => `/api/superadmin/companies/${id}/`,
    fields: [
      { key: 'name', label: 'Company Name', type: 'text', required: true },
      { key: 'is_active', label: 'Active', type: 'checkbox' },
    ],
  },
  employee: {
    title: 'Employee Profile',
    url: (id) => `/api/superadmin/employees/${id}/`,
    fields: [
      { key: 'employee_id', label: 'Employee ID', type: 'text' },
      { key: 'department', label: 'Department', type: 'text' },
      { key: 'designation', label: 'Designation', type: 'text' },
      { key: 'phone', label: 'Phone', type: 'text' },
      { key: 'joining_date', label: 'Joining Date', type: 'date' },
      { key: 'is_admin', label: 'Is Admin', type: 'checkbox' },
      { key: 'is_owner', label: 'Is Owner', type: 'checkbox' },
    ],
    note: (r) => `${saEscape(r.full_name)} · ${saEscape(r.email)} · ${saEscape(r.company_name)}`,
  },
  workentry: {
    title: 'Work Entry',
    url: (id) => `/api/superadmin/work-entries/${id}/`,
    fields: [
      { key: 'project_name', label: 'Project Name', type: 'text' },
      { key: 'task_done', label: 'Task Done', type: 'textarea' },
      { key: 'date', label: 'Date', type: 'date' },
      { key: 'planned_minutes', label: 'Planned Minutes', type: 'number' },
      { key: 'actual_minutes', label: 'Actual Minutes', type: 'number' },
      { key: 'status', label: 'Status', type: 'select', options: ['not_started', 'in_progress', 'completed', 'reassigned'] },
      { key: 'review_status', label: 'Review Status', type: 'select', options: ['pending', 'approved', 'rejected'] },
      { key: 'remark', label: 'Remark', type: 'textarea' },
      { key: 'admin_comment', label: 'Admin Comment', type: 'textarea' },
    ],
    note: (r) => `${saEscape(r.employee_name)} · ${saEscape(r.company_name)}`,
  },
  task: {
    title: 'Assigned Task',
    url: (id) => `/api/superadmin/tasks/${id}/`,
    fields: [
      { key: 'project_name', label: 'Project Name', type: 'text' },
      { key: 'task_description', label: 'Task Description', type: 'textarea' },
      { key: 'deadline', label: 'Deadline', type: 'date' },
      { key: 'planned_minutes', label: 'Planned Minutes', type: 'number' },
      { key: 'actual_minutes', label: 'Actual Minutes', type: 'number' },
      { key: 'status', label: 'Status', type: 'select', options: ['assigned', 'in_progress', 'completed'] },
    ],
    note: (r) => `Assigned to ${saEscape(r.assigned_to)} · ${saEscape(r.company_name)}`,
  },
  invite: {
    title: 'Admin Invite',
    url: (id) => `/api/superadmin/invites/${id}/`,
    fields: [
      { key: 'accepted', label: 'Accepted', type: 'checkbox' },
    ],
    note: (r) => `${saEscape(r.email)} → ${saEscape(r.company_name)} · invited by ${saEscape(r.invited_by)} · expires ${saDate(r.expires_at)}`,
    extraButton: { label: 'Resend Invite (reset 48h expiry)', payload: { resend: true } },
  },
  user: {
    title: 'User Account',
    url: (id) => `/api/superadmin/users/${id}/`,
    fields: [
      { key: 'first_name', label: 'First Name', type: 'text' },
      { key: 'last_name', label: 'Last Name', type: 'text' },
      { key: 'email', label: 'Email', type: 'text' },
      { key: 'is_active', label: 'Active', type: 'checkbox' },
      { key: 'is_superuser', label: 'Superuser', type: 'checkbox' },
      { key: 'new_password', label: 'Set New Password (leave blank to keep current)', type: 'password' },
    ],
    note: (r) => `${saEscape(r.username)} · ${r.company_name && r.company_name !== '—' ? saEscape(r.company_name) : 'No company'}`,
  },
};

let _saCurrent = { type: null, id: null, onSaved: null, onDeleted: null };

function _saFieldHtml(field, value) {
  const val = value === null || value === undefined ? '' : value;
  if (field.type === 'checkbox') {
    return `
      <div class="sa-form-row sa-checkbox-row">
        <input type="checkbox" id="sf_${field.key}" ${val ? 'checked' : ''}>
        <label for="sf_${field.key}">${field.label}</label>
      </div>`;
  }
  if (field.type === 'textarea') {
    return `
      <div class="sa-form-row">
        <label>${field.label}</label>
        <textarea class="sa-textarea" id="sf_${field.key}">${saEscape(val)}</textarea>
      </div>`;
  }
  if (field.type === 'select') {
    const opts = field.options.map((o) => `<option value="${o}" ${o === val ? 'selected' : ''}>${saStatusLabel(o)}</option>`).join('');
    return `
      <div class="sa-form-row">
        <label>${field.label}</label>
        <select class="sa-select" id="sf_${field.key}">${opts}</select>
      </div>`;
  }
  const inputType = field.type === 'date' ? 'date' : field.type === 'number' ? 'number' : field.type === 'password' ? 'password' : 'text';
  const dateVal = field.type === 'date' && val ? String(val).slice(0, 10) : val;
  return `
    <div class="sa-form-row">
      <label>${field.label}</label>
      <input type="${inputType}" class="sa-input" id="sf_${field.key}" value="${saEscape(dateVal)}" ${field.required ? 'required' : ''}>
    </div>`;
}

async function saOpenEditor(type, id, { onSaved, onDeleted, allowDelete = true } = {}) {
  const config = SA_ENTITY_CONFIGS[type];
  if (!config) return;
  _saCurrent = { type, id, onSaved, onDeleted };

  document.getElementById('saEditModalTitle').textContent = config.title;
  document.getElementById('saEditModalSub').textContent = 'Loading…';
  document.getElementById('saEditFields').innerHTML = '';
  document.getElementById('saEditNote').textContent = '';
  document.getElementById('saEditError').classList.remove('show');
  document.getElementById('saEditDeleteBtn').style.display = allowDelete ? 'inline-flex' : 'none';
  saOpenModal('saEditModal');

  try {
    const record = await saGet(config.url(id));
    document.getElementById('saEditModalSub').textContent = `Editing #${id}`;
    if (config.note) document.getElementById('saEditNote').innerHTML = config.note(record);
    document.getElementById('saEditFields').innerHTML = config.fields.map((f) => _saFieldHtml(f, record[f.key])).join('');

    if (config.extraButton) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'sa-btn sa-btn-outline sa-btn-sm';
      btn.style.marginTop = '0.5rem';
      btn.textContent = config.extraButton.label;
      btn.onclick = async () => {
        try {
          await saPut(config.url(id), config.extraButton.payload);
          saToast('Done.', 'success');
          saCloseModal('saEditModal');
          if (onSaved) onSaved();
        } catch (e) {
          saToast(e.message, 'error');
        }
      };
      document.getElementById('saEditFields').appendChild(btn);
    }
  } catch (e) {
    document.getElementById('saEditError').textContent = e.message;
    document.getElementById('saEditError').classList.add('show');
  }
}

async function saConfirmDeleteCurrent() {
  const { type, id, onDeleted } = _saCurrent;
  const config = SA_ENTITY_CONFIGS[type];
  if (!config) return;
  if (!confirm(`Delete this ${config.title.toLowerCase()}? This cannot be undone.`)) return;
  try {
    await saDelete(config.url(id));
    saToast(`${config.title} deleted.`, 'success');
    saCloseModal('saEditModal');
    if (onDeleted) onDeleted();
  } catch (e) {
    saToast(e.message, 'error');
  }
}

document.addEventListener('submit', async (e) => {
  if (e.target.id !== 'saEditForm') return;
  e.preventDefault();
  const { type, id, onSaved } = _saCurrent;
  const config = SA_ENTITY_CONFIGS[type];
  if (!config) return;

  const errBox = document.getElementById('saEditError');
  errBox.classList.remove('show');

  const payload = {};
  config.fields.forEach((f) => {
    const el = document.getElementById(`sf_${f.key}`);
    if (!el) return;
    if (f.type === 'checkbox') payload[f.key] = el.checked;
    else if (f.type === 'password') { if (el.value) payload[f.key] = el.value; }
    else payload[f.key] = el.value;
  });

  try {
    await saPut(config.url(id), payload);
    saToast(`${config.title} saved.`, 'success');
    saCloseModal('saEditModal');
    if (onSaved) onSaved();
  } catch (err) {
    errBox.textContent = err.message;
    errBox.classList.add('show');
  }
});

document.addEventListener('DOMContentLoaded', () => {
  if (!saRequireAuth()) return;
});