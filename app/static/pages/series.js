/**
 * Series Page Entry Point
 * Handles series discovery and book browsing functionality
 */

import { Router } from '../js/core/router.js';
import { api } from '../js/core/api.js';
import { SeriesView } from '../js/views/seriesView.js';

/**
 * Series Page class
 */
class SeriesPage {
  constructor() {
    this.router = null;
    this.seriesView = null;
    this.elements = {};
  }

  /**
   * Initialize the series page
   */
  async init() {
    // Collect DOM elements
    this.collectElements();

    // Initialize router
    this.router = new Router();

    // Initialize series view
    this.seriesView = new SeriesView({
      titleInput: this.elements.seriesTitle,
      authorInput: this.elements.seriesAuthor,
      limitSelect: this.elements.seriesLimit,
      searchBtn: this.elements.seriesSearchBtn,
      status: this.elements.seriesStatus,
      tableContainer: this.elements.seriesTableContainer,
      table: this.elements.seriesTable,
      tbody: this.elements.seriesTableBody,
      detailContainer: this.elements.seriesDetailContainer,
      detailTitle: this.elements.seriesDetailTitle,
      detailGrid: this.elements.seriesDetailGrid,
      backBtn: this.elements.backToSeriesTable
    }, this.router);

    // Set up router event handlers
    this.setupRouterHandlers();

    // Set up series-search event listener
    this.setupSeriesSearchListener();

    // Check application health
    await this.checkHealth();

    // Restore state from URL
    await this.restoreStateFromURL();
  }

  /**
   * Collect DOM element references
   */
  collectElements() {
    this.elements = {
      seriesTitle: document.getElementById('seriesTitle'),
      seriesAuthor: document.getElementById('seriesAuthor'),
      seriesLimit: document.getElementById('seriesLimit'),
      seriesSearchBtn: document.getElementById('seriesSearchBtn'),
      seriesStatus: document.getElementById('seriesStatus'),
      seriesTableContainer: document.getElementById('seriesTableContainer'),
      seriesTable: document.getElementById('seriesTable'),
      seriesTableBody: document.getElementById('seriesTableBody'),
      seriesDetailContainer: document.getElementById('seriesDetailContainer'),
      seriesDetailTitle: document.getElementById('seriesDetailTitle'),
      booksTableBody: document.getElementById('booksTableBody'),
      mamResultsContainer: document.getElementById('mamResultsContainer'),
      mamResultsTitle: document.getElementById('mamResultsTitle'),
      mamResultsGrid: document.getElementById('mamResultsGrid'),
      backToSeriesTable: document.getElementById('backToSeriesTable'),
      backToBooks: document.getElementById('backToBooksTable'),
      navHealth: document.getElementById('navHealth')
    };
  }

  /**
   * Set up router event handlers for browser back/forward
   */
  setupRouterHandlers() {
    window.addEventListener('routerStateChange', async (event) => {
      const state = event.detail;

      // Restore form inputs
      if (this.elements.seriesTitle) this.elements.seriesTitle.value = state.q || '';
      if (this.elements.seriesAuthor) this.elements.seriesAuthor.value = state.author || '';
      if (this.elements.seriesLimit) this.elements.seriesLimit.value = state.limit || '20';

      // Check if we need to restore detail view (book details take priority)
      if (state.book_title && state.book_position) {
        // Restore MAM results view (deepest level)
        const position = parseInt(state.book_position, 10);
        await this.seriesView.viewBookTorrents(state.book_title, position);
      } else if (state.series_id && state.series_name) {
        // Restore books table view
        const seriesId = parseInt(state.series_id, 10);
        await this.seriesView.loadSeriesBooks(seriesId, state.series_name);
      } else if (state.q) {
        // Re-run search if query exists (top level)
        await this.seriesView.searchSeries();
      } else {
        // Clear search results if no query
        this.elements.seriesTableContainer.style.display = 'none';
        this.elements.seriesDetailContainer.style.display = 'none';
        this.elements.seriesTableBody.innerHTML = '';
        this.elements.seriesStatus.textContent = '';
      }
    });
  }

  /**
   * Set up listener for series-search events from card buttons
   */
  setupSeriesSearchListener() {
    document.addEventListener('series-search', async (event) => {
      const cardData = event.detail;
      console.log('📖 Series search event received:', cardData);

      // Populate form with card data
      if (this.elements.seriesTitle) {
        this.elements.seriesTitle.value = cardData.title || '';
      }
      if (this.elements.seriesAuthor) {
        this.elements.seriesAuthor.value = cardData.author || '';
      }

      // Run search
      await this.seriesView.searchSeries(cardData);
    });
  }

  /**
   * Check application health status
   */
  async checkHealth() {
    try {
      const health = await api.health();
      this.updateHealthIndicator(health.ok);
    } catch {
      this.updateHealthIndicator(false);
    }
  }

  /**
   * Update health indicator in navigation bar
   * @param {boolean} ok - Health status
   */
  updateHealthIndicator(ok) {
    const healthIndicator = this.elements.navHealth;
    const healthDot = healthIndicator?.querySelector('.health-dot');
    const healthText = healthIndicator?.querySelector('.health-text');

    if (healthIndicator && healthDot && healthText) {
      healthText.textContent = ok ? 'OK' : 'Error';
      if (ok) {
        healthIndicator.classList.add('ok');
        healthIndicator.classList.remove('error');
      } else {
        healthIndicator.classList.add('error');
        healthIndicator.classList.remove('ok');
      }
    }
  }

  /**
   * Restore application state from URL parameters
   */
  async restoreStateFromURL() {
    const state = this.router.getStateFromURL();

    // Pre-populate form inputs from URL
    if (state.q && this.elements.seriesTitle) {
      this.elements.seriesTitle.value = state.q;
    }
    if (state.author && this.elements.seriesAuthor) {
      this.elements.seriesAuthor.value = state.author;
    }
    if (state.limit && this.elements.seriesLimit) {
      this.elements.seriesLimit.value = state.limit;
    }

    // Restore deepest level first (book torrents > series books > search results)
    if (state.book_title && state.book_position) {
      // Restore MAM results view (deepest level)
      const position = parseInt(state.book_position, 10);
      // First need to load the series data
      if (state.series_id && state.series_name) {
        const seriesId = parseInt(state.series_id, 10);
        await this.seriesView.loadSeriesBooks(seriesId, state.series_name);
        // Then view the book torrents
        await this.seriesView.viewBookTorrents(state.book_title, position);
      }
    } else if (state.series_id && state.series_name) {
      // Restore books table view
      const seriesId = parseInt(state.series_id, 10);
      await this.seriesView.loadSeriesBooks(seriesId, state.series_name);
    } else if (state.q) {
      // Auto-run search if query parameter exists (top level)
      await this.seriesView.searchSeries();
    } else {
      // Focus title input if no state to restore
      if (this.elements.seriesTitle) this.elements.seriesTitle.focus();
    }
  }
}

// Initialize page when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.seriesPage = new SeriesPage();
    window.seriesPage.init().catch(err => {
      console.error('Failed to initialize series page:', err);
    });
  });
} else {
  // DOM already loaded
  window.seriesPage = new SeriesPage();
  window.seriesPage.init().catch(err => {
    console.error('Failed to initialize series page:', err);
  });
}
