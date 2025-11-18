<template>
  <n-layout-header
    bordered
    class="nav-header"
    :style="{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      backdropFilter: 'blur(10px)',
      backgroundColor: 'rgba(26, 26, 26, 0.95)',
      borderBottom: '2px solid var(--accent-maroon)',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
    }"
  >
    <n-space align="center" justify="space-between" :size="12" :wrap="false">
      <!-- Brand/Logo Section -->
      <n-thing class="brand-section">
        <template #avatar>
          <span class="brand-icon">📚</span>
        </template>
        <template #header>
          <span class="brand-title">MAM Finder</span>
        </template>
      </n-thing>

      <!-- Navigation Pills -->
      <n-space :size="8" :wrap="false" class="nav-pills">
        <n-button
          text
          tag="a"
          @click.prevent="navigateTo('/')"
          :type="currentRoute === 'search' ? 'primary' : 'default'"
          :class="{ 'nav-active': currentRoute === 'search' }"
          class="nav-pill"
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
          class="nav-pill"
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
          class="nav-pill"
        >
          <template #icon>
            <span>🎭</span>
          </template>
          Showcase
        </n-button>

        <n-button
          text
          tag="a"
          @click.prevent="navigateTo('/logs')"
          :type="currentRoute === 'logs' ? 'primary' : 'default'"
          :class="{ 'nav-active': currentRoute === 'logs' }"
          class="nav-pill"
        >
          <template #icon>
            <span>📄</span>
          </template>
          Logs
        </n-button>
      </n-space>

      <!-- Health Indicator with Badge -->
      <n-popover trigger="hover" placement="bottom-end">
        <template #trigger>
          <n-badge
            :value="health.ok ? '✓' : '✗'"
            :type="health.checking ? 'default' : health.ok ? 'success' : 'error'"
            :color="health.checking ? '#888888' : health.ok ? '#2d7a3e' : '#a83232'"
            :processing="health.checking"
            show-zero
          >
            <n-button text class="health-button">
              <template #icon>
                <span class="health-icon">💊</span>
              </template>
              Status
            </n-button>
          </n-badge>
        </template>
        <div class="health-popover">
          <strong>Application Health</strong>
          <p>{{ healthText }}</p>
        </div>
      </n-popover>
    </n-space>
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
.nav-header {
  padding: 0.5rem 1rem;
  margin: calc(-1 * var(--spacing-xl)) calc(-1 * var(--spacing-xl)) var(--spacing-lg);
}

/* Brand Section */
.brand-section {
  min-width: 140px;
}

.brand-icon {
  font-size: 1.5rem;
}

.brand-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

/* Navigation Pills */
.nav-pills {
  flex: 1;
  justify-content: center;
}

.nav-pill {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  font-weight: 500;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  background: transparent;
}

.nav-pill:hover {
  background: var(--bg-panel-hover) !important;
  border-color: var(--accent-maroon);
  color: var(--text-primary);
}

.nav-pill.nav-active {
  background: var(--accent-maroon) !important;
  border-color: var(--accent-maroon-light);
  color: white !important;
}

/* Health Button */
.health-button {
  font-size: 0.85rem;
}

.health-icon {
  font-size: 1.1rem;
}

.health-popover {
  text-align: center;
}

.health-popover strong {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.health-popover p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .nav-header {
    padding: 0.4rem 0.6rem;
  }

  .brand-section {
    min-width: auto;
  }

  .brand-title {
    display: none;
  }

  .nav-pill {
    padding: 0.4rem 0.6rem;
    font-size: 0.85rem;
  }

  .nav-pill :deep(.n-button__content) {
    gap: 4px;
  }
}
</style>
