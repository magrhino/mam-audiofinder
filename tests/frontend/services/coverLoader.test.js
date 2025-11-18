/**
 * Tests for CoverLoader service
 * Tests lazy loading, IntersectionObserver integration, and cover fetching
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { CoverLoader } from '../../../app/static/js/services/coverLoader.js';
import { mockCoverResponse, mockFetchResponses, resetMocks } from '../mocks/api.mock.js';
import { createCoverContainer, nextTick, cleanupDOM, createTestContainer } from '../utils/dom-helpers.js';

describe('CoverLoader', () => {
  let coverLoader;
  let container;

  beforeEach(() => {
    coverLoader = new CoverLoader();
    container = createTestContainer();
    mockFetchResponses();
  });

  afterEach(() => {
    coverLoader.destroy();
    cleanupDOM();
    resetMocks();
  });

  describe('initialization', () => {
    it('should create CoverLoader instance', () => {
      expect(coverLoader).toBeDefined();
      expect(coverLoader.observer).toBeNull();
      expect(coverLoader.rowStateStore).toBeInstanceOf(Map);
    });

    it('should initialize IntersectionObserver on init()', () => {
      const observer = coverLoader.init();

      expect(observer).toBeDefined();
      expect(coverLoader.observer).toBe(observer);
    });

    it('should return existing observer on subsequent init() calls', () => {
      const observer1 = coverLoader.init();
      const observer2 = coverLoader.init();

      expect(observer1).toBe(observer2);
    });

    it('should auto-initialize observer on first observe() call', () => {
      const element = createCoverContainer({
        mamId: '123456',
        title: 'Test Book',
        author: 'Test Author'
      });

      expect(coverLoader.observer).toBeNull();

      coverLoader.observe(element);

      expect(coverLoader.observer).toBeDefined();
    });
  });

  describe('row state management', () => {
    it('should store row state', () => {
      const state = { title: 'Test', author: 'Author' };
      coverLoader.setRowState('row-1', state);

      expect(coverLoader.getRowState('row-1')).toBe(state);
    });

    it('should retrieve row state', () => {
      const state = { title: 'Test', author: 'Author' };
      coverLoader.setRowState('row-1', state);

      const retrieved = coverLoader.getRowState('row-1');
      expect(retrieved).toEqual(state);
    });

    it('should return undefined for non-existent row state', () => {
      expect(coverLoader.getRowState('non-existent')).toBeUndefined();
    });

    it('should clear all row state', () => {
      coverLoader.setRowState('row-1', { title: 'Test 1' });
      coverLoader.setRowState('row-2', { title: 'Test 2' });

      coverLoader.clearRowState();

      expect(coverLoader.getRowState('row-1')).toBeUndefined();
      expect(coverLoader.getRowState('row-2')).toBeUndefined();
    });
  });

  describe('cover container creation', () => {
    it('should create cover container with correct attributes', () => {
      const element = coverLoader.createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        rowId: 'row-1'
      });

      expect(element).toBeInstanceOf(HTMLElement);
      expect(element.className).toBe('cover-skeleton');
      expect(element.dataset.mamId).toBe('123456');
      expect(element.dataset.title).toBe('The Hobbit');
      expect(element.dataset.author).toBe('J.R.R. Tolkien');
      expect(element.dataset.rowId).toBe('row-1');
    });

    it('should create cover container without rowId', () => {
      const element = coverLoader.createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      });

      expect(element.dataset.rowId).toBe('');
    });

    it('should handle empty values', () => {
      const element = coverLoader.createCoverContainer({
        mamId: '',
        title: '',
        author: ''
      });

      expect(element.dataset.mamId).toBe('');
      expect(element.dataset.title).toBe('');
      expect(element.dataset.author).toBe('');
    });
  });

  describe('cover fetching', () => {
    it('should fetch and display cover image', async () => {
      const coverContainer = createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      });

      container.appendChild(coverContainer);

      await coverLoader.fetchCoverForItem(
        coverContainer,
        '123456',
        'The Hobbit',
        'J.R.R. Tolkien'
      );

      await nextTick();
      await nextTick(); // Extra tick for image load

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/covers/fetch')
      );

      const img = coverContainer.querySelector('img.cover-image');
      expect(img).toBeDefined();
      expect(img.src).toContain('/covers/123456.jpg');
    });

    it('should update row state with cover info', async () => {
      const coverContainer = createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        rowId: 'row-1'
      });

      const rowState = { title: 'The Hobbit' };
      coverLoader.setRowState('row-1', rowState);

      container.appendChild(coverContainer);

      await coverLoader.fetchCoverForItem(
        coverContainer,
        '123456',
        'The Hobbit',
        'J.R.R. Tolkien',
        rowState
      );

      await nextTick();

      expect(rowState.abs_cover_url).toBe('/covers/123456.jpg');
      expect(rowState.abs_item_id).toBe('abs_item_123');
    });

    it('should handle cover fetch error', async () => {
      // Override fetch to return error
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ error: 'No cover found' })
      });

      const coverContainer = createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      });

      container.appendChild(coverContainer);

      await coverLoader.fetchCoverForItem(
        coverContainer,
        '123456',
        'The Hobbit',
        'J.R.R. Tolkien'
      );

      await nextTick();

      expect(coverContainer.innerHTML).toContain('No cover');
      expect(coverContainer.classList.contains('cover-loaded')).toBe(false);
    });

    it('should handle network error', async () => {
      // Override fetch to throw error
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const coverContainer = createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      });

      container.appendChild(coverContainer);

      await coverLoader.fetchCoverForItem(
        coverContainer,
        '123456',
        'The Hobbit',
        'J.R.R. Tolkien'
      );

      await nextTick();

      expect(coverContainer.innerHTML).toContain('Error');
      expect(coverContainer.classList.contains('cover-loaded')).toBe(false);
    });

    it('should show placeholder when missing required data', async () => {
      const coverContainer = createCoverContainer({
        mamId: '',
        title: '',
        author: ''
      });

      coverLoader.init();
      coverLoader.observe(coverContainer);

      await nextTick();

      expect(coverContainer.innerHTML).toContain('No info');
    });

    it('should add loaded class when image loads successfully', async () => {
      const coverContainer = createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      });

      container.appendChild(coverContainer);

      await coverLoader.fetchCoverForItem(
        coverContainer,
        '123456',
        'The Hobbit',
        'J.R.R. Tolkien'
      );

      await nextTick();
      await nextTick();

      expect(coverContainer.classList.contains('cover-loaded')).toBe(true);
    });
  });

  describe('IntersectionObserver integration', () => {
    it('should observe element and trigger cover fetch', async () => {
      const coverContainer = createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      });

      container.appendChild(coverContainer);

      coverLoader.observe(coverContainer);

      await nextTick();
      await nextTick();

      // IntersectionObserver mock immediately triggers callback
      expect(global.fetch).toHaveBeenCalled();
    });

    it('should unobserve element after fetching', async () => {
      const coverContainer = createCoverContainer({
        mamId: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      });

      container.appendChild(coverContainer);

      coverLoader.init();
      const unobserveSpy = vi.spyOn(coverLoader.observer, 'unobserve');

      coverLoader.observe(coverContainer);

      await nextTick();

      // Observer should unobserve after triggering
      expect(unobserveSpy).toHaveBeenCalledWith(coverContainer);
    });
  });

  describe('cleanup', () => {
    it('should disconnect observer on destroy', () => {
      coverLoader.init();
      const disconnectSpy = vi.spyOn(coverLoader.observer, 'disconnect');

      coverLoader.destroy();

      expect(disconnectSpy).toHaveBeenCalled();
      expect(coverLoader.observer).toBeNull();
    });

    it('should clear row state on destroy', () => {
      coverLoader.setRowState('row-1', { title: 'Test' });

      coverLoader.destroy();

      expect(coverLoader.getRowState('row-1')).toBeUndefined();
    });

    it('should handle destroy without initialization', () => {
      const newLoader = new CoverLoader();

      expect(() => newLoader.destroy()).not.toThrow();
    });
  });
});
