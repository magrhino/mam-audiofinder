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

// Console helpers for debugging tests
global.console = {
  ...console,
  // Suppress console.log in tests unless explicitly needed
  log: vi.fn(),
  // Keep errors and warnings visible
  error: console.error,
  warn: console.warn
};
