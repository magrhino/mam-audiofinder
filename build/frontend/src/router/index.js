/**
 * Vue Router Configuration with Authentication Guards
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
const LoginView = () => import('@views/LoginView.vue')

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { title: 'Login - Shelfarr', requiresAuth: false }
  },
  {
    path: '/',
    name: 'discover',
    component: DiscoverView,
    meta: { title: 'Discover - Audiobook Finder', requiresAuth: true }
  },
  {
    path: '/history',
    name: 'history',
    component: HistoryView,
    meta: { title: 'History - Audiobook Finder', requiresAuth: true }
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
    meta: { title: 'Logs - Audiobook Finder', requiresAuth: true }
  },
  {
    path: '/series',
    name: 'series',
    component: SeriesView,
    meta: { title: 'Series - Audiobook Finder', requiresAuth: true }
  },
  {
    path: '/library',
    name: 'library',
    component: LibraryView,
    meta: { title: 'Library - Audiobook Finder', requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { title: 'Settings - Audiobook Finder', requiresAuth: true }
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

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  // Import useAuth dynamically to avoid circular dependency
  const { useAuth } = await import('@composables/useAuth')
  const auth = useAuth()

  // Check auth status if not already checked
  if (!auth.authStatus.value.checked) {
    await auth.checkAuthStatus()
  }

  // Route explicitly marked as not requiring auth (login page)
  if (to.meta.requiresAuth === false) {
    // If already authenticated and going to login, redirect to home
    if (to.name === 'login' && auth.isAuthenticated.value) {
      next('/')
      return
    }
    next()
    return
  }

  // Route requires auth (default or explicit)
  if (auth.requiresAuth.value && !auth.isAuthenticated.value) {
    // Redirect to login with return URL
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
    return
  }

  next()
})

// Update document title on route change
router.afterEach((to) => {
  document.title = to.meta.title || 'Audiobook Finder'
})

export default router
