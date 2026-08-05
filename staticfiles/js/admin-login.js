/**
 * Admin Login Page JavaScript
 * Handles authentication, form validation, and Google Sign-In
 */

console.log('Admin login script loaded successfully!');

const API_BASE = '';

// State
let authMode = 'signin';
let showPassword = false;
let googleInitialized = false;

window.authMode = authMode;

let signinTab, signupTab, signupFields, authTitle, authSubtitle, submitBtn;
let errorMessage, errorText, passwordInput, companyNameInput, passwordStrength;

function switchTab(mode) {
  authMode = mode;
  window.authMode = authMode;

  if (!signinTab || !signupTab || !authTitle || !authSubtitle || !submitBtn) {
    return;
  }

  if (mode === 'signin') {
    signinTab.classList.add('active');
    signupTab.classList.remove('active');
    signupFields.style.display = 'none';
    authTitle.textContent = '👋 Admin Sign In';
    authSubtitle.textContent = 'Enter your admin credentials';
    submitBtn.querySelector('.button-text').textContent = 'Sign In';
  } else {
    signupTab.classList.add('active');
    signinTab.classList.remove('active');
    signupFields.style.display = 'block';
    authTitle.textContent = '🏢 Create Your Workspace';
    authSubtitle.textContent = 'You become the Owner Admin — invite teammates later by email';
    submitBtn.querySelector('.button-text').textContent = 'Create Company Workspace';
  }

  hideError();
  updateGoogleOverlay();

  if (window.google && window.google.accounts && googleInitialized) {
    const buttonElement = document.getElementById('googleSignInButton');
    if (buttonElement) {
      buttonElement.innerHTML = '';
      google.accounts.id.renderButton(buttonElement, {
        theme: 'outline',
        size: 'large',
        width: 360,
        text: authMode === 'signup' ? 'signup_with' : 'signin_with',
        shape: 'rectangular',
        logo_alignment: 'left'
      });
    }
  }
}

function togglePassword() {
  if (!passwordInput) return;
  showPassword = !showPassword;
  passwordInput.type = showPassword ? 'text' : 'password';
  const eyeIcon = document.getElementById('eyeIcon');
  if (eyeIcon) {
    eyeIcon.innerHTML = showPassword
      ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a22.92 22.92 0 0 1 5.94-5.94M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><line x1="9.9" y1="4.9" x2="17.04" y2="12.03"></line><line x1="14.94" y1="14.94" x2="9.9" y2="9.9"></line>'
      : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
  }
}

function showError(message) {
  if (!errorText || !errorMessage) return;
  errorText.textContent = message;
  errorMessage.style.display = 'flex';
}

function hideError() {
  if (!errorMessage) return;
  errorMessage.style.display = 'none';
}

