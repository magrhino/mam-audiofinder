/**
 * Vue Router Configuration
 * Defines all routes for the MAM Audiobook Finder app
 */

import { createRouter, createWebHistory } from 'vue-router'

// Lazy load views for code splitting
const SearchView = () => import('@views/SearchView.vue')
const HistoryView = () => import('@views/HistoryView.vue')
const ShowcaseView = () => import('@views/ShowcaseView.vue')
const LogsView = () => import('@views/LogsView.vue')
const SeriesView = () => import('@views/SeriesView.vue')

const routes = [
  {
    path: '/',
    name: 'search',
    component: SearchView,
    meta: { title: 'Search - Audiobook Finder' }
  },
  {
    path: '/history',
    name: 'history',
    component: HistoryView,
    meta: { title: 'History - Audiobook Finder' }
  },
  {
    path: '/showcase',
    name: 'showcase',
    component: ShowcaseView,
    meta: { title: 'Showcase - Audiobook Finder' }
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
