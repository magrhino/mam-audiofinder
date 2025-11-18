/**
 * SearchView module - Handles MAM audiobook search functionality
 */

import { api } from '../core/api.js';
import { escapeHtml, formatSize } from '../core/utils.js';
import { CoverLoader } from '../services/coverLoader.js';
import { addLibraryIndicator } from '../components/libraryIndicator.js';

/**
 * SearchView handles the search form and results display
 */
export class SearchView {
  constructor(elements, router) {
    this.elements = elements;
    this.router = router;
    this.coverLoader = new CoverLoader();

    // Client-side sorting state
    this.currentResults = [];
    this.sortBy = null;
    this.sortDir = 'asc';

    this.bindEvents();
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    if (this.elements.form) {
      this.elements.form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.search();
      });
    }

    // Bind sortable header click handlers
    this.bindSortableHeaders();
  }

  /**
   * Bind click handlers to sortable table headers
   */
  bindSortableHeaders() {
    const table = this.elements.table;
    if (!table) return;

    const headers = table.querySelectorAll('th.sortable');
    headers.forEach(header => {
      header.addEventListener('click', () => {
        const sortKey = header.dataset.sort;
        if (!sortKey) return;

        // Toggle direction if clicking same column, otherwise default to asc
        if (this.sortBy === sortKey) {
          this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
          this.sortBy = sortKey;
          this.sortDir = 'asc';
        }

        // Re-sort and render
        this.sortAndRender();

        // Update URL with sort parameters
        this.updateSortURL();
      });
    });
  }

  /**
   * Perform search and render results
   */
  async search() {
    this.coverLoader.clearRowState();
    const text = (this.elements.q?.value || '').trim();
    const sortType = (this.elements.sort?.value) || 'default';
    const perpage = parseInt(this.elements.perpage?.value || '25', 10);

    this.elements.status.textContent = 'Searching…';
    this.elements.table.style.display = 'none';
    this.elements.tbody.innerHTML = '';

    try {
      const data = await api.search({
        tor: { text, sortType },
        perpage
      });

      const rows = data.results || [];
      if (!rows.length) {
        this.elements.status.textContent = 'No results.';
        return;
      }

      // Store results for client-side sorting
      this.currentResults = rows;

      // Reset client-side sort state on new search
      this.sortBy = null;
      this.sortDir = 'asc';

      this.renderResults(rows);

      // Update URL with search parameters
      this.router.updateURL({
        q: text,
        sort: sortType,
        perpage: perpage.toString(),
        view: ''
      }, true);

      // Show table immediately with skeleton placeholders
      this.elements.table.style.display = '';
      this.elements.status.textContent = `${rows.length} results shown`;

      // Update sort indicators
      this.updateSortIndicators();

    } catch (e) {
      console.error(e);
      this.elements.status.textContent = 'Search failed.';
    }
  }

  /**
   * Render search results
   * @param {Array} rows - Search result items
   */
  renderResults(rows) {
    // Initialize the cover observer
    this.coverLoader.init();

    rows.forEach((item, idx) => {
      const tr = this.createResultRow(item, idx);
      this.elements.tbody.appendChild(tr);
    });
  }

  /**
   * Create a result row element
   * @param {Object} item - Result item data
   * @param {number} idx - Row index
   * @returns {HTMLTableRowElement}
   */
  createResultRow(item, idx) {
    const rowId = `${item.id || 'row'}-${idx}`;
    const rowState = {
      ...item,
      abs_cover_url: item.abs_cover_url || '',
      abs_item_id: item.abs_item_id || ''
    };
    this.coverLoader.setRowState(rowId, rowState);

    const tr = document.createElement('tr');
    const sl = `${item.seeders ?? '-'} / ${item.leechers ?? '-'}`;

    // Create Add button
    const addBtn = this.createAddButton(item, rowState);

    // Torrent details link on MAM
    const detailsURL = item.id ? `https://www.myanonamouse.net/t/${encodeURIComponent(item.id)}` : '';

    // Create cover container with skeleton placeholder
    const coverContainer = this.coverLoader.createCoverContainer({
      mamId: item.id || '',
      title: item.title || '',
      author: item.author_info || '',
      rowId: rowId
    });

    // Add library indicator if item is in ABS library
    if (item.in_abs_library) {
      addLibraryIndicator(coverContainer, true);
    }

    // Create the row structure
    const coverCell = document.createElement('td');
    coverCell.style.padding = '0.25rem';
    coverCell.appendChild(coverContainer);

    tr.innerHTML = `
      <td style="padding: 0.25rem;"></td>
      <td>${escapeHtml(item.title || '')}</td>
      <td>${escapeHtml(item.author_info || '')}</td>
      <td>${escapeHtml(item.narrator_info || '')}</td>
      <td>${escapeHtml(item.format || '')}</td>
      <td class="right">${formatSize(item.size)}</td>
      <td class="right">${sl}</td>
      <td>${escapeHtml(item.added || '')}</td>
      <td class="center">
        ${detailsURL ? `<a href="${detailsURL}" target="_blank" rel="noopener noreferrer" title="Open on MAM">🔗</a>` : ''}
      </td>
      <td></td>
    `;

    // Replace the first cell with our cover cell
    tr.replaceChild(coverCell, tr.firstElementChild);

    // Add the Add button
    tr.lastElementChild.appendChild(addBtn);

    // Observe the cover container for lazy loading
    this.coverLoader.observe(coverContainer);

    return tr;
  }

  /**
   * Create Add to qBittorrent button
   * @param {Object} item - Item data
   * @param {Object} rowState - Row state reference
   * @returns {HTMLButtonElement}
   */
  createAddButton(item, rowState) {
    const addBtn = document.createElement('button');
    addBtn.textContent = 'Add';
    // Enable if we have a direct dl hash OR at least an id
    addBtn.disabled = !(item.dl || item.id);

    addBtn.addEventListener('click', async () => {
      addBtn.disabled = true;
      addBtn.textContent = 'Adding…';
      try {
        await api.addTorrent({
          id: String(rowState.id ?? ''),
          title: rowState.title || '',
          dl: rowState.dl || '',
          author: rowState.author_info || '',
          narrator: rowState.narrator_info || '',
          abs_cover_url: rowState.abs_cover_url || '',
          abs_item_id: rowState.abs_item_id || ''
        });

        addBtn.textContent = 'Added';

        // Notify that history should be reloaded
        window.dispatchEvent(new CustomEvent('torrentAdded'));

      } catch (e) {
        console.error(e);
        addBtn.textContent = 'Error';
        addBtn.disabled = false;
      }
    });

    return addBtn;
  }

  /**
   * Sort current results and re-render
   */
  sortAndRender() {
    if (!this.sortBy || !this.currentResults.length) return;

    const sorted = [...this.currentResults].sort((a, b) => {
      return this.compareItems(a, b, this.sortBy, this.sortDir);
    });

    // Clear and re-render
    this.elements.tbody.innerHTML = '';
    this.coverLoader.clearRowState();
    this.renderResults(sorted);

    // Update sort indicators
    this.updateSortIndicators();
  }

  /**
   * Compare two items for sorting
   * @param {Object} a - First item
   * @param {Object} b - Second item
   * @param {string} sortKey - Key to sort by
   * @param {string} direction - 'asc' or 'desc'
   * @returns {number} Comparison result
   */
  compareItems(a, b, sortKey, direction) {
    let aVal, bVal;

    // Map sort keys to data fields
    switch (sortKey) {
      case 'author':
        aVal = a.author_info || '';
        bVal = b.author_info || '';
        return this.compareStrings(aVal, bVal, direction);

      case 'narrator':
        aVal = a.narrator_info || '';
        bVal = b.narrator_info || '';
        return this.compareStrings(aVal, bVal, direction);

      case 'format':
        aVal = a.format || '';
        bVal = b.format || '';
        return this.compareStrings(aVal, bVal, direction);

      case 'size':
        aVal = a.size || 0;
        bVal = b.size || 0;
        return this.compareNumbers(aVal, bVal, direction);

      case 'seeders':
        aVal = a.seeders ?? 0;
        bVal = b.seeders ?? 0;
        return this.compareNumbers(aVal, bVal, direction);

      case 'uploaded':
        aVal = a.added || '';
        bVal = b.added || '';
        return this.compareDates(aVal, bVal, direction);

      default:
        return 0;
    }
  }

  /**
   * Compare strings (case-insensitive)
   */
  compareStrings(a, b, direction) {
    const result = a.toLowerCase().localeCompare(b.toLowerCase());
    return direction === 'asc' ? result : -result;
  }

  /**
   * Compare numbers
   */
  compareNumbers(a, b, direction) {
    const result = a - b;
    return direction === 'asc' ? result : -result;
  }

  /**
   * Compare dates (as strings for now)
   */
  compareDates(a, b, direction) {
    // For now, treat as strings since format is unknown
    // MAM dates are typically in a sortable format
    const result = a.localeCompare(b);
    return direction === 'asc' ? result : -result;
  }

  /**
   * Update visual indicators for sorted columns
   */
  updateSortIndicators() {
    const table = this.elements.table;
    if (!table) return;

    const headers = table.querySelectorAll('th.sortable');
    headers.forEach(header => {
      const sortKey = header.dataset.sort;

      // Remove all sort classes
      header.classList.remove('sort-active', 'sort-asc', 'sort-desc');

      // Add classes to active sorted column
      if (sortKey === this.sortBy) {
        header.classList.add('sort-active', `sort-${this.sortDir}`);
      }
    });
  }

  /**
   * Update URL with current sort parameters
   */
  updateSortURL() {
    const params = this.router.getParams();

    if (this.sortBy) {
      params.sortBy = this.sortBy;
      params.sortDir = this.sortDir;
    } else {
      delete params.sortBy;
      delete params.sortDir;
    }

    this.router.updateURL(params, true);
  }

  /**
   * Restore search state from URL parameters
   * @param {Object} state - State object with q, sort, perpage
   */
  restoreState(state) {
    if (state.q) {
      if (this.elements.q) this.elements.q.value = state.q;
    }
    if (state.sort) {
      if (this.elements.sort) this.elements.sort.value = state.sort;
    }
    if (state.perpage) {
      if (this.elements.perpage) this.elements.perpage.value = state.perpage;
    }

    // Restore client-side sort state
    if (state.sortBy) {
      this.sortBy = state.sortBy;
      this.sortDir = state.sortDir || 'asc';
    }

    // Auto-run search if query parameter exists
    if (state.q) {
      this.search().then(() => {
        // Apply client-side sort after search completes
        if (this.sortBy && this.currentResults.length > 0) {
          this.sortAndRender();
        }
      });
    }
  }

  /**
   * Clean up resources
   */
  destroy() {
    this.coverLoader.destroy();
  }
}
