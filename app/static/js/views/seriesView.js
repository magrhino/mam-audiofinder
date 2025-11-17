/**
 * SeriesView module - Handles Hardcover series discovery and book browsing
 * Uses table-first layout per Phase 3 requirements
 */

import { api } from '../core/api.js';
import { escapeHtml } from '../core/utils.js';
import { showToast } from '../components/toast.js';
import {
  setSeriesSearchButtonSuccess,
  setSeriesSearchButtonError
} from '../components/seriesSearchButton.js';
import { addLibraryIndicator } from '../components/libraryIndicator.js';

/**
 * SeriesView handles series search and book detail display
 */
export class SeriesView {
  constructor(elements, router) {
    this.elements = elements;
    this.router = router;
    this.currentSeriesResults = [];
    this.currentSeriesData = null; // Current series metadata
    this.currentBooks = [];       // Current books list
    this.currentCardData = null;  // Track originating card for event responses

    this.bindEvents();
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    // Search button click
    if (this.elements.searchBtn) {
      this.elements.searchBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.searchSeries();
      });
    }

    // Enter key in inputs
    [this.elements.titleInput, this.elements.authorInput].forEach(input => {
      if (input) {
        input.addEventListener('keypress', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            this.searchSeries();
          }
        });
      }
    });

    // Back to series table button
    if (this.elements.backBtn) {
      this.elements.backBtn.addEventListener('click', () => {
        this.showSeriesTable();
      });
    }

    // Back to books table button
    if (this.elements.backToBooks) {
      this.elements.backToBooks.addEventListener('click', () => {
        this.showBooksTable();
      });
    }
  }

  /**
   * Validate and coerce limit to allowed values
   * @param {number} limit - Requested limit
   * @returns {number} Validated limit
   */
  validateLimit(limit) {
    const ALLOWED_LIMITS = [5, 10, 20, 30, 40, 50];
    if (ALLOWED_LIMITS.includes(limit)) {
      return limit;
    }
    // Coerce to nearest allowed value
    const nearest = ALLOWED_LIMITS.reduce((prev, curr) =>
      Math.abs(curr - limit) < Math.abs(prev - limit) ? curr : prev
    );
    console.warn(`Coerced limit ${limit} → ${nearest}`);
    return nearest;
  }

  /**
   * Search for series
   * @param {Object} cardData - Optional card data from series-search event
   */
  async searchSeries(cardData = null) {
    const title = (this.elements.titleInput?.value || '').trim();
    const author = (this.elements.authorInput?.value || '').trim();
    const limit = this.validateLimit(parseInt(this.elements.limitSelect?.value || '20', 10));

    if (!title) {
      this.elements.status.textContent = 'Please enter a book title.';
      return;
    }

    // Store card data if provided (from series-search event)
    this.currentCardData = cardData;

    this.elements.status.textContent = 'Searching for series...';
    this.elements.tableContainer.style.display = 'none';
    this.elements.detailContainer.style.display = 'none';
    this.elements.tbody.innerHTML = '';

    try {
      const data = await api.searchSeries({
        title,
        author,
        limit
      });

      this.currentSeriesResults = data.hardcover_series || [];

      if (!this.currentSeriesResults.length) {
        this.elements.status.textContent = 'No series found.';

        // Update card button if this was from a card click
        if (cardData?.cardGuid) {
          const button = document.querySelector(`[data-card-guid="${cardData.cardGuid}"] .series-search-btn`);
          setSeriesSearchButtonError(button, 'No series');
        }

        return;
      }

      this.renderSeriesTable(this.currentSeriesResults);

      // Update URL with search parameters
      this.router.updateURL({
        q: title,
        author: author,
        limit: limit.toString()
      }, true);

      // Show table
      this.elements.tableContainer.style.display = '';
      this.elements.status.textContent = `Found ${this.currentSeriesResults.length} series`;

      // Update card button if this was from a card click
      if (cardData?.cardGuid) {
        const button = document.querySelector(`[data-card-guid="${cardData.cardGuid}"] .series-search-btn`);
        setSeriesSearchButtonSuccess(button, this.currentSeriesResults.length);
      }

    } catch (error) {
      console.error('Series search failed:', error);

      // Check for rate limit errors
      if (error.message.includes('429') || error.message.includes('503')) {
        showToast('Hardcover rate limit reached. Please try again in 30 seconds.', 'warning');
        this.elements.status.textContent = 'Rate limit reached - try again soon';
      } else {
        showToast(`Series search failed: ${error.message}`, 'error');
        this.elements.status.textContent = 'Search failed.';
      }

      // Update card button if this was from a card click
      if (cardData?.cardGuid) {
        const button = document.querySelector(`[data-card-guid="${cardData.cardGuid}"] .series-search-btn`);
        setSeriesSearchButtonError(button, 'Failed');
      }
    }
  }

  /**
   * Render series results table
   * @param {Array} series - Series results
   */
  renderSeriesTable(series) {
    this.elements.tbody.innerHTML = '';

    series.forEach((item, idx) => {
      const tr = this.createSeriesRow(item, idx);
      this.elements.tbody.appendChild(tr);
    });
  }

  /**
   * Create a series table row
   * @param {Object} item - Series item
   * @param {number} idx - Row index
   * @returns {HTMLTableRowElement}
   */
  createSeriesRow(item, idx) {
    const tr = document.createElement('tr');
    tr.dataset.seriesId = item.series_id;
    tr.style.cursor = 'pointer';

    // Highlight if this is the originating series (matching by name)
    if (this.currentCardData && item.series_name) {
      const cardTitle = this.currentCardData.normalizedTitle || this.currentCardData.title || '';
      const seriesName = item.series_name.toLowerCase();
      if (cardTitle.toLowerCase().includes(seriesName) || seriesName.includes(cardTitle.toLowerCase())) {
        tr.classList.add('highlighted-row');
      }
    }

    // Series name
    const tdSeries = document.createElement('td');
    tdSeries.innerHTML = escapeHtml(item.series_name || 'Unknown Series');
    tr.appendChild(tdSeries);

    // Author
    const tdAuthor = document.createElement('td');
    tdAuthor.innerHTML = escapeHtml(item.author_name || 'Unknown');
    tr.appendChild(tdAuthor);

    // Book count
    const tdBooks = document.createElement('td');
    tdBooks.className = 'center';
    tdBooks.textContent = item.book_count || '0';
    tr.appendChild(tdBooks);

    // Readers count
    const tdReaders = document.createElement('td');
    tdReaders.className = 'center';
    tdReaders.textContent = item.readers_count ? item.readers_count.toLocaleString() : '0';
    tr.appendChild(tdReaders);

    // Action button
    const tdAction = document.createElement('td');
    tdAction.className = 'center';
    const btn = document.createElement('button');
    btn.className = 'primary small';
    btn.textContent = 'View Books';
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.loadSeriesBooks(item.series_id, item.series_name);
    });
    tdAction.appendChild(btn);
    tr.appendChild(tdAction);

    // Row click handler
    tr.addEventListener('click', () => {
      this.loadSeriesBooks(item.series_id, item.series_name);
    });

    return tr;
  }

  /**
   * Load books for a specific series
   * @param {number} seriesId - Series ID
   * @param {string} seriesName - Series name
   */
  async loadSeriesBooks(seriesId, seriesName) {
    this.elements.status.textContent = `Loading books for ${seriesName}...`;
    this.elements.booksTableBody.innerHTML = '';

    try {
      const data = await api.getSeriesBooks(seriesId);
      const books = data.books || [];

      if (!books.length) {
        this.elements.status.textContent = 'No books found in this series.';
        showToast('No books found in this series', 'warning');
        return;
      }

      // Store series data and books
      this.currentSeriesData = {
        series_id: seriesId,
        series_name: seriesName,
        author_name: data.author_name || ''
      };
      this.currentBooks = books;

      // Update detail title
      this.elements.detailTitle.textContent = `${seriesName} (${books.length} books)`;

      // Render book table
      this.renderBooksTable(books);

      // Show detail view, hide series table
      this.showBooksTable();

      // Update URL with series details
      const currentParams = this.router.getStateFromURL();
      this.router.updateURL({
        ...currentParams,
        series_id: seriesId.toString(),
        series_name: seriesName
      }, false);

      this.elements.status.textContent = '';
      showToast(`Loaded ${books.length} books from ${seriesName}`, 'success');

    } catch (error) {
      console.error('Failed to load series books:', error);

      // Check for rate limit errors
      if (error.message.includes('429') || error.message.includes('503')) {
        showToast('Hardcover rate limit reached. Please try again in 30 seconds.', 'warning');
        this.elements.status.textContent = 'Rate limit reached - try again soon';
      } else {
        showToast(`Failed to load books: ${error.message}`, 'error');
        this.elements.status.textContent = 'Failed to load books.';
      }
    }
  }

  /**
   * Render books table (table-first layout per Phase 3)
   * @param {Array} books - Book list (strings or objects)
   */
  renderBooksTable(books) {
    this.elements.booksTableBody.innerHTML = '';

    // Books are returned as simple string array from Hardcover API
    books.forEach((book, index) => {
      const tr = this.createBookRow(book, index + 1);
      this.elements.booksTableBody.appendChild(tr);
    });
  }

  /**
   * Create a book table row
   * @param {string} bookTitle - Book title (Hardcover returns strings)
   * @param {number} position - Book position in series
   * @returns {HTMLTableRowElement}
   */
  createBookRow(bookTitle, position) {
    const tr = document.createElement('tr');

    // Position
    const tdPosition = document.createElement('td');
    tdPosition.className = 'center';
    tdPosition.textContent = position;
    tr.appendChild(tdPosition);

    // Title
    const tdTitle = document.createElement('td');
    tdTitle.textContent = bookTitle;
    tr.appendChild(tdTitle);

    // Year (not available from current Hardcover API, placeholder)
    const tdYear = document.createElement('td');
    tdYear.textContent = '—';
    tdYear.className = 'muted';
    tr.appendChild(tdYear);

    // Action button
    const tdAction = document.createElement('td');
    tdAction.className = 'center';
    const btn = document.createElement('button');
    btn.className = 'primary small';
    btn.textContent = 'View Torrents';
    btn.addEventListener('click', () => {
      this.viewBookTorrents(bookTitle, position);
    });
    tdAction.appendChild(btn);
    tr.appendChild(tdAction);

    return tr;
  }

  /**
   * View MAM torrents for a specific book
   * @param {string} bookTitle - Book title
   * @param {number} position - Book position
   */
  async viewBookTorrents(bookTitle, position) {
    const searchQuery = `${bookTitle} ${this.currentSeriesData.author_name}`;
    const limit = this.validateLimit(parseInt(this.elements.limitSelect?.value || '20', 10));

    this.elements.status.textContent = `Searching MAM for "${bookTitle}"...`;

    try {
      // Search MAM using the perpage limit from the selector
      const searchResult = await api.search({
        tor: { text: searchQuery, sortType: 'default' },
        perpage: limit
      });

      const results = searchResult.results || [];

      if (!results.length) {
        showToast(`No torrents found for "${bookTitle}"`, 'warning');
        this.elements.status.textContent = 'No torrents found';
        return;
      }

      // Group results like showcase does (by normalized title)
      const grouped = this.groupMAMResults(results);

      // Update MAM results title
      this.elements.mamResultsTitle.textContent = `#${position} - ${bookTitle} (${results.length} torrents)`;

      // Render grouped results
      await this.renderGroupedMAMResults(grouped);

      // Show MAM results view
      this.showMAMResults();

      // Update URL
      const currentParams = this.router.getStateFromURL();
      this.router.updateURL({
        ...currentParams,
        book_title: bookTitle,
        book_position: position.toString()
      }, false);

      this.elements.status.textContent = '';
      showToast(`Found ${results.length} torrents for "${bookTitle}"`, 'success');

    } catch (error) {
      console.error('Failed to search MAM:', error);
      showToast(`Failed to search MAM: ${error.message}`, 'error');
      this.elements.status.textContent = 'Search failed';
    }
  }

  /**
   * Group MAM results by normalized title (reuse showcase logic)
   * @param {Array} results - MAM search results
   * @returns {Array} Grouped results
   */
  groupMAMResults(results) {
    const groups = {};

    results.forEach(item => {
      const normalizedTitle = this.normalizeTitle(item.title || '');
      if (!groups[normalizedTitle]) {
        groups[normalizedTitle] = {
          normalized_title: normalizedTitle,
          display_title: item.title,
          display_author: item.author,
          versions: []
        };
      }
      groups[normalizedTitle].versions.push(item);
    });

    return Object.values(groups);
  }

  /**
   * Normalize title for grouping
   * @param {string} title - Title to normalize
   * @returns {string} Normalized title
   */
  normalizeTitle(title) {
    return title
      .toLowerCase()
      .replace(/^(the|a|an)\s+/i, '')
      .replace(/[^\w\s]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * Render grouped MAM results (showcase-style cards)
   * @param {Array} groups - Grouped results
   */
  async renderGroupedMAMResults(groups) {
    this.elements.mamResultsGrid.innerHTML = '';

    for (const group of groups) {
      const card = await this.createGroupedCard(group);
      this.elements.mamResultsGrid.appendChild(card);
    }
  }

  /**
   * Create a grouped card (simplified showcase card)
   * @param {Object} group - Grouped MAM results
   * @returns {HTMLElement}
   */
  async createGroupedCard(group) {
    const card = document.createElement('div');
    card.className = 'showcase-card';

    const firstVersion = group.versions[0];

    // Versions badge
    const badge = document.createElement('div');
    badge.className = 'showcase-versions-badge';
    badge.textContent = `${group.versions.length} version${group.versions.length > 1 ? 's' : ''}`;
    card.appendChild(badge);

    // Cover skeleton (will load cover)
    const coverSkeleton = document.createElement('div');
    coverSkeleton.className = 'showcase-cover-skeleton';

    // Add library indicator if in library
    if (firstVersion.in_abs_library) {
      addLibraryIndicator(coverSkeleton, true);
    }

    card.appendChild(coverSkeleton);

    // Load cover asynchronously
    this.loadCoverForCard(coverSkeleton, firstVersion.id, group.display_title, group.display_author);

    // Title
    const titleEl = document.createElement('div');
    titleEl.className = 'showcase-title';
    titleEl.textContent = group.display_title;
    card.appendChild(titleEl);

    // Author
    const authorEl = document.createElement('div');
    authorEl.className = 'showcase-author';
    authorEl.textContent = group.display_author;
    card.appendChild(authorEl);

    // Formats
    const formatsDiv = document.createElement('div');
    formatsDiv.className = 'showcase-formats';
    const uniqueFormats = [...new Set(group.versions.map(v => v.filetype))];
    uniqueFormats.forEach(format => {
      const formatBadge = document.createElement('span');
      formatBadge.className = 'showcase-format-badge';
      formatBadge.textContent = format;
      formatsDiv.appendChild(formatBadge);
    });
    card.appendChild(formatsDiv);

    // Click to expand versions (TODO: implement expansion)
    card.style.cursor = 'pointer';
    card.addEventListener('click', () => {
      // TODO: Expand to show all versions with Add buttons
      console.log('Card clicked:', group);
    });

    return card;
  }

  /**
   * Load cover for a card
   * @param {HTMLElement} skeleton - Skeleton element
   * @param {string} mamId - MAM ID
   * @param {string} title - Title
   * @param {string} author - Author
   */
  async loadCoverForCard(skeleton, mamId, title, author) {
    try {
      const data = await api.fetchCover({
        mam_id: mamId,
        title: title || '',
        author: author || '',
        max_retries: '3'
      });

      if (data.cover_url) {
        const img = document.createElement('img');
        img.className = 'showcase-cover';
        img.src = data.cover_url;
        img.alt = title || 'Cover';
        img.loading = 'lazy';

        img.onload = () => {
          const libraryIndicator = skeleton.querySelector('.in-library-indicator');
          const wrapper = document.createElement('div');
          wrapper.style.position = 'relative';
          wrapper.appendChild(img);
          if (libraryIndicator) {
            wrapper.appendChild(libraryIndicator);
          }
          skeleton.replaceWith(wrapper);
        };

        img.onerror = () => {
          const placeholder = document.createElement('div');
          placeholder.className = 'showcase-cover-placeholder';
          placeholder.textContent = '📚';
          skeleton.replaceWith(placeholder);
        };
      }
    } catch (error) {
      console.error('Failed to load cover:', error);
    }
  }

  /**
   * Show series table, hide other views
   */
  showSeriesTable() {
    this.elements.tableContainer.style.display = '';
    this.elements.detailContainer.style.display = 'none';
    this.elements.mamResultsContainer.style.display = 'none';
    this.elements.status.textContent = `Found ${this.currentSeriesResults.length} series`;

    // Remove series details from URL, keep search params
    const currentParams = this.router.getStateFromURL();
    const { series_id, series_name, book_title, book_position, ...searchParams } = currentParams;
    this.router.updateURL(searchParams, false);
  }

  /**
   * Show books table, hide other views
   */
  showBooksTable() {
    this.elements.tableContainer.style.display = 'none';
    this.elements.detailContainer.style.display = '';
    this.elements.mamResultsContainer.style.display = 'none';

    // Remove book details from URL, keep series params
    const currentParams = this.router.getStateFromURL();
    const { book_title, book_position, ...paramsToKeep } = currentParams;
    this.router.updateURL(paramsToKeep, false);
  }

  /**
   * Show MAM results, hide other views
   */
  showMAMResults() {
    this.elements.tableContainer.style.display = 'none';
    this.elements.detailContainer.style.display = 'none';
    this.elements.mamResultsContainer.style.display = '';
  }
}
