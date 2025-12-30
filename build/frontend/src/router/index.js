/**
 * Vue Router Configuration
 * Defines all routes for the MAM Audiobook Finder app
 */

import { createRouter, createWebHistory } from 'vue-router'

// Lazy load views for code splitting
const DiscoverView = () => import('@views/DiscoverView.vue')
const HistoryView = () => import('@views/HistoryView.vue')
const LogsView = () => import('@views/LogsView.vue')
const SeriesView = () => import('@views/SeriesView.vue')
const LibraryView = () => import('@views/LibraryView.vue')
const SettingsView = () => import('@views/SettingsView.vue')

const routes = [
  {
    path: '/',
    name: 'discover',
    component: DiscoverView,
    meta: { title: 'Discover - Audiobook Finder' }
  },
  {
    path: '/history',
    name: 'history',
    component: HistoryView,
    meta: { title: 'History - Audiobook Finder' }
  },
  // Legacy route redirects for backwards compatibility
  {
    path: '/search',
    redirect: to => ({ path: '/', query: { ...to.query, view: 'table' } })
  },
  {
    path: '/showcase',
    redirect: to => ({ path: '/', query: { ...to.query, view: 'cards' } })
  },
  {
    path: '/logs',
    name: 'logs',
    component: LogsView,
    meta: { title: 'Logs - Audiobook Finder' }
  },
  {
    path: '/series',
    name: 'series',
    component: SeriesView,
    meta: { title: 'Series - Audiobook Finder' }
  },
  {
    path: '/library',
    name: 'library',
    component: LibraryView,
    meta: { title: 'Library - Audiobook Finder' }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { title: 'Settings - Audiobook Finder' }
  },
  // Catch-all route for unmatched paths - redirect to home
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Update document title on route change
router.afterEach((to) => {
  document.title = to.meta.title || 'Audiobook Finder'
})

export default router