function checkPasswordStrength() {
  if (!passwordInput || !passwordStrength) return;
  const password = passwordInput.value;
  if (authMode !== 'signup' || !password) {
    passwordStrength.style.display = 'none';
    return;
  }
  passwordStrength.style.display = 'block';
  const checks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]~`]/.test(password)
  };
  Object.keys(checks).forEach(rule => {
    const element = document.querySelector(`[data-rule="${rule}"]`);
    if (element) {
      if (checks[rule]) {
        element.classList.add('met');
        element.textContent = '✓ ' + element.textContent.substring(2);
      } else {
        element.classList.remove('met');
        element.textContent = '○ ' + element.textContent.substring(2);
      }
    }
  });
  return Object.values(checks).every(Boolean);
}

function validateForm() {
  if (!passwordInput || !companyNameInput) return false;
  const email = document.getElementById('email').value;
  const password = passwordInput.value;
  const fullName = document.getElementById('fullName').value;
  const companyName = companyNameInput.value;

  if (!email || !password) {
    showError('Please fill in all required fields.');
    return false;
  }

  if (authMode === 'signup') {
    if (!fullName || !companyName) {
      showError('Please fill in all required fields.');
      return false;
    }
    if (companyName.trim().length < 2) {
      showError('Please enter your company name (at least 2 characters).');
      return false;
    }
    if (!checkPasswordStrength()) {
      showError('Password does not meet the required strength.');
      return false;
    }
  }
  return true;
}

async function handleSubmit(event) {
  event.preventDefault();
  if (!validateForm()) return;
  if (!passwordInput || !companyNameInput) return;

  const email = document.getElementById('email').value;
  const password = passwordInput.value;
  const fullName = document.getElementById('fullName').value;
  const companyName = companyNameInput.value;

  setLoading(true);
  hideError();

  try {
    let data;

    if (authMode === 'signin') {
      const response = await fetch(`${API_BASE}/api/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      let raw;
      try {
        raw = await response.text();
        data = raw ? JSON.parse(raw) : {};
      } catch (parseErr) {
        showError(`Server error (${response.status}). Check the Django console for the traceback.`);
        setLoading(false);
        return;
      }

      if (!response.ok || data.error) {
        showError(data.error || `Sign in failed (status ${response.status}).`);
        setLoading(false);
        return;
      }

      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user || {}));
      localStorage.setItem('is_admin', data.is_admin);

      if (data.company_name) {
        localStorage.setItem('company_name', data.company_name);
        window.dispatchEvent(new Event('company-name-updated'));
      }

      if (data.is_superuser) {
        window.location.href = '/superadmin/';
      } else if (!data.is_admin) {
        showError('Please use Admin Login.');
        setLoading(false);
        return;
      } else {
        window.location.href = '/admin/worklog/';
      }

    } else {
      const response = await fetch(`${API_BASE}/api/admin/signup-company/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
          company_name: companyName
        })
      });

      let raw;
      try {
        raw = await response.text();
        data = raw ? JSON.parse(raw) : {};
      } catch (parseErr) {
        showError(`Server error (status ${response.status}). Open the Django terminal to see the real error.`);
        setLoading(false);
        return;
      }

      if (!response.ok) {
        showError(data.error || `Signup failed (status ${response.status}). Check the Network tab response body.`);
        setLoading(false);
        return;
      }

      if (data.error) {
        showError(data.error);
        setLoading(false);
        return;
      }

      if (!data.token) {
        showError('Signup succeeded but the server did not return a login token. Check the backend response shape.');
        setLoading(false);
        return;
      }

      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user || {}));
      localStorage.setItem('is_admin', 'true');

      const finalCompanyName = data.company_name || companyName;
      localStorage.setItem('company_name', finalCompanyName);
      window.dispatchEvent(new Event('company-name-updated'));

      showWelcomeModal(finalCompanyName);
    }
  } catch (error) {
    showError('Connection failed. Make sure the server is running.');
  }

  setLoading(false);
}

function setLoading(loading) {
  if (!submitBtn) return;
  submitBtn.disabled = loading;
  const buttonText = submitBtn.querySelector('.button-text');
  if (loading) {
    const text = authMode === 'signin' ? 'Signing in...' : 'Creating workspace...';
    if (buttonText) buttonText.innerHTML = `<span class="spinner"></span> ${text}`;
  } else {
    if (buttonText) buttonText.textContent = authMode === 'signin' ? 'Sign In' : 'Create Company Workspace';
  }
}

function showWelcomeModal(companyName) {
  const nameEl = document.getElementById('welcomeCompanyName');
  const modalEl = document.getElementById('welcomeModal');
  if (!nameEl || !modalEl) {
    window.location.href = '/admin/worklog/';
    return;
  }
  nameEl.textContent = companyName;
  modalEl.style.display = 'flex';
}

function continueToDashboard() {
  document.getElementById('welcomeModal').style.display = 'none';
  window.location.href = '/admin/worklog/';
}

function goBack() {
  window.location.href = '/';
}

function updateGoogleOverlay() {
  const overlay = document.getElementById('googleOverlay');
  if (!overlay) return;
  if (authMode === 'signup') {
    if (!companyNameInput) return;
    const companyName = companyNameInput.value.trim();
    overlay.style.display = companyName.length < 2 ? 'flex' : 'none';
  } else {
    overlay.style.display = 'none';
  }
}

function handleGoogleCredentialResponse(response) {
  if (!companyNameInput) {
    alert('Page not fully loaded. Please refresh and try again.');
    return;
  }

  const companyName = companyNameInput.value.trim();
  const credential = response.credential;
  if (!credential) {
    alert('Google Sign-In failed. No credential received.');
    return;
  }

  const requestBody = {
    credential: credential,
    company_name: authMode === 'signup' ? companyName : ''
  };

  fetch(`${API_BASE}/api/admin/google-login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody)
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      alert('Error: ' + data.error);
      return;
    }

    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    localStorage.setItem('is_admin', data.is_admin);

    const company = data.company_name || data.user?.company_name || data.user?.company || '';
    if (company) {
      localStorage.setItem('company_name', company);
      window.dispatchEvent(new Event('company-name-updated'));
    }

    if (authMode === 'signup' && data.company_name) {
      showWelcomeModal(data.company_name);
    } else {
      window.location.href = '/admin/worklog/';
    }
  })
  .catch(error => {
    alert('Connection failed. Make sure the server is running on port 8001.');
  });
}

function initGoogleSignIn() {
  if (window.google && window.google.accounts && !googleInitialized) {
    window.authMode = authMode;

    google.accounts.id.initialize({
      client_id: '576290068258-pik2uu8krp8t6gn2q0iesa80e3elv5rh.apps.googleusercontent.com',
      callback: handleGoogleCredentialResponse,
      auto_select: false,
      cancel_on_tap_outside: false
    });

    const buttonElement = document.getElementById('googleSignInButton');
    if (buttonElement) {
      buttonElement.innerHTML = '';
      google.accounts.id.renderButton(buttonElement, {
        theme: 'outline',
        size: 'large',
        width: 360,
        text: authMode === 'signup' ? 'signup_with' : 'signin_with',
        shape: 'rectangular',
        logo_alignment: 'left'
      });
    }
    googleInitialized = true;
  }
}

document.addEventListener('DOMContentLoaded', function() {
  signinTab = document.getElementById('signinTab');
  signupTab = document.getElementById('signupTab');
  signupFields = document.getElementById('signupFields');
  authTitle = document.getElementById('authTitle');
  authSubtitle = document.getElementById('authSubtitle');
  submitBtn = document.getElementById('submitBtn');
  errorMessage = document.getElementById('errorMessage');
  errorText = document.getElementById('errorText');
  passwordInput = document.getElementById('password');
  companyNameInput = document.getElementById('companyName');
  passwordStrength = document.getElementById('passwordStrength');

  if (passwordInput) {
    passwordInput.addEventListener('input', checkPasswordStrength);
  }
  if (companyNameInput) {
    companyNameInput.addEventListener('input', updateGoogleOverlay);
  }

  if (window.google && window.google.accounts) {
    initGoogleSignIn();
  } else {
    let attempts = 0;
    const maxAttempts = 25;
    const checkGoogle = setInterval(() => {
      attempts++;
      if (window.google && window.google.accounts) {
        initGoogleSignIn();
        clearInterval(checkGoogle);
      } else if (attempts >= maxAttempts) {
        clearInterval(checkGoogle);
      }
    }, 200);
  }
});

window.addEventListener('load', function() {
  if (window.google && window.google.accounts && !googleInitialized) {
    initGoogleSignIn();
  }
});