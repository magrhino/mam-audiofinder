<template>
  <n-layout-header bordered class="nav-header glass-header">
    <div class="nav-container">
      <!-- Brand/Logo Section -->
      <div class="nav-section nav-left">
        <n-thing class="brand-section glass-brand">
          <template #avatar>
            <img
              :src="brandLogoSrc"
              alt="Shelfarr logo"
              class="brand-logo"
              @error="handleLogoError"
            />
          </template>
          <template #header>
            <span v-if="!isMobile" class="brand-title">Shelfarr</span>
          </template>
        </n-thing>
      </div>

      <!-- Navigation Pills (Centered) -->
      <div class="nav-section nav-center">
        <n-flex class="nav-pills">
          <router-link
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            custom
            v-slot="{ navigate, isActive }"
          >
            <n-button
              text
              @click="navigate"
              :class="{ 'nav-active': isActive }"
              class="nav-pill glass-pill"
            >
              <template #icon>
                <span>{{ link.icon }}</span>
              </template>
              <span v-if="!isMobile" class="nav-pill-text">{{ link.label }}</span>
            </n-button>
          </router-link>
        </n-flex>
      </div>

      <!-- Health Indicator -->
      <div class="nav-section nav-right">
        <n-popover trigger="hover" placement="bottom-end">
          <template #trigger>
            <div class="health-indicator glass-health" :class="healthClass">
              <span v-if="health.checking" class="health-spinner"></span>
              <span v-else-if="health.ok" class="health-dot"></span>
              <span v-else class="health-x">✗</span>
              <span v-if="!isMobile" class="health-label">{{ healthStatusText }}</span>
            </div>
          </template>
          <div class="health-popover glass-popover">
            <strong>Application Health</strong>
            <p>{{ healthText }}</p>
          </div>
        </n-popover>
      </div>
    </div>
  </n-layout-header>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useBreakpoints } from '@vueuse/core'
import {
  NLayoutHeader,
  NFlex,
  NButton,
  NThing,
  NPopover
} from 'naive-ui'

const props = defineProps({
  health: {
    type: Object,
    required: true,
    validator: (value) => {
      return typeof value.ok === 'boolean' && typeof value.checking === 'boolean'
    }
  }
})

// Responsive breakpoints matching SearchView pattern
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Check if mobile (< 768px)
const isMobile = computed(() => !breakpoints.greater('tablet').value)

// Navigation links configuration
const navLinks = [
  { path: '/', icon: '🔍', label: 'Search' },
  { path: '/history', icon: '📋', label: 'History' },
  { path: '/showcase', icon: '🎭', label: 'Showcase' },
  { path: '/series', icon: '📚', label: 'Series' },
  { path: '/logs', icon: '📄', label: 'Logs' }
]

const brandLogoPrimary = '/static/favicon.svg'
const brandLogoFallback = '/static/icon.png'
const brandLogoSrc = ref(brandLogoPrimary)

const handleLogoError = () => {
  if (brandLogoSrc.value !== brandLogoFallback) {
    brandLogoSrc.value = brandLogoFallback
  }
}

const healthClass = computed(() => {
  if (props.health.checking) return 'checking'
  return props.health.ok ? 'healthy' : 'unhealthy'
})

const healthStatusText = computed(() => {
  if (props.health.checking) return 'Checking'
  return props.health.ok ? 'Healthy' : 'Error'
})

const healthText = computed(() => {
  if (props.health.checking) return 'Checking system health...'
  return props.health.ok ? 'All systems operational' : 'Service unavailable'
})
</script>

<style scoped>
/* Glassomorphism Header */
.glass-header {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0.5rem 1rem;

  /* Edge-to-edge full width */
  margin-left: calc(-1 * var(--spacing-xl));
  margin-right: calc(-1 * var(--spacing-xl));
  margin-bottom: var(--spacing-lg);
  width: calc(100% + 2 * var(--spacing-xl));

  /* Glass effect */
  background: rgba(0, 0, 0, 0.4) !important;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);

  /* Subtle gradient overlay */
  border-bottom: 1px solid rgba(80, 0, 0, 0.3);
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

/* Three-column centered layout */
.nav-container {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 1rem;
  width: 100%;
  max-width: 100%;
  padding: 0 0.5rem;
}

.nav-section {
  display: flex;
  align-items: center;
}

.nav-left {
  justify-content: flex-start;
  padding-left: 0.5rem;
}

