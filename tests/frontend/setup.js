/**
 * Vitest setup file for frontend tests
 * Global test configuration and mocks
 */

import { vi } from 'vitest';

// Mock IntersectionObserver (not available in happy-dom)
global.IntersectionObserver = vi.fn().mockImplementation((callback) => {
  return {
    observe: vi.fn((element) => {
      // Immediately trigger callback to simulate element in viewport
      callback([{
        isIntersecting: true,
        target: element
      }]);
    }),
    unobserve: vi.fn(),
    disconnect: vi.fn()
  };
});

// Mock fetch globally (can be overridden per test)
global.fetch = vi.fn();

// Mock window.dispatchEvent for custom events
const originalDispatchEvent = window.dispatchEvent;
window.dispatchEvent = vi.fn(originalDispatchEvent);

// Mock document.createElement to auto-trigger onload for images
const originalCreateElement = document.createElement.bind(document);
document.createElement = (tagName, ...args) => {
  const element = originalCreateElement(tagName, ...args);

  if (tagName.toLowerCase() === 'img') {
    // Override src property to trigger onload when set
    let _src = '';
    Object.defineProperty(element, 'src', {
      get() {
        return _src;
      },
      set(value) {
        _src = value;
        // Trigger onload asynchronously
        setTimeout(() => {
          if (element.onload && typeof element.onload === 'function') {
            element.onload();
          }
        }, 0);
      }
    });
  }

  return element;
};

// Console helpers for debugging tests
global.console = {
  ...console,
  // Suppress console.log in tests unless explicitly needed
  log: vi.fn(),
  // Keep errors and warnings visible
  error: console.error,
  warn: console.warn
};
