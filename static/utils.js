/**
 * Shared utilities for the RAG Chatbot frontend.
 * Handles authentication, API calls, and common UI functions.
 */

const API_BASE = '';

// ==================== Auth Helpers ====================

function getToken() {
    return localStorage.getItem('rag_token');
}

function getEmail() {
    return localStorage.getItem('rag_email');
}

function setAuth(token, email) {
    localStorage.setItem('rag_token', token);
    localStorage.setItem('rag_email', email);
}

function clearAuth() {
    localStorage.removeItem('rag_token');
    localStorage.removeItem('rag_email');
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = '/';
        return false;
    }
    return true;
}

function logout() {
    clearAuth();
    window.location.href = '/';
}

// ==================== API Helpers ====================

async function apiPost(endpoint, body = {}, includeToken = true) {
    const headers = { 'Content-Type': 'application/json' };
    let url = `${API_BASE}${endpoint}`;
    
    if (includeToken && getToken()) {
        url += (url.includes('?') ? '&' : '?') + `token=${getToken()}`;
    }

    const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
    });

    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.detail || 'Request failed');
    }
    
    return data;
}

async function apiGet(endpoint) {
    let url = `${API_BASE}${endpoint}`;
    
    if (getToken()) {
        url += (url.includes('?') ? '&' : '?') + `token=${getToken()}`;
    }

    const response = await fetch(url);
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.detail || 'Request failed');
    }
    
    return data;
}

async function apiUpload(endpoint, formData) {
    let url = `${API_BASE}${endpoint}`;
    
    if (getToken()) {
        url += (url.includes('?') ? '&' : '?') + `token=${getToken()}`;
    }

    const response = await fetch(url, {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
    }
    
    return data;
}

// ==================== Toast Notifications ====================

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastSlide 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ==================== Format Helpers ====================

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==================== Render Navbar ====================

function renderNavbar(activePage) {
    const email = getEmail();
    return `
    <nav class="navbar">
        <a href="/" class="navbar-brand">
            <div class="logo-icon">🏛️</div>
            <span>GovSchemes AI</span>
        </a>
        <div class="navbar-links">
            <a href="/database" class="nav-link ${activePage === 'database' ? 'active' : ''}">
                <span class="nav-icon">📁</span>
                <span>Database</span>
            </a>
            <a href="/chat" class="nav-link ${activePage === 'chat' ? 'active' : ''}">
                <span class="nav-icon">💬</span>
                <span>Chat</span>
            </a>
            ${email ? `
                <span class="nav-link" style="cursor:default; color: var(--surface-500);">
                    <span class="nav-icon">👤</span>
                    <span>${email}</span>
                </span>
                <button class="nav-btn-logout" onclick="logout()">Logout</button>
            ` : ''}
        </div>
    </nav>`;
}
