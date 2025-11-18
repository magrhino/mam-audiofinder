/**
 * Tests for LibraryIndicator component
 * Tests creation and display of library status indicators
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  createLibraryIndicator,
  addLibraryIndicator
} from '../../../app/static/js/components/libraryIndicator.js';
import { cleanupDOM, createTestContainer } from '../utils/dom-helpers.js';

describe('LibraryIndicator', () => {
  let container;

  beforeEach(() => {
    container = createTestContainer();
  });

  afterEach(() => {
    cleanupDOM();
  });

  describe('createLibraryIndicator()', () => {
    it('should create indicator when item is in library', () => {
      const indicator = createLibraryIndicator(true);

      expect(indicator).toBeInstanceOf(HTMLElement);
      expect(indicator.className).toBe('in-library-indicator');
      expect(indicator.textContent).toBe('✓');
      expect(indicator.getAttribute('title')).toBe('Already in your library');
      expect(indicator.getAttribute('aria-label')).toBe('Already in your library');
    });

    it('should return null when item is not in library', () => {
      const indicator = createLibraryIndicator(false);

      expect(indicator).toBeNull();
    });

    it('should return null for falsy values', () => {
      expect(createLibraryIndicator(null)).toBeNull();
      expect(createLibraryIndicator(undefined)).toBeNull();
      expect(createLibraryIndicator(0)).toBeNull();
      expect(createLibraryIndicator('')).toBeNull();
    });
  });

  describe('addLibraryIndicator()', () => {
    it('should add indicator to cover container', () => {
      const coverContainer = document.createElement('div');
      coverContainer.className = 'cover-container';
      container.appendChild(coverContainer);

      const indicator = addLibraryIndicator(coverContainer, true);

      expect(indicator).toBeInstanceOf(HTMLElement);
      expect(coverContainer.contains(indicator)).toBe(true);
      expect(coverContainer.querySelector('.in-library-indicator')).toBe(indicator);
    });

    it('should not add indicator when item not in library', () => {
      const coverContainer = document.createElement('div');
      coverContainer.className = 'cover-container';
      container.appendChild(coverContainer);

      const indicator = addLibraryIndicator(coverContainer, false);

      expect(indicator).toBeNull();
      expect(coverContainer.querySelector('.in-library-indicator')).toBeNull();
    });

    it('should return null when container is null', () => {
      const indicator = addLibraryIndicator(null, true);

      expect(indicator).toBeNull();
    });

    it('should return null when container is undefined', () => {
      const indicator = addLibraryIndicator(undefined, true);

      expect(indicator).toBeNull();
    });

    it('should not add duplicate indicators', () => {
      const coverContainer = document.createElement('div');
      coverContainer.className = 'cover-container';
      container.appendChild(coverContainer);

      const indicator1 = addLibraryIndicator(coverContainer, true);
      const indicator2 = addLibraryIndicator(coverContainer, true);

      expect(indicator1).toBe(indicator2);
      expect(coverContainer.querySelectorAll('.in-library-indicator')).toHaveLength(1);
    });

    it('should return existing indicator if already present', () => {
      const coverContainer = document.createElement('div');
      coverContainer.className = 'cover-container';
      container.appendChild(coverContainer);

      // Manually add indicator
      const existingIndicator = createLibraryIndicator(true);
      coverContainer.appendChild(existingIndicator);

      // Try to add again
      const indicator = addLibraryIndicator(coverContainer, true);

      expect(indicator).toBe(existingIndicator);
      expect(coverContainer.querySelectorAll('.in-library-indicator')).toHaveLength(1);
    });
  });

  describe('visual styling', () => {
    it('should have correct CSS class for styling', () => {
      const indicator = createLibraryIndicator(true);

      expect(indicator.className).toBe('in-library-indicator');
    });

    it('should use checkmark character', () => {
      const indicator = createLibraryIndicator(true);

      expect(indicator.textContent).toBe('✓');
    });

    it('should have accessibility attributes', () => {
      const indicator = createLibraryIndicator(true);

      expect(indicator.hasAttribute('title')).toBe(true);
      expect(indicator.hasAttribute('aria-label')).toBe(true);
    });
  });

  describe('integration scenarios', () => {
    it('should work with multiple cover containers', () => {
      const cover1 = document.createElement('div');
      const cover2 = document.createElement('div');
      const cover3 = document.createElement('div');

      container.appendChild(cover1);
      container.appendChild(cover2);
      container.appendChild(cover3);

      addLibraryIndicator(cover1, true);
      addLibraryIndicator(cover2, false);
      addLibraryIndicator(cover3, true);

      expect(cover1.querySelector('.in-library-indicator')).not.toBeNull();
      expect(cover2.querySelector('.in-library-indicator')).toBeNull();
      expect(cover3.querySelector('.in-library-indicator')).not.toBeNull();
    });

    it('should maintain indicator after DOM manipulation', () => {
      const coverContainer = document.createElement('div');
      container.appendChild(coverContainer);

      const indicator = addLibraryIndicator(coverContainer, true);

      // Add other content
      const img = document.createElement('img');
      coverContainer.appendChild(img);

      // Indicator should still be there
      expect(coverContainer.contains(indicator)).toBe(true);
      expect(coverContainer.querySelector('.in-library-indicator')).toBe(indicator);
    });
  });
});