.nav-center {
  justify-content: center;
}

.nav-right {
  justify-content: flex-end;
  padding-right: 0.5rem;
}

/* Brand Section - Glass card */
.glass-brand {
  background: rgba(36, 36, 36, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 0.25rem 0.5rem;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.glass-brand:hover {
  background: rgba(36, 36, 36, 0.5);
  border-color: rgba(80, 0, 0, 0.4);
  box-shadow: 0 2px 8px rgba(80, 0, 0, 0.2);
}

.brand-logo {
  width: 36px;
  height: 36px;
  display: block;
  object-fit: contain;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5));
}

.brand-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

/* Navigation Pills - Glass buttons */
.nav-pills {
  justify-content: center;
}

.glass-pill {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  /* Glass effect for inactive pills */
  background: rgba(42, 42, 42, 0.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.05) !important;
  backdrop-filter: blur(8px);
  color: var(--text-secondary);
  position: relative;
  overflow: hidden;
}

/* Icon-only mobile layout */
.glass-pill:has(.nav-pill-text:not(:empty)) {
  /* Pills with text get normal padding */
  padding: 0.5rem 1rem;
}

.glass-pill:not(:has(.nav-pill-text)) {
  /* Icon-only pills on mobile get square padding */
  padding: 0.5rem;
  min-width: 40px;
  min-height: 40px;
  justify-content: center;
  display: flex;
  align-items: center;
}

.nav-pill-text {
  white-space: nowrap;
}

.glass-pill::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.05),
    transparent
  );
  transition: left 0.5s ease;
}

.glass-pill:hover::before {
  left: 100%;
}

.glass-pill:hover {
  background: rgba(80, 0, 0, 0.2) !important;
  border-color: rgba(80, 0, 0, 0.5) !important;
  color: var(--text-primary);
  box-shadow:
    0 4px 12px rgba(80, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.glass-pill.nav-active {
  background: rgba(80, 0, 0, 0.6) !important;
  border-color: rgba(106, 0, 0, 0.7) !important;
  color: white !important;
  box-shadow:
    0 4px 16px rgba(80, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.15),
    inset 0 -1px 0 rgba(0, 0, 0, 0.3);
}

/* Health Indicator - Glass card with dot/X */
.health-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(42, 42, 42, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 0.4rem 0.8rem;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  cursor: pointer;
  min-height: 40px;
}

.health-indicator:hover {
  background: rgba(42, 42, 42, 0.5);
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.health-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* Health Dot - Green when healthy */
.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2d7a3e;
  box-shadow: 0 0 8px rgba(45, 122, 62, 0.6);
  animation: pulse-green 2s ease-in-out infinite;
}

@keyframes pulse-green {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(0.95);
  }
}

/* Health X - Red when unhealthy */
.health-x {
  font-size: 0.9rem;
  color: #a83232;
  font-weight: bold;
  text-shadow: 0 0 8px rgba(168, 50, 50, 0.6);
  animation: pulse-red 2s ease-in-out infinite;
}

@keyframes pulse-red {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

/* Health Spinner - Gray when checking */
.health-spinner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #888888;
  animation: pulse-gray 1.5s ease-in-out infinite;
}

@keyframes pulse-gray {
  0%, 100% {
    opacity: 0.5;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Glass Popover */
.glass-popover {
  text-align: center;
  background: rgba(42, 42, 42, 0.95);
  backdrop-filter: blur(20px);
  padding: 0.5rem;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-popover strong {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.glass-popover p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .glass-header {
    padding: 0.4rem 0;
  }

  .nav-container {
    gap: 0.5rem;
    padding: 0 0.25rem;
  }

  .nav-left {
    padding-left: 0.25rem;
  }

  .nav-right {
    padding-right: 0.25rem;
  }

  .glass-pill :deep(.n-button__content) {
    gap: 4px;
  }

  /* Match health indicator to nav pill sizing on mobile */
  .health-indicator {
    padding: 0.5rem;
    min-width: 40px;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .glass-header {
    padding: 0.3rem 0;
  }

  .nav-container {
    gap: 0.25rem;
    padding: 0 0.15rem;
  }

  .nav-left {
    padding-left: 0.15rem;
  }

  .nav-right {
    padding-right: 0.15rem;
  }

  .glass-brand {
    padding: 0.25rem;
  }

  .brand-logo {
    width: 28px;
    height: 28px;
  }
}
</style>
