/**
 * Tests for ImportForm component
 * Tests torrent import workflow, multi-disc detection, and form interactions
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ImportForm } from '../../../app/static/js/components/importForm.js';
import {
  mockHistoryItem,
  mockTorrent,
  mockTorrentTree,
  mockMultiDiscTorrentTree,
  mockImportResponse,
  mockConfig,
  mockFetchResponses,
  resetMocks
} from '../mocks/api.mock.js';
import {
  cleanupDOM,
  createTestContainer,
  nextTick,
  waitTicks,
  getBySelector,
  setInputValue,
  click,
  selectOption
} from '../utils/dom-helpers.js';

describe('ImportForm', () => {
  let container;
  let historyTable;
  let expanderRow;
  let importForm;

  beforeEach(() => {
    container = createTestContainer();
    mockFetchResponses();

    // Create minimal DOM structure
    historyTable = document.createElement('table');
    expanderRow = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 10;
    expanderRow.appendChild(td);
    historyTable.appendChild(expanderRow);
    container.appendChild(historyTable);

    importForm = new ImportForm(mockHistoryItem, expanderRow, historyTable);
  });

  afterEach(() => {
    cleanupDOM();
    resetMocks();
  });

  describe('initialization', () => {
    it('should create ImportForm instance', () => {
      expect(importForm).toBeDefined();
      expect(importForm.historyItem).toBe(mockHistoryItem);
      expect(importForm.expanderRow).toBe(expanderRow);
      expect(importForm.treeData).toBeNull();
    });

    it('should render import form with correct structure', async () => {
      await importForm.render();

      const form = expanderRow.querySelector('.import-form');
      expect(form).toBeDefined();

      expect(expanderRow.querySelector('.imp-author')).toBeDefined();
      expect(expanderRow.querySelector('.imp-title')).toBeDefined();
      expect(expanderRow.querySelector('.imp-torrent')).toBeDefined();
      expect(expanderRow.querySelector('.imp-go')).toBeDefined();
      expect(expanderRow.querySelector('.imp-flatten')).toBeDefined();
      expect(expanderRow.querySelector('.imp-view-files')).toBeDefined();
    });

    it('should pre-populate form with history item data', async () => {
      await importForm.render();

      const authorInput = getBySelector(expanderRow, '.imp-author');
      const titleInput = getBySelector(expanderRow, '.imp-title');

      expect(authorInput.value).toBe(mockHistoryItem.author);
      expect(titleInput.value).toBe(mockHistoryItem.title);
    });

    it('should set button text based on import mode', async () => {
      global.fetch = vi.fn((url) => {
        if (url === '/config') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ ...mockConfig, import_mode: 'copy' })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();

      const btn = getBySelector(expanderRow, '.imp-go');
      expect(btn.textContent).toBe('Copy to Library');
    });

    it('should show "Link to Library" for link mode', async () => {
      global.fetch = vi.fn((url) => {
        if (url === '/config') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ ...mockConfig, import_mode: 'link' })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();

      const btn = getBySelector(expanderRow, '.imp-go');
      expect(btn.textContent).toBe('Link to Library');
    });

    it('should show "Move to Library" for move mode', async () => {
      global.fetch = vi.fn((url) => {
        if (url === '/config') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ ...mockConfig, import_mode: 'move' })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();

      const btn = getBySelector(expanderRow, '.imp-go');
      expect(btn.textContent).toBe('Move to Library');
    });
  });

  describe('torrent loading', () => {
    it('should load and display completed torrents', async () => {
      global.fetch = vi.fn((url) => {
        if (url === '/qb/torrents') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ items: [mockTorrent] })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await nextTick();

      const select = getBySelector(expanderRow, '.imp-torrent');
      expect(select.options.length).toBeGreaterThan(0);
      expect(select.options[0].textContent).toContain(mockTorrent.name);
    });

    it('should auto-select torrent by hash match', async () => {
      global.fetch = vi.fn((url) => {
        if (url === '/qb/torrents') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ items: [mockTorrent] })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await nextTick();

      const select = getBySelector(expanderRow, '.imp-torrent');
      expect(select.value).toBe(mockTorrent.hash);

      const statusEl = getBySelector(expanderRow, '.imp-status');
      expect(statusEl.innerHTML).toContain('auto-selected');
    });

    it('should auto-select torrent by MAM ID match', async () => {
      const differentHashItem = {
        ...mockHistoryItem,
        qb_hash: 'different_hash'
      };

      const form = new ImportForm(differentHashItem, expanderRow, historyTable);

      global.fetch = vi.fn((url) => {
        if (url === '/qb/torrents') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ items: [mockTorrent] })
          });
        }
        return mockFetchResponses()(url);
      });

      await form.render();
      await nextTick();

      const select = getBySelector(expanderRow, '.imp-torrent');
      expect(select.value).toBe(mockTorrent.hash);
    });

    it('should show message when no torrents found', async () => {
      global.fetch = vi.fn((url) => {
        if (url === '/qb/torrents') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ items: [] })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await nextTick();

      const select = getBySelector(expanderRow, '.imp-torrent');
      expect(select.options[0].textContent).toContain('No completed torrents');
    });

    it('should handle torrent loading error', async () => {
      global.fetch = vi.fn((url) => {
        if (url === '/qb/torrents') {
          return Promise.reject(new Error('Connection failed'));
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await nextTick();

      const select = getBySelector(expanderRow, '.imp-torrent');
      expect(select.options[0].textContent).toContain('Failed to load');
    });
  });

  describe('multi-disc detection', () => {
    it('should detect multi-disc structure', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/tree')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockMultiDiscTorrentTree
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await importForm.detectMultiDisc('def456abc123');
      await nextTick();

      const flattenCheckbox = getBySelector(expanderRow, '.imp-flatten');
      const hint = getBySelector(expanderRow, '.imp-detection-hint');

      expect(flattenCheckbox.checked).toBe(true);
      expect(hint.innerHTML).toContain('Multi-disc detected');
      expect(hint.innerHTML).toContain('3 discs');
    });

    it('should not recommend flatten for single file', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/tree')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              ...mockTorrentTree,
              single_file: true
            })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await importForm.detectMultiDisc('abc123def456');
      await nextTick();

      const flattenCheckbox = getBySelector(expanderRow, '.imp-flatten');
      const hint = getBySelector(expanderRow, '.imp-detection-hint');

      expect(flattenCheckbox.checked).toBe(false);
      expect(flattenCheckbox.disabled).toBe(true);
      expect(hint.innerHTML).toContain('Single file');
    });

    it('should not recommend flatten for normal structure', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/tree')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockTorrentTree
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await importForm.detectMultiDisc('abc123def456');
      await nextTick();

      const flattenCheckbox = getBySelector(expanderRow, '.imp-flatten');

      expect(flattenCheckbox.checked).toBe(false);
      expect(flattenCheckbox.disabled).toBe(false);
    });
  });

  describe('file tree view', () => {
    it('should toggle tree view visibility', async () => {
      await importForm.render();
      importForm.treeData = mockTorrentTree;

      const viewFilesBtn = getBySelector(expanderRow, '.imp-view-files');
      const treeView = getBySelector(expanderRow, '.imp-tree-view');

      expect(treeView.style.display).toBe('none');

      importForm.toggleTreeView();
      expect(treeView.style.display).toBe('block');
      expect(viewFilesBtn.textContent).toContain('Hide Files');

      importForm.toggleTreeView();
      expect(treeView.style.display).toBe('none');
      expect(viewFilesBtn.textContent).toContain('View Files');
    });

    it('should render original file structure', async () => {
      await importForm.render();

      const html = importForm.renderTreeView(mockTorrentTree, false);

      expect(html).toContain('Original structure');
      expect(html).toContain('Chapter 01.mp3');
      expect(html).toContain('Chapter 02.mp3');
      expect(html).toContain('Chapter 03.mp3');
    });

    it('should render flattened preview for multi-disc', async () => {
      await importForm.render();

      const html = importForm.renderTreeView(mockMultiDiscTorrentTree, true);

      expect(html).toContain('Preview after flatten');
      expect(html).toContain('Part 001');
      expect(html).toContain('Part 002');
      expect(html).not.toContain('Disc 1');
    });

    it('should skip .cue files in flattened preview', async () => {
      const treeWithCue = {
        ...mockMultiDiscTorrentTree,
        files: [
          ...mockMultiDiscTorrentTree.files,
          { path: 'Disc 1/data.cue', size: 1024 }
        ]
      };

      await importForm.render();

      const html = importForm.renderTreeView(treeWithCue, true);

      expect(html).not.toContain('.cue');
    });

    it('should update tree view when flatten checkbox changes', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('/tree')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockMultiDiscTorrentTree
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await importForm.detectMultiDisc('def456abc123');
      await nextTick();

      const viewFilesBtn = getBySelector(expanderRow, '.imp-view-files');
      click(viewFilesBtn);

      const treeView = getBySelector(expanderRow, '.imp-tree-view');
      expect(treeView.innerHTML).toContain('Preview after flatten');

      const flattenCheckbox = getBySelector(expanderRow, '.imp-flatten');
      flattenCheckbox.checked = false;
      flattenCheckbox.dispatchEvent(new Event('change'));

      await nextTick();

      expect(treeView.innerHTML).toContain('Original structure');
    });
  });

  describe('import execution', () => {
    it('should perform import with correct parameters', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url === '/import' && options?.method === 'POST') {
          const body = JSON.parse(options.body);
          expect(body.author).toBe('J.R.R. Tolkien');
          expect(body.title).toBe('The Hobbit');
          expect(body.hash).toBe('abc123def456');
          expect(body.history_id).toBe(1);
          expect(body.flatten).toBe(false);

          return Promise.resolve({
            ok: true,
            json: async () => mockImportResponse
          });
        }
        return mockFetchResponses()(url, options);
      });

      await importForm.render();
      await nextTick();

      const goBtn = getBySelector(expanderRow, '.imp-go');
      await click(goBtn);

      await waitTicks(3);

      const statusEl = getBySelector(expanderRow, '.imp-status');
      expect(statusEl.textContent).toContain('Done');
      expect(statusEl.textContent).toContain('3 files');
    });

    it('should validate required fields before import', async () => {
      await importForm.render();

      const authorInput = getBySelector(expanderRow, '.imp-author');
      setInputValue(authorInput, '');

      const goBtn = getBySelector(expanderRow, '.imp-go');
      await click(goBtn);

      await nextTick();

      const statusEl = getBySelector(expanderRow, '.imp-status');
      expect(statusEl.textContent).toContain('Please fill');
    });

    it('should disable button during import', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url === '/import' && options?.method === 'POST') {
          return new Promise(resolve => {
            setTimeout(() => {
              resolve({
                ok: true,
                json: async () => mockImportResponse
              });
            }, 100);
          });
        }
        return mockFetchResponses()(url, options);
      });

      await importForm.render();
      await nextTick();

      const goBtn = getBySelector(expanderRow, '.imp-go');

      click(goBtn);
      await nextTick();

      expect(goBtn.disabled).toBe(true);
    });

    it('should show import statistics', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url === '/import' && options?.method === 'POST') {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              ...mockImportResponse,
              files_copied: 10,
              files_linked: 8
            })
          });
        }
        return mockFetchResponses()(url, options);
      });

      await importForm.render();
      await nextTick();

      const goBtn = getBySelector(expanderRow, '.imp-go');
      await click(goBtn);

      await waitTicks(3);

      const statusEl = getBySelector(expanderRow, '.imp-status');
      expect(statusEl.textContent).toContain('10 files');
      expect(statusEl.textContent).toContain('8 hardlinked');
      expect(statusEl.textContent).toContain('2 copied');
    });

    it('should handle import error', async () => {
      global.fetch = vi.fn((url, options) => {
        if (url === '/import' && options?.method === 'POST') {
          return Promise.resolve({
            ok: false,
            status: 404,
            json: async () => ({ detail: 'Torrent not found' })
          });
        }
        return mockFetchResponses()(url, options);
      });

      await importForm.render();
      await nextTick();

      const goBtn = getBySelector(expanderRow, '.imp-go');
      await click(goBtn);

      await waitTicks(3);

      const statusEl = getBySelector(expanderRow, '.imp-status');
      expect(statusEl.textContent).toContain('Failed');
      expect(statusEl.textContent).toContain('Torrent not found');
      expect(goBtn.disabled).toBe(false);
    });

    it('should dispatch importCompleted event', async () => {
      const eventSpy = vi.fn();
      window.addEventListener('importCompleted', eventSpy);

      global.fetch = vi.fn((url, options) => {
        if (url === '/import' && options?.method === 'POST') {
          return Promise.resolve({
            ok: true,
            json: async () => mockImportResponse
          });
        }
        return mockFetchResponses()(url, options);
      });

      await importForm.render();
      await nextTick();

      const goBtn = getBySelector(expanderRow, '.imp-go');
      await click(goBtn);

      await waitTicks(3);

      expect(eventSpy).toHaveBeenCalled();
      expect(eventSpy.mock.calls[0][0].detail.historyId).toBe(mockHistoryItem.id);

      window.removeEventListener('importCompleted', eventSpy);
    });
  });

  describe('torrent selection warnings', () => {
    it('should warn when selected torrent does not match history item', async () => {
      const mismatchTorrent = {
        ...mockTorrent,
        mam_id: '999999',
        name: 'Different Book'
      };

      global.fetch = vi.fn((url) => {
        if (url === '/qb/torrents') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ items: [mismatchTorrent] })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await nextTick();

      const statusEl = getBySelector(expanderRow, '.imp-status');
      expect(statusEl.innerHTML).toContain('does not match');
    });

    it('should warn when torrent path is invalid', async () => {
      const invalidPathTorrent = {
        ...mockTorrent,
        content_path: '/invalid/path'
      };

      global.fetch = vi.fn((url) => {
        if (url === '/qb/torrents') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ items: [invalidPathTorrent] })
          });
        }
        return mockFetchResponses()(url);
      });

      await importForm.render();
      await nextTick();

      const select = getBySelector(expanderRow, '.imp-torrent');
      selectOption(select, invalidPathTorrent.hash);

      await nextTick();

      const statusEl = getBySelector(expanderRow, '.imp-status');
      expect(statusEl.innerHTML).toContain('hardlink may fail');
    });
  });
});
