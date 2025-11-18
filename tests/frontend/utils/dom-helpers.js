/**
 * DOM helper utilities for testing
 * Simplifies DOM manipulation and assertions in tests
 */

import { vi } from 'vitest';

/**
 * Create a mock HTMLImageElement with load/error simulation
 */
export function createMockImage() {
  const img = document.createElement('img');
  const originalSetAttribute = img.setAttribute.bind(img);

  // Track when src is set
  img.setAttribute = vi.fn((name, value) => {
    originalSetAttribute(name, value);

    // Simulate immediate load when src is set (for testing)
    if (name === 'src') {
      setTimeout(() => {
        if (img.onload) {
          img.onload();
        }
      }, 0);
    }
  });

  return img;
}

/**
 * Simulate image load error
 */
export function simulateImageError(img) {
  setTimeout(() => {
    if (img.onerror) {
      img.onerror(new Error('Image load failed'));
    }
  }, 0);
}

/**
 * Create a cover container element with dataset
 */
export function createCoverContainer({ mamId, title, author, rowId = '' }) {
  const container = document.createElement('div');
  container.className = 'cover-skeleton';
  container.dataset.mamId = mamId || '';
  container.dataset.title = title || '';
  container.dataset.author = author || '';
  if (rowId) {
    container.dataset.rowId = rowId;
  }
  return container;
}

/**
 * Wait for next tick (useful for async DOM updates)
 */
export function nextTick() {
  return new Promise(resolve => setTimeout(resolve, 0));
}

/**
 * Wait for multiple ticks
 */
export function waitTicks(count = 1) {
  let promise = Promise.resolve();
  for (let i = 0; i < count; i++) {
    promise = promise.then(() => nextTick());
  }
  return promise;
}

/**
 * Query element and assert it exists
 */
export function getBySelector(parent, selector) {
  const element = parent.querySelector(selector);
  if (!element) {
    throw new Error(`Element not found: ${selector}`);
  }
  return element;
}

/**
 * Query all elements by selector
 */
export function getAllBySelector(parent, selector) {
  return Array.from(parent.querySelectorAll(selector));
}

/**
 * Simulate user input on an element
 */
export function setInputValue(input, value) {
  input.value = value;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}

/**
 * Simulate click event
 */
export function click(element) {
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

/**
 * Simulate select option change
 */
export function selectOption(select, value) {
  select.value = value;
  select.dispatchEvent(new Event('change', { bubbles: true }));
}

/**
 * Check if element has class
 */
export function hasClass(element, className) {
  return element.classList.contains(className);
}

/**
 * Get text content, trimmed
 */
export function getText(element) {
  return element.textContent.trim();
}

/**
 * Clean up DOM after test
 */
export function cleanupDOM() {
  document.body.innerHTML = '';
}

/**
 * Create a minimal DOM structure for testing
 */
export function createTestContainer() {
  const container = document.createElement('div');
  container.id = 'test-container';
  document.body.appendChild(container);
  return container;
}
