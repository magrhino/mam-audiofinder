<template>
  <n-dropdown
    :options="menuOptions"
    @select="handleSelect"
    placement="bottom-end"
    trigger="click"
  >
    <n-button quaternary circle class="gear-button" :class="{ 'is-active': isActive }">
      <template #icon>
        <span class="gear-icon">⚙️</span>
      </template>
    </n-button>
  </n-dropdown>
</template>

<script setup>
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NDropdown, NButton } from 'naive-ui'
import { useAuth } from '@composables/useAuth'

const route = useRoute()
const router = useRouter()
const { requiresAuth, logout, user } = useAuth()

// Check if current route is one of the menu items
const isActive = computed(() => {
  return ['/settings', '/logs'].includes(route.path)
})

// Base menu options
const baseOptions = [
  {
    label: 'Settings',
    key: '/settings',
    icon: () => h('span', { style: { marginRight: '8px' } }, '⚙️')
  },
  {
    label: 'Logs',
    key: '/logs',
    icon: () => h('span', { style: { marginRight: '8px' } }, '📄')
  }
]

// Menu options with conditional logout
const menuOptions = computed(() => {
  if (!requiresAuth.value) {
    return baseOptions
  }

  // Add divider and logout when auth is required
  return [
    ...baseOptions,
    { type: 'divider', key: 'd1' },
    {
      label: user.value?.username ? `Logout (${user.value.username})` : 'Logout',
      key: 'logout',
      icon: () => h('span', { style: { marginRight: '8px' } }, '🚪')
    }
  ]
})

const handleSelect = async (key) => {
  if (key === 'logout') {
    await logout()
    router.push('/login')
    return
  }
  router.push(key)
}
</script>

<style scoped>
.gear-button {
  min-width: 40px;
  min-height: 40px;
  background: rgba(42, 42, 42, 0.3) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: var(--radius-md, 8px) !important;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.gear-button:hover {
  background: rgba(80, 0, 0, 0.2) !important;
  border-color: rgba(80, 0, 0, 0.5) !important;
  box-shadow:
    0 4px 12px rgba(80, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.gear-button.is-active {
  background: rgba(80, 0, 0, 0.6) !important;
  border-color: rgba(106, 0, 0, 0.7) !important;
  box-shadow:
    0 4px 16px rgba(80, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.gear-icon {
  font-size: 16px;
}

/* Dropdown menu styling */
:deep(.n-dropdown-menu) {
  background: rgba(42, 42, 42, 0.95) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

:deep(.n-dropdown-option) {
  transition: all 0.2s ease;
}

:deep(.n-dropdown-option:hover) {
  background: rgba(80, 0, 0, 0.2) !important;
}

:deep(.n-dropdown-option.n-dropdown-option--pending) {
  background: rgba(80, 0, 0, 0.3) !important;
}
</style>
