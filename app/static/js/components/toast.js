/**
 * Toast Component - Lightweight notification system
 * Displays transient messages for errors, warnings, and success states
 */

/**
 * Show a toast notification
 *
 * @param {string} message - Message to display
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info' (default: 'info')
 * @param {number} duration - Duration in milliseconds (default: 5000, 0 for permanent)
 */
export function showToast(message, type = 'info', duration = 5000) {
  // Create toast container if it doesn't exist
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  // Add icon based on type
  const icon = getToastIcon(type);

  // Set content
  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button class="toast-close" aria-label="Close">✕</button>
  `;

  // Close button handler
  const closeBtn = toast.querySelector('.toast-close');
  closeBtn.addEventListener('click', () => {
    removeToast(toast);
  });

  // Add to container
  container.appendChild(toast);

  // Trigger animation
  setTimeout(() => {
    toast.classList.add('toast-show');
  }, 10);

  // Auto-remove after duration (if not permanent)
  if (duration > 0) {
    setTimeout(() => {
      removeToast(toast);
    }, duration);
  }

  // Log to console based on type
  const logMethod = type === 'error' ? console.error : type === 'warning' ? console.warn : console.log;
  logMethod(`[Toast ${type}]`, message);

  return toast;
}

/**
 * Remove a toast element
 * @private
 */
function removeToast(toast) {
  toast.classList.remove('toast-show');
  toast.classList.add('toast-hide');

  setTimeout(() => {
    toast.remove();

    // Remove container if empty
    const container = document.getElementById('toast-container');
    if (container && container.children.length === 0) {
      container.remove();
    }
  }, 300);
}

/**
 * Get icon for toast type
 * @private
 */
function getToastIcon(type) {
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  };
  return icons[type] || icons.info;
}

/**
 * Escape HTML to prevent XSS
 * @private
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Show success toast
 */
export function showSuccess(message, duration = 3000) {
  return showToast(message, 'success', duration);
}

/**
 * Show error toast
 */
export function showError(message, duration = 5000) {
  return showToast(message, 'error', duration);
}

/**
 * Show warning toast
 */
export function showWarning(message, duration = 5000) {
  return showToast(message, 'warning', duration);
}

/**
 * Show info toast
 */
export function showInfo(message, duration = 5000) {
  return showToast(message, 'info', duration);
}
