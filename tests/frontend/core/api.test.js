/**
 * Tests for API client
 * Tests all API endpoints including description fetching, cover fetching, etc.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { api } from '../../../app/static/js/core/api.js';
import {
  mockConfig,
  mockSearchResult,
  mockHistoryItem,
  mockTorrent,
  mockTorrentTree,
  mockMultiDiscTorrentTree,
  mockImportResponse,
  mockCoverResponse,
  mockFetchResponses,
  resetMocks
} from '../mocks/api.mock.js';

describe('API Client', () => {
  beforeEach(() => {
    mockFetchResponses();
  });

  afterEach(() => {
    resetMocks();
  });

  describe('health()', () => {
    it('should check health endpoint', async () => {
      const result = await api.health();

      expect(result).toEqual({ ok: true });
      expect(global.fetch).toHaveBeenCalledWith('/health');
    });
  });

  describe('getConfig()', () => {
    it('should fetch application configuration', async () => {
      const result = await api.getConfig();

      expect(result).toEqual(mockConfig);
      expect(global.fetch).toHaveBeenCalledWith('/config');
    });

    it('should throw on HTTP error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500
      });

      await expect(api.getConfig()).rejects.toThrow('HTTP 500');
    });
  });

  describe('search()', () => {
    it('should search MAM with query', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ results: [mockSearchResult] })
      });

      const payload = {
        tor: { text: 'hobbit', sortType: 'relevance' },
        perpage: 50
      };

      const result = await api.search(payload);

      expect(result.results).toHaveLength(1);
      expect(result.results[0]).toEqual(mockSearchResult);
      expect(global.fetch).toHaveBeenCalledWith('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    });

    it('should handle search errors', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400
      });

      const payload = {
        tor: { text: '', sortType: 'relevance' },
        perpage: 50
      };

      await expect(api.search(payload)).rejects.toThrow('HTTP 400');
    });
  });

  describe('fetchCover()', () => {
    it('should fetch cover for audiobook', async () => {
      const params = {
        mam_id: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        max_retries: '2'
      };

      const result = await api.fetchCover(params);

      expect(result).toEqual(mockCoverResponse);
      expect(result.cover_url).toBe('/covers/123456.jpg');
      expect(result.item_id).toBe('abs_item_123');

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain('/api/covers/fetch');
      expect(callUrl).toContain('mam_id=123456');
      expect(callUrl).toContain('title=The+Hobbit');
      expect(callUrl).toContain('author=J.R.R.+Tolkien');
    });

    it('should handle missing author', async () => {
      const params = {
        mam_id: '123456',
        title: 'The Hobbit',
        author: '',
        max_retries: '2'
      };

      await api.fetchCover(params);

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain('author=');
    });

    it('should use default max_retries', async () => {
      const params = {
        mam_id: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      };

      await api.fetchCover(params);

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain('max_retries=2');
    });
  });

  describe('getHistory()', () => {
    it('should fetch history items with no-cache headers', async () => {
      const result = await api.getHistory();

      expect(result.items).toHaveLength(1);
      expect(result.items[0]).toEqual(mockHistoryItem);

      const fetchCall = global.fetch.mock.calls[0];
      expect(fetchCall[0]).toBe('/api/history');
      expect(fetchCall[1].cache).toBe('no-cache');
      expect(fetchCall[1].headers['Cache-Control']).toContain('no-cache');
    });

    it('should log history response', async () => {
      const consoleSpy = vi.spyOn(global.console, 'log');

      await api.getHistory();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[API] History response:'),
        expect.any(Number),
        'items'
      );
    });
  });

  describe('verifyHistoryItem()', () => {
    it('should verify history item', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ok: true,
          verification: { status: 'verified', note: 'Matched by ASIN' }
        })
      });

      const result = await api.verifyHistoryItem(1);

      expect(result.ok).toBe(true);
      expect(result.verification.status).toBe('verified');
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/history/1/verify',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should handle verification errors with detail', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'History item not found' })
      });

      await expect(api.verifyHistoryItem(999)).rejects.toThrow('HTTP 404 — History item not found');
    });
  });

  describe('deleteHistoryItem()', () => {
    it('should delete history item', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ok: true })
      });

      const result = await api.deleteHistoryItem(1);

      expect(result.ok).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/history/1',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  describe('getCompletedTorrents()', () => {
    it('should fetch completed torrents', async () => {
      const result = await api.getCompletedTorrents();

      expect(result.items).toHaveLength(1);
      expect(result.items[0]).toEqual(mockTorrent);
      expect(global.fetch).toHaveBeenCalledWith('/qb/torrents');
    });
  });

  describe('getTorrentTree()', () => {
    it('should fetch torrent file tree', async () => {
      const result = await api.getTorrentTree('abc123def456');

      expect(result).toEqual(mockTorrentTree);
      expect(result.single_file).toBe(false);
      expect(result.files).toHaveLength(3);
      expect(global.fetch).toHaveBeenCalledWith(
        '/qb/torrent/abc123def456/tree'
      );
    });

    it('should URL encode hash parameter', async () => {
      await api.getTorrentTree('abc/123');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('abc%2F123')
      );
    });
  });

  describe('importTorrent()', () => {
    it('should import torrent with flatten option', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockImportResponse
      });

      const params = {
        author: 'J.R.R. Tolkien',
        title: 'The Hobbit',
        hash: 'abc123def456',
        history_id: 1,
        flatten: true
      };

      const result = await api.importTorrent(params);

      expect(result).toEqual(mockImportResponse);
      expect(result.files_linked).toBe(3);
      expect(result.verification.status).toBe('verified');

      expect(global.fetch).toHaveBeenCalledWith('/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
    });

    it('should handle import errors with detail', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Torrent not found' })
      });

      const params = {
        author: 'Test',
        title: 'Test',
        hash: 'invalid',
        history_id: 1,
        flatten: false
      };

      await expect(api.importTorrent(params)).rejects.toThrow('HTTP 404 — Torrent not found');
    });
  });

  describe('addTorrent()', () => {
    it('should add torrent to qBittorrent', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ok: true })
      });

      const params = {
        mam_id: '123456',
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien'
      };

      const result = await api.addTorrent(params);

      expect(result.ok).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith('/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
    });

    it('should handle add torrent errors', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'qBittorrent connection failed' })
      });

      await expect(api.addTorrent({})).rejects.toThrow('HTTP 500 — qBittorrent connection failed');
    });
  });

  describe('getLogs()', () => {
    it('should fetch logs with parameters', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ok: true, logs: ['Log line 1', 'Log line 2'] })
      });

      const params = { lines: 100, level: 'ERROR' };
      const result = await api.getLogs(params);

      expect(result.logs).toHaveLength(2);

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain('/api/logs');
      expect(callUrl).toContain('lines=100');
      expect(callUrl).toContain('level=ERROR');
    });
  });

  describe('getShowcase()', () => {
    it('should fetch showcase grouped results', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          groups: [{ title: 'The Hobbit', items: [mockSearchResult] }],
          total_groups: 1,
          total_results: 1
        })
      });

      const params = { query: 'hobbit', limit: 20 };
      const result = await api.getShowcase(params);

      expect(result.total_groups).toBe(1);
      expect(result.groups).toHaveLength(1);

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain('/api/showcase');
      expect(callUrl).toContain('query=hobbit');
      expect(callUrl).toContain('limit=20');
    });
  });

  describe('searchSeries()', () => {
    it('should search for series on Hardcover', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          hardcover_series: [{ id: 1, name: 'The Lord of the Rings' }],
          cached: false
        })
      });

      const params = {
        title: 'Lord of the Rings',
        author: 'J.R.R. Tolkien',
        limit: 10
      };

      const result = await api.searchSeries(params);

      expect(result.hardcover_series).toHaveLength(1);
      expect(global.fetch).toHaveBeenCalledWith('/api/series/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.stringContaining('Lord of the Rings')
      });
    });

    it('should handle optional parameters', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ hardcover_series: [], cached: false })
      });

      const params = { title: 'Hobbit' };
      await api.searchSeries(params);

      const body = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(body.author).toBe('');
      expect(body.normalized_title).toBeNull();
    });
  });

  describe('getSeriesBooks()', () => {
    it('should fetch books in a series', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          series_id: 1,
          series_name: 'The Lord of the Rings',
          books: [
            { title: 'The Fellowship of the Ring', position: 1 },
            { title: 'The Two Towers', position: 2 }
          ],
          cached: false
        })
      });

      const result = await api.getSeriesBooks(1);

      expect(result.books).toHaveLength(2);
      expect(result.series_name).toBe('The Lord of the Rings');
      expect(global.fetch).toHaveBeenCalledWith('/api/series/1/books');
    });

    it('should handle series fetch errors', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Series not found' })
      });

      await expect(api.getSeriesBooks(999)).rejects.toThrow('HTTP 404 — Series not found');
    });
  });
});
