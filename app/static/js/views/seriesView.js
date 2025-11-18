/**
 * SeriesView module - Handles Hardcover series discovery and book browsing
 */

import { api } from '../core/api.js';
import { escapeHtml } from '../core/utils.js';
import { createBookCard } from '../components/cardHelper.js';
import { showToast } from '../components/toast.js';
import {
  setSeriesSearchButtonSuccess,
  setSeriesSearchButtonError
} from '../components/seriesSearchButton.js';

/**
 * SeriesView handles series search and book detail display
 */
export class SeriesView {
  constructor(elements, router) {
    this.elements = elements;
    this.router = router;
    this.currentSeriesResults = [];
    this.currentCardData = null; // Track originating card for event responses

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

    // Back button
    if (this.elements.backBtn) {
      this.elements.backBtn.addEventListener('click', () => {
        this.showSeriesTable();
      });
    }
  }

  /**
   * Search for series
   * @param {Object} cardData - Optional card data from series-search event
   */
  async searchSeries(cardData = null) {
    const title = (this.elements.titleInput?.value || '').trim();
    const author = (this.elements.authorInput?.value || '').trim();
    const limit = parseInt(this.elements.limitSelect?.value || '20', 10);

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
    this.elements.detailGrid.innerHTML = '';

    try {
      const data = await api.getSeriesBooks(seriesId);
      const books = data.books || [];

      if (!books.length) {
        this.elements.status.textContent = 'No books found in this series.';
        return;
      }

      // Update detail title
      this.elements.detailTitle.textContent = `${seriesName} (${books.length} books)`;

      // Render book cards (pass series author from API response)
      const seriesAuthor = data.author_name || '';
      await this.renderBookCards(books, seriesAuthor);

      // Show detail view, hide table
      this.showDetailView();

      // Update URL with series details
      const currentParams = this.router.getStateFromURL();
      this.router.updateURL({
        ...currentParams,
        series_id: seriesId.toString(),
        series_name: seriesName
      }, false);

      this.elements.status.textContent = '';

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
   * Render book cards using CardHelper
   * @param {Array} books - Book list (strings or objects)
   * @param {string} seriesAuthor - Series author name
   */
  async renderBookCards(books, seriesAuthor) {
    this.elements.detailGrid.innerHTML = '';

    // If books are objects, sort by position; if strings, keep order
    const sortedBooks = books[0] && typeof books[0] === 'object'
      ? books.sort((a, b) => (a.position || 0) - (b.position || 0))
      : books; // Keep original order for string titles

    for (let i = 0; i < sortedBooks.length; i++) {
      const card = await this.createBookCardWithMAM(sortedBooks[i], i, seriesAuthor);
      this.elements.detailGrid.appendChild(card);
    }
  }

  /**
   * Create a book card with MAM matching
   * @param {Object|string} book - Hardcover book data (object or string title)
   * @param {number} index - Book index for position
   * @param {string} seriesAuthor - Series author name for fallback
   * @returns {Promise<HTMLElement>}
   */
  async createBookCardWithMAM(book, index, seriesAuthor) {
    // Handle both string (title only) and object formats
    let title, author, coverUrl, position, description;

    if (typeof book === 'string') {
      // Hardcover API returns array of title strings
      title = book;
      author = seriesAuthor || 'Unknown Author';
      coverUrl = '';
      position = index + 1; // Use array index as position
      description = '';
    } else {
      // Full book object (if API returns this format in future)
      title = book.title || 'Unknown Title';
      const authors = book.authors || [];
      author = authors.length > 0 ? authors.join(', ') : (seriesAuthor || 'Unknown Author');
      coverUrl = book.cover_url || '';
      position = book.position || (index + 1);
      description = book.description || '';
    }

    // Search MAM for this book to check if available
    let mamMatch = null;
    let inLibrary = false;

    try {
      const searchResult = await api.search({
        tor: { text: `${title} ${author}`, sortType: 'default' },
        perpage: 1
      });

      if (searchResult.results && searchResult.results.length > 0) {
        mamMatch = searchResult.results[0];
        inLibrary = mamMatch.in_abs_library || false;
      }
    } catch (error) {
      console.warn(`Could not search MAM for "${title}":`, error);
    }

    // Create card using cardHelper
    const card = createBookCard({
      title: `#${position} - ${title}`,
      author: author,
      coverUrl: coverUrl,
      mamId: mamMatch ? mamMatch.id : '',
      formats: mamMatch ? [mamMatch.filetype] : [],
      versionsCount: 1,
      inLibrary: inLibrary,
      description: description,
      showDescription: !!description,
      cardClass: 'showcase-card',
      onClick: mamMatch ? () => this.handleCardClick(mamMatch) : null
    });

    return card;
  }

  /**
   * Handle card click (for adding to qBittorrent)
   * @param {Object} item - MAM item data
   */
  handleCardClick(item) {
    // Show import form or add to queue
    console.log('Card clicked:', item);
    // TODO: Implement add-to-queue functionality
  }

  /**
   * Show series table, hide detail view
   */
  showSeriesTable() {
    this.elements.tableContainer.style.display = '';
    this.elements.detailContainer.style.display = 'none';
    this.elements.status.textContent = `Found ${this.currentSeriesResults.length} series`;

    // Remove series details from URL, keep search params
    const currentParams = this.router.getStateFromURL();
    const { series_id, series_name, ...searchParams } = currentParams;
    this.router.updateURL(searchParams, false);
  }

  /**
   * Show detail view, hide series table
   */
  showDetailView() {
    this.elements.tableContainer.style.display = 'none';
    this.elements.detailContainer.style.display = '';
  }
}
