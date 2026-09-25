const AUTH_TOKEN_KEY = 'price_ai_token';

function setAuthToken(token) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

function clearAuthToken() {
  setAuthToken('');
}

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || '';
}

function isAuthenticated() {
  return Boolean(getAuthToken());
}

function handleAuthFailure(message = 'Session expire ho gaya hai, please dubara login karein.') {
  if (window.__authRedirectInProgress) {
    return;
  }

  window.__authRedirectInProgress = true;
  clearAuthToken();
  alert(message);

  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

async function loginUser(email, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ email, password })
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Login failed');
  }

  setAuthToken(data.token);
  return data;
}

function logoutUser() {
  setAuthToken('');
  window.location.href = '/login';
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getAuthToken()}`
  };
}

function updateUIForAuth() {
  const token = getAuthToken();
  const loginSection = document.getElementById('loginForm');
  const dashboardSection = document.getElementById('dashboard');
  if (token) {
    if (loginSection) loginSection.classList.add('hidden');
    if (dashboardSection) dashboardSection.classList.remove('hidden');
  } else {
    if (loginSection) loginSection.classList.remove('hidden');
    if (dashboardSection) dashboardSection.classList.add('hidden');
  }
}

window.addEventListener('DOMContentLoaded', updateUIForAuth);
