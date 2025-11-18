<template>
  <n-layout-header bordered class="nav-header glass-header">
    <div class="nav-container">
      <!-- Brand/Logo Section (Fixed Width) -->
      <div class="nav-section nav-left">
        <n-thing class="brand-section glass-brand">
          <template #avatar>
            <span class="brand-icon">📚</span>
          </template>
          <template #header>
            <span class="brand-title">MAM Finder</span>
          </template>
        </n-thing>
      </div>

      <!-- Navigation Pills (Centered) -->
      <div class="nav-section nav-center">
        <n-space :size="8" :wrap="false" class="nav-pills">
          <n-button
            text
            tag="a"
            @click.prevent="navigateTo('/')"
            :type="currentRoute === 'search' ? 'primary' : 'default'"
            :class="{ 'nav-active': currentRoute === 'search' }"
            class="nav-pill glass-pill"
          >
            <template #icon>
              <span>🔍</span>
            </template>
            Search
          </n-button>

          <n-button
            text
            tag="a"
            @click.prevent="navigateTo('/history')"
            :type="currentRoute === 'history' ? 'primary' : 'default'"
            :class="{ 'nav-active': currentRoute === 'history' }"
            class="nav-pill glass-pill"
          >
            <template #icon>
              <span>📋</span>
            </template>
            History
          </n-button>

          <n-button
            text
            tag="a"
            @click.prevent="navigateTo('/showcase')"
            :type="currentRoute === 'showcase' ? 'primary' : 'default'"
            :class="{ 'nav-active': currentRoute === 'showcase' }"
            class="nav-pill glass-pill"
          >
            <template #icon>
              <span>🎭</span>
            </template>
            Showcase
          </n-button>

          <n-button
            text
            tag="a"
            @click.prevent="navigateTo('/series')"
            :type="currentRoute === 'series' ? 'primary' : 'default'"
            :class="{ 'nav-active': currentRoute === 'series' }"
            class="nav-pill glass-pill"
          >
            <template #icon>
              <span>📚</span>
            </template>
            Series
          </n-button>

          <n-button
            text
            tag="a"
            @click.prevent="navigateTo('/logs')"
            :type="currentRoute === 'logs' ? 'primary' : 'default'"
            :class="{ 'nav-active': currentRoute === 'logs' }"
            class="nav-pill glass-pill"
          >
            <template #icon>
              <span>📄</span>
            </template>
            Logs
          </n-button>
        </n-space>
      </div>

      <!-- Health Indicator (Fixed Width) -->
      <div class="nav-section nav-right">
        <n-popover trigger="hover" placement="bottom-end">
          <template #trigger>
            <n-badge
              :value="health.ok ? '✓' : '✗'"
              :type="health.checking ? 'default' : health.ok ? 'success' : 'error'"
              :color="health.checking ? 'rgba(136, 136, 136, 0.8)' : health.ok ? 'rgba(45, 122, 62, 0.9)' : 'rgba(168, 50, 50, 0.9)'"
              :processing="health.checking"
              show-zero
            >
              <n-button text class="health-button glass-health">
                <template #icon>
                  <span class="health-icon">💊</span>
                </template>
                Status
              </n-button>
            </n-badge>
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
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NLayoutHeader,
  NSpace,
  NButton,
  NThing,
  NBadge,
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

const route = useRoute()
const router = useRouter()
const currentRoute = computed(() => route.name)

const healthText = computed(() => {
  if (props.health.checking) return 'Checking system health...'
  return props.health.ok ? 'All systems operational' : 'Service unavailable'
})

const navigateTo = (path) => {
  router.push(path)
}
</script>

<style scoped>
/* Glassomorphism Header */
.glass-header {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0.5rem 1rem;
  margin: calc(-1 * var(--spacing-xl)) calc(-1 * var(--spacing-xl)) var(--spacing-lg);

  /* Glass effect */
  background: rgba(26, 26, 26, 0.4) !important;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 100%;
}

.nav-section {
  display: flex;
  align-items: center;
}

.nav-left {
  flex: 0 0 180px;
  justify-content: flex-start;
}

.nav-center {
  flex: 1 1 auto;
  justify-content: center;
}

.nav-right {
  flex: 0 0 180px;
  justify-content: flex-end;
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

.brand-icon {
  font-size: 1.5rem;
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
  display: flex;
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

/* Health Button - Glass indicator */
.glass-health {
  background: rgba(42, 42, 42, 0.3) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: var(--radius-md);
  padding: 0.4rem 0.8rem !important;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  font-size: 0.85rem;
}

.glass-health:hover {
  background: rgba(42, 42, 42, 0.5) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.health-icon {
  font-size: 1.1rem;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5));
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
    padding: 0.4rem 0.6rem;
  }

  .nav-left,
  .nav-right {
    flex: 0 0 auto;
  }

  .nav-center {
    flex: 1 1 auto;
    justify-content: center;
  }

  .brand-title {
    display: none;
  }

  .glass-pill {
    padding: 0.4rem 0.6rem;
    font-size: 0.85rem;
  }

  .glass-pill :deep(.n-button__content) {
    gap: 4px;
  }
}

@media (max-width: 480px) {
  .nav-left {
    flex: 0 0 auto;
    min-width: 0;
  }

  .nav-right {
    flex: 0 0 auto;
  }

  .glass-brand {
    padding: 0.25rem;
  }

  .brand-icon {
    font-size: 1.2rem;
  }
}
</style>
