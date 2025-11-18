/**
 * Mock API responses for testing
 * Simulates backend API endpoints with realistic data
 */

import { vi } from 'vitest';

/**
 * Sample MAM search result
 */
export const mockSearchResult = {
  id: '123456',
  title: 'The Hobbit',
  author: 'J.R.R. Tolkien',
  narrator: 'Andy Serkis',
  category: 'Audiobooks',
  size: '500.5 MiB',
  seeders: 42,
  leechers: 5,
  snatched: 1250,
  added: '2024-01-15 10:30:00'
};

/**
 * Sample cover fetch response
 */
export const mockCoverResponse = {
  cover_url: '/covers/123456.jpg',
  item_id: 'abs_item_123',
  cached: true
};

/**
 * Sample history item
 */
export const mockHistoryItem = {
  id: 1,
  mam_id: '123456',
  title: 'The Hobbit',
  author: 'J.R.R. Tolkien',
  narrator: 'Andy Serkis',
  dl: 'https://example.com/torrent',
  added_at: '2024-01-15T10:30:00',
  qb_status: 'completed',
  qb_hash: 'abc123def456',
  imported_at: null,
  abs_item_id: 'abs_item_123',
  abs_cover_url: '/covers/123456.jpg',
  abs_verify_status: 'verified',
  abs_verify_note: 'Matched by ASIN',
  abs_description: 'A fantastic adventure story...',
  abs_metadata: JSON.stringify({ isbn: '1234567890' }),
  abs_description_source: 'audiobookshelf'
};

/**
 * Sample torrent from qBittorrent
 */
export const mockTorrent = {
  hash: 'abc123def456',
  name: 'The Hobbit - J.R.R. Tolkien',
  size: 524800000,
  progress: 1.0,
  state: 'completed',
  category: 'mam-audiobooks',
  save_path: '/media/downloads/qbittorrent',
  content_path: '/media/downloads/qbittorrent/The Hobbit - J.R.R. Tolkien',
  mam_id: '123456',
  single_file: false,
  root: 'The Hobbit - J.R.R. Tolkien'
};

/**
 * Sample torrent tree data
 */
export const mockTorrentTree = {
  hash: 'abc123def456',
  name: 'The Hobbit - J.R.R. Tolkien',
  single_file: false,
  has_disc_structure: false,
  disc_count: 0,
  recommended_flatten: false,
  files: [
    {
      path: 'Chapter 01.mp3',
      size: 5248000
    },
    {
      path: 'Chapter 02.mp3',
      size: 5248000
    },
    {
      path: 'Chapter 03.mp3',
      size: 5248000
    }
  ]
};

/**
 * Sample multi-disc torrent tree data
 */
export const mockMultiDiscTorrentTree = {
  hash: 'def456abc123',
  name: 'The Lord of the Rings - J.R.R. Tolkien',
  single_file: false,
  has_disc_structure: true,
  disc_count: 3,
  recommended_flatten: true,
  files: [
    {
      path: 'Disc 1/Track 01.mp3',
      size: 5248000
    },
    {
      path: 'Disc 1/Track 02.mp3',
      size: 5248000
    },
    {
      path: 'Disc 2/Track 01.mp3',
      size: 5248000
    },
    {
      path: 'Disc 2/Track 02.mp3',
      size: 5248000
    },
    {
      path: 'Disc 3/Track 01.mp3',
      size: 5248000
    },
    {
      path: 'Disc 3/Track 02.mp3',
      size: 5248000
    }
  ]
};

/**
 * Sample import response
 */
export const mockImportResponse = {
  ok: true,
  dest: '/media/library/J.R.R. Tolkien/The Hobbit',
  files_copied: 3,
  files_linked: 3,
  import_mode: 'link',
  verification: {
    status: 'verified',
    item_id: 'abs_item_123',
    note: 'Matched by ASIN'
  }
};

/**
 * Sample config response
 */
export const mockConfig = {
  import_mode: 'link',
  flatten_discs: true,
  abs_configured: true,
  abs_check_library: true,
  qb_category: 'mam-audiobooks',
  qb_postimport_category: 'mam-imported'
};

/**
 * Create a mock API client
 */
export function createMockApi() {
  return {
    health: vi.fn().mockResolvedValue({ ok: true }),
    getConfig: vi.fn().mockResolvedValue(mockConfig),
    search: vi.fn().mockResolvedValue({ results: [mockSearchResult] }),
    addTorrent: vi.fn().mockResolvedValue({ ok: true }),
    getHistory: vi.fn().mockResolvedValue({ items: [mockHistoryItem] }),
    deleteHistoryItem: vi.fn().mockResolvedValue({ ok: true }),
    verifyHistoryItem: vi.fn().mockResolvedValue({
      ok: true,
      verification: { status: 'verified', note: 'Matched by ASIN' }
    }),
    getCompletedTorrents: vi.fn().mockResolvedValue({ items: [mockTorrent] }),
    getTorrentTree: vi.fn().mockResolvedValue(mockTorrentTree),
    importTorrent: vi.fn().mockResolvedValue(mockImportResponse),
    getLogs: vi.fn().mockResolvedValue({ ok: true, logs: [] }),
    fetchCover: vi.fn().mockResolvedValue(mockCoverResponse),
    getShowcase: vi.fn().mockResolvedValue({
      groups: [],
      total_groups: 0,
      total_results: 0
    }),
    searchSeries: vi.fn().mockResolvedValue({
      hardcover_series: [],
      cached: false
    }),
    getSeriesBooks: vi.fn().mockResolvedValue({
      books: [],
      cached: false
    })
  };
}

/**
 * Mock fetch responses for various endpoints
 */
export function mockFetchResponses() {
  global.fetch = vi.fn((url, options) => {
    const method = options?.method || 'GET';

    // Health endpoint
    if (url === '/health') {
      return Promise.resolve({
        ok: true,
        json: async () => ({ ok: true })
      });
    }

    // Config endpoint
    if (url === '/config') {
      return Promise.resolve({
        ok: true,
        json: async () => mockConfig
      });
    }

    // Cover fetch endpoint
    if (url.startsWith('/api/covers/fetch')) {
      return Promise.resolve({
        ok: true,
        json: async () => mockCoverResponse
      });
    }

    // History endpoint
    if (url === '/api/history') {
      return Promise.resolve({
        ok: true,
        json: async () => ({ items: [mockHistoryItem] })
      });
    }

    // Torrent tree endpoint
    if (url.includes('/qb/torrent/') && url.includes('/tree')) {
      return Promise.resolve({
        ok: true,
        json: async () => mockTorrentTree
      });
    }

    // Completed torrents endpoint
    if (url === '/qb/torrents') {
      return Promise.resolve({
        ok: true,
        json: async () => ({ items: [mockTorrent] })
      });
    }

    // Import endpoint
    if (url === '/import' && method === 'POST') {
      return Promise.resolve({
        ok: true,
        json: async () => mockImportResponse
      });
    }

    // Default fallback
    return Promise.resolve({
      ok: false,
      status: 404,
      json: async () => ({ error: 'Not found' })
    });
  });
}

/**
 * Reset all mocks
 */
export function resetMocks() {
  vi.clearAllMocks();
}
