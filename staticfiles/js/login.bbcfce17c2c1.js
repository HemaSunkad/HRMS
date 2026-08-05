/**
 * Login Page Logic
 * Handles role selection, authentication, and form management
 */

// State
let currentRole = null; // 'employee' | 'admin' | null
let currentAuthMode = 'signin'; // 'signin' | 'signup'
let isLoading = false;
let errorMessage = '';

// Form data
let email = '';
let password = '';
let fullName = '';
let companyName = '';
let showPassword = false;

// Validation
function validateEmail(emailValue) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(emailValue);
}

function validatePassword(passwordValue) {
  const checks = {
    length: passwordValue.length >= 8,
    uppercase: /[A-Z]/.test(passwordValue),
    lowercase: /[a-z]/.test(passwordValue),
    number: /[0-9]/.test(passwordValue),
    special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]~`]/.test(passwordValue)
  };
  return {
    checks,
    isValid: Object.values(checks).every(Boolean)
  };
}

// UI Rendering
function render() {
  const app = document.getElementById('app');

  if (!currentRole) {
    // Role Selection Screen
    app.innerHTML = `
      <div class="max-w-md relative z-10">
        <!-- Header -->
        <div class="text-center mb-10">
          <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-violet-200 shadow-md mb-6">
            <svg class="animate-bounce" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"></path>
            </svg>
            <span style="background: linear-gradient(135deg, #8b5cf6, #ec4899, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">
              Work Management
            </span>
          </div>

          <h1 class="text-5xl font-black leading-tight text-slate-900 mb-2">
            <span style="background: linear-gradient(135deg, #8b5cf6, #ec4899, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Track work.
            </span><br>
            Grow together.
          </h1>

          <p class="text-slate-600 text-sm mt-3">
            Your team's work, all in one place — secure, private, and built for real productivity.
          </p>
        </div>

        <!-- Role Cards -->
        <div class="space-y-4">
          <button onclick="selectRole('employee')" class="role-card animate-slideInUp stagger-1">
            <div class="flex items-center gap-4">
              <div class="role-icon role-icon-employee">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </div>
              <div class="flex-1 text-left">
                <h3 class="font-bold text-slate-900 text-lg">Employee</h3>
                <p class="text-sm text-slate-600">Sign in to log your daily work and stay on top of tasks</p>
              </div>
              <div class="w-8 h-8 rounded-full border border-slate-200 flex items-center justify-center">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2">
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                  <polyline points="12 5 19 12 12 19"></polyline>
                </svg>
              </div>
            </div>
          </button>

          <button onclick="selectRole('admin')" class="role-card animate-slideInUp stagger-2">
            <div class="flex items-center gap-4">
              <div class="role-icon role-icon-admin">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
              </div>
              <div class="flex-1 text-left">
                <h3 class="font-bold text-slate-900 text-lg">Admin / Manager</h3>
                <p class="text-sm text-slate-600">Sign in or create your company account to manage your team</p>
              </div>
              <div class="w-8 h-8 rounded-full border border-slate-200 flex items-center justify-center">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2">
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                  <polyline points="12 5 19 12 12 19"></polyline>
                </svg>
              </div>
            </div>
          </button>
        </div>

        <div class="footer">
          © 2025 WorkTrack. All rights reserved.
        </div>
      </div>
    `;
  } else if (currentRole === 'employee') {
    // Employee Login Screen
    app.innerHTML = `
      <div class="max-w-md relative z-10">
        <button onclick="goBack()" class="back-button animate-slideInLeft">
          ← Back to role selection
        </button>

        <div class="flex items-center gap-2 mb-6">
          <div class="role-badge role-badge-employee">
            <span class="role-badge-dot role-badge-dot-employee"></span>
            Employee Sign In
          </div>
        </div>

        <div class="form-container animate-scaleIn">
          <div class="mb-6">
            <h2 class="text-2xl font-black text-slate-900">👋 Welcome back</h2>
            <p class="text-slate-500 text-sm mt-1">Sign in with credentials provided by your admin</p>
          </div>

          <div id="errorMessage" class="error-message ${errorMessage ? 'show' : ''}">
            ⚠️ ${errorMessage}
          </div>

          <form onsubmit="handleEmployeeLogin(event)">
            <div class="mb-4">
              <label class="block text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">Email Address</label>
              <div class="relative">
                <svg class="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                  <polyline points="22,6 12,13 2,6"></polyline>
                </svg>
                <input
                  type="email"
                  class="form-input"
                  placeholder="employee@gmail.com"
                  value="${email}"
                  oninput="email = this.value"
                  required
                >
              </div>
            </div>

            <div class="mb-4">
              <label class="block text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">Password</label>
              <div class="relative">
                <svg class="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <input
                  type="${showPassword ? 'text' : 'password'}"
                  class="form-input"
                  placeholder="••••••••"
                  value="${password}"
                  oninput="password = this.value"
                  required
                >
                <button type="button" onclick="togglePassword()" class="password-toggle">
                  ${showPassword ?
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-5.06 5.94M1 1l22 22"></path></svg>' :
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>'
                  }
                </button>
              </div>
            </div>

            <button type="submit" class="submit-btn submit-btn-employee" ${isLoading ? 'disabled' : ''} style="margin-top: 0.5rem;">
              ${isLoading ?
                '<span class="flex items-center justify-center gap-2"><div class="spinner-sm"></div>Signing in...</span>' :
                '<span>Sign In <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg></span>'
              }
            </button>
          </form>

          <div class="mt-6 p-4 bg-cyan-50 rounded-xl border border-cyan-100">
            <p class="text-xs text-slate-500 text-center">
              🔐 Your login credentials are provided by your Admin / Manager.<br>
              Contact your admin if you don't have access.
            </p>
          </div>
        </div>
      </div>
    `;
  } else {
    // Admin Login/Signup Screen
    const passwordValidation = validatePassword(password);
    const isCompanyNameValid = companyName.trim().length >= 2;

    app.innerHTML = `
      <div class="max-w-md relative z-10">
        <button onclick="goBack()" class="back-button animate-slideInLeft">
          ← Back to role selection
        </button>

        <div class="flex items-center gap-2 mb-6">
          <div class="role-badge role-badge-admin">
            <span class="role-badge-dot role-badge-dot-admin"></span>
            Admin Access
          </div>
        </div>

        <div class="form-container animate-scaleIn">
          <!-- Tabs -->
          <div class="auth-tabs">
            <button
              onclick="setAuthMode('signin')"
              class="auth-tab ${currentAuthMode === 'signin' ? 'auth-tab-active' : ''}"
            >
              Sign In
            </button>
            <button
              onclick="setAuthMode('signup')"
              class="auth-tab ${currentAuthMode === 'signup' ? 'auth-tab-active' : ''}"
            >
              New Company
            </button>
          </div>

          <div class="mb-6">
            <h2 class="text-2xl font-black text-slate-900">
              ${currentAuthMode === 'signin' ? '👋 Admin Sign In' : '🏢 Create Your Workspace'}
            </h2>
            <p class="text-slate-500 text-sm mt-1">
              ${currentAuthMode === 'signin' ?
                'Enter your admin credentials' :
                'You become the Owner Admin — invite teammates later by email'
              }
            </p>
          </div>

          <div id="errorMessage" class="error-message ${errorMessage ? 'show' : ''}">
            ⚠️ ${errorMessage}
          </div>

          <form onsubmit="${currentAuthMode === 'signin' ? 'handleAdminLogin(event)' : 'handleAdminSignUp(event)'}">
            ${currentAuthMode === 'signup' ? `
              <div class="space-y-4 animate-fadeIn" style="margin-bottom: 1rem;">
                <div>
                  <label class="block text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">Full Name</label>
                  <div class="relative">
                    <svg class="input-icon input-icon-admin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                      <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                    <input
                      type="text"
                      class="form-input"
                      placeholder="Your Name"
                      value="${fullName}"
                      oninput="fullName = this.value"
                      required
                    >
                  </div>
                </div>

                <div>
                  <label class="block text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">
                    Company Name <span class="text-violet-500">*</span>
                  </label>
                  <div class="relative">
                    <svg class="input-icon input-icon-admin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>
                      <line x1="9" y1="22" x2="9" y2="22.01"></line>
                      <line x1="15" y1="22" x2="15" y2="22.01"></line>
                      <line x1="9" y1="2" x2="9" y2="22"></line>
                      <line x1="15" y1="2" x2="15" y2="22"></line>
                    </svg>
                    <input
                      type="text"
                      class="form-input"
                      placeholder="e.g., HAEGL Technologies"
                      value="${companyName}"
                      oninput="companyName = this.value"
                      required
                    >
                  </div>
                  <p class="text-xs text-slate-400 mt-1">
                    This creates a brand-new, private workspace just for your company. No codes needed — you can invite co-admins securely by email once you're in.
                  </p>
                </div>
              </div>
            ` : ''}

            <div class="mb-4">
              <label class="block text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">Email Address</label>
              <div class="relative">
                <svg class="input-icon input-icon-admin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                  <polyline points="22,6 12,13 2,6"></polyline>
                </svg>
                <input
                  type="email"
                  class="form-input"
                  placeholder="admin@gmail.com"
                  value="${email}"
                  oninput="email = this.value"
                  required
                >
              </div>
            </div>

            <div class="mb-4">
              <label class="block text-xs font-bold text-slate-500 mb-1.5 uppercase tracking-wider">Password</label>
              <div class="relative">
                <svg class="input-icon input-icon-admin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <input
                  type="${showPassword ? 'text' : 'password'}"
                  class="form-input"
                  placeholder="••••••••"
                  value="${password}"
                  oninput="password = this.value"
                  required
                >
                <button type="button" onclick="togglePassword()" class="password-toggle">
                  ${showPassword ?
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-5.06 5.94M1 1l22 22"></path></svg>' :
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>'
                  }
                </button>
              </div>
            </div>

            ${currentAuthMode === 'signup' && password.length > 0 ? `
              <div class="password-validation animate-fadeIn">
                <span class="${passwordValidation.checks.length ? 'password-check met' : 'password-check'}">
                  ${passwordValidation.checks.length ? '✓' : '○'} 8+ characters
                </span>
                <span class="${passwordValidation.checks.uppercase ? 'password-check met' : 'password-check'}">
                  ${passwordValidation.checks.uppercase ? '✓' : '○'} Uppercase letter
                </span>
                <span class="${passwordValidation.checks.lowercase ? 'password-check met' : 'password-check'}">
                  ${passwordValidation.checks.lowercase ? '✓' : '○'} Lowercase letter
                </span>
                <span class="${passwordValidation.checks.number ? 'password-check met' : 'password-check'}">
                  ${passwordValidation.checks.number ? '✓' : '○'} Number
                </span>
                <span class="${passwordValidation.checks.special ? 'password-check met' : 'password-check'}">
                  ${passwordValidation.checks.special ? '✓' : '○'} Special character
                </span>
              </div>
            ` : ''}

            <button
              type="submit"
              class="submit-btn submit-btn-admin"
              ${isLoading ? 'disabled' : ''}
              ${currentAuthMode === 'signup' && (!passwordValidation.isValid || !isCompanyNameValid) ? 'disabled' : ''}
              style="margin-top: 0.5rem;"
            >
              ${isLoading ?
                '<span class="flex items-center justify-center gap-2"><div class="spinner-sm"></div>' + (currentAuthMode === 'signin' ? 'Signing in...' : 'Creating workspace...') + '</span>' :
                (currentAuthMode === 'signin' ?
                  '<span>Sign In <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg></span>' :
                  '<span>Create Company Workspace <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="9" y1="22" x2="9" y2="22.01"></line><line x1="15" y1="22" x2="15" y2="22.01"></line><line x1="9" y1="2" x2="9" y2="22"></line><line x1="15" y1="2" x2="15" y2="22"></line></svg></span>'
                )
              }
            </button>
          </form>

          <!-- Google Sign-In -->
          <div style="margin-top: 1.5rem;">
            <div class="flex items-center gap-3 mb-4">
              <div class="flex-1 h-px bg-slate-200"></div>
              <span class="text-xs text-slate-400 font-medium">OR</span>
              <div class="flex-1 h-px bg-slate-200"></div>
            </div>

            <div class="relative">
              <div id="googleButton" class="google-button-container flex justify-center"></div>
              ${currentAuthMode === 'signup' && !isCompanyNameValid ? `
                <div class="google-button-overlay">
                  <span class="text-xs text-slate-500 flex items-center gap-1.5">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2">
                      <rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>
                      <line x1="9" y1="22" x2="9" y2="22.01"></line>
                      <line x1="15" y1="22" x2="15" y2="22.01"></line>
                    </svg>
                    Enter company name above to continue
                  </span>
                </div>
              ` : ''}
            </div>

            <p class="text-xs text-slate-400 text-center mt-2">
              Google Sign-In is reserved for Admin accounts only.
            </p>
          </div>

          <!-- Invite-only note -->
          <div class="mt-6 p-4 bg-violet-50 rounded-xl border border-violet-100">
            <p class="text-xs text-slate-500 text-center">
              🔒 Joining an existing company as a co-admin? Ask your Owner Admin to send you a private email invite — there's no code to enter here.
            </p>
          </div>
        </div>
      </div>
    `;

    // Initialize Google Sign-In if admin role
    if (currentRole === 'admin' && window.google) {
      initializeGoogleSignIn();
    }
  }
}

// Event Handlers
function selectRole(role) {
  currentRole = role;
  currentAuthMode = 'signin';
  errorMessage = '';
  render();
}

function goBack() {
  currentRole = null;
  currentAuthMode = 'signin';
  errorMessage = '';
  render();
}

function setAuthMode(mode) {
  currentAuthMode = mode;
  errorMessage = '';
  render();
}

function togglePassword() {
  showPassword = !showPassword;
  render();
}

async function handleEmployeeLogin(event) {
  event.preventDefault();
  isLoading = true;
  errorMessage = '';
  render();

  try {
    const data = await loginAPI(email, password);

    if (data.error) {
      errorMessage = data.error;
      isLoading = false;
      render();
      return;
    }

    // Store auth data (FIX: pass company_name through so it isn't lost)
    setAuthData(data.token, data.user, data.is_admin, data.company_name);

    // Redirect (FIX: real Django routes have no .html and end with /)
    if (data.is_superuser) {
      window.location.href = '/superadmin/';
    } else {
      window.location.href = '/employee/worklog/';
    }
  } catch (error) {
    errorMessage = 'Connection failed. Make sure the server is running.';
    isLoading = false;
    render();
  }
}

async function handleAdminLogin(event) {
  event.preventDefault();
  isLoading = true;
  errorMessage = '';
  render();

  try {
    const data = await loginAPI(email, password);

    if (data.error) {
      errorMessage = data.error;
      isLoading = false;
      render();
      return;
    }

    // Store auth data (FIX: pass company_name through so it isn't lost)
    setAuthData(data.token, data.user, data.is_admin, data.company_name);

    // Redirect based on user type (FIX: real Django routes)
    if (data.is_superuser) {
      window.location.href = '/superadmin/';
    } else if (!data.is_admin) {
      errorMessage = 'You do not have admin access.';
      isLoading = false;
      render();
    } else {
      window.location.href = '/admin/worklog/';
    }
  } catch (error) {
    errorMessage = 'Connection failed. Make sure the server is running.';
    isLoading = false;
    render();
  }
}

async function handleAdminSignUp(event) {
  event.preventDefault();
  isLoading = true;
  errorMessage = '';
  render();

  try {
    const data = await signupCreateCompanyAPI(email, password, fullName, companyName);

    if (data.error) {
      errorMessage = data.error;
      isLoading = false;
      render();
      return;
    }

    // Store auth data (FIX: pass company_name through so it isn't lost)
    setAuthData(data.token, data.user, data.is_admin, data.company_name);
    const finalCompanyName = data.company_name || companyName;
    setCompanyName(finalCompanyName);

    // Show welcome modal
    showWelcomeModal(finalCompanyName);
  } catch (error) {
    errorMessage = 'Connection failed.';
    isLoading = false;
    render();
  }
}

// Admin signup API
async function signupCreateCompanyAPI(email, password, fullName, companyName) {
  const res = await fetch('/api/admin/signup-company/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName, company_name: companyName }),
  });
  return await res.json();
}

// Welcome Modal
function showWelcomeModal(companyName) {
  document.getElementById('welcomeCompanyName').textContent = companyName;
  document.getElementById('welcomeModal').classList.add('show');
}

function handleWelcomeContinue() {
  document.getElementById('welcomeModal').classList.remove('show');
  window.location.href = '/admin/worklog/';
}

// Google Sign-In
function handleGoogleCredentialResponse(response) {
  isLoading = true;
  errorMessage = '';
  render();

  googleAdminLoginAPI(response.credential, currentAuthMode === 'signup' ? companyName : '')
    .then(data => {
      if (data.error) {
        errorMessage = data.error;
        isLoading = false;
        render();
        return;
      }

      // Store auth data (FIX: pass company_name through so it isn't lost)
      setAuthData(data.token, data.user, data.is_admin, data.company_name);

      const company = data.company_name || data.user?.company_name || data.user?.company || '';
      if (company) {
        setCompanyName(company);
      }

      if (currentAuthMode === 'signup' && data.company_name) {
        showWelcomeModal(data.company_name);
        isLoading = false;
      } else {
        window.location.href = '/admin/worklog/';
      }
    })
    .catch(() => {
      errorMessage = 'Connection failed.';
      isLoading = false;
      render();
    });
}

// Google admin login API
async function googleAdminLoginAPI(credential, companyName) {
  const res = await fetch('/api/admin/google-login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential, company_name: companyName }),
  });
  return await res.json();
}

function initializeGoogleSignIn() {
  if (!window.google) return;

  // Check if GOOGLE_CLIENT_ID is available (you'd set this in environment or config)
  const clientId = process?.env?.NEXT_PUBLIC_GOOGLE_CLIENT_ID || window.GOOGLE_CLIENT_ID;

  if (!clientId) {
    console.warn('Google Client ID not configured');
    return;
  }

  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleCredentialResponse,
  });

  const container = document.getElementById('googleButton');
  if (container) {
    container.innerHTML = '';
    window.google.accounts.id.renderButton(container, {
      theme: 'outline',
      size: 'large',
      width: 360,
      text: currentAuthMode === 'signup' ? 'signup_with' : 'signin_with',
    });
  }
}

// Watch for Google script load
let googleCheckInterval;
function waitForGoogle() {
  if (window.google) {
    initializeGoogleSignIn();
    clearInterval(googleCheckInterval);
  }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  render();

  // Check if we need to wait for Google script
  if (currentRole === 'admin') {
    googleCheckInterval = setInterval(waitForGoogle, 200);
    setTimeout(() => clearInterval(googleCheckInterval), 5000);
  }
});

// Also watch for Google load if it loads after DOM
window.addEventListener('load', () => {
  if (window.google && currentRole === 'admin') {
    initializeGoogleSignIn();
  }
});