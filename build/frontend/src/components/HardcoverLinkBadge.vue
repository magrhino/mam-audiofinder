<script setup>
import { computed } from 'vue'
import { NTooltip, NTag } from 'naive-ui'

const props = defineProps({
  linked: {
    type: Boolean,
    default: false,
  },
  confidence: {
    type: Number,
    default: 0,
  },
  seriesName: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['edit'])

// Determine link status
const status = computed(() => {
  if (!props.linked) return 'unlinked'
  if (props.confidence >= 1.0) return 'manual'
  if (props.confidence >= 0.7) return 'linked'
  return 'verify'
})

const statusConfig = computed(() => {
  switch (status.value) {
    case 'manual':
      return {
        icon: '🔗',
        label: 'Linked',
        type: 'success',
        tooltip: props.seriesName
          ? `Manually linked to "${props.seriesName}"`
          : 'Manually linked to Hardcover',
      }
    case 'linked':
      return {
        icon: '⚡',
        label: 'Auto',
        type: 'info',
        tooltip: props.seriesName
          ? `Auto-linked to "${props.seriesName}" (${Math.round(props.confidence * 100)}% confidence)`
          : `Auto-linked (${Math.round(props.confidence * 100)}% confidence)`,
      }
    case 'verify':
      return {
        icon: '⚠️',
        label: 'Verify',
        type: 'warning',
        tooltip: props.seriesName
          ? `Low confidence match to "${props.seriesName}" - click to verify`
          : 'Low confidence match - click to verify',
      }
    default:
      return {
        icon: '🔗',
        label: 'Link',
        type: 'default',
        tooltip: 'Not linked to Hardcover - click to search',
      }
  }
})

function handleClick() {
  emit('edit')
}
</script>

<template>
  <NTooltip trigger="hover">
    <template #trigger>
      <NTag
        :type="statusConfig.type"
        size="small"
        round
        :bordered="false"
        class="link-badge"
        :class="`badge-${status}`"
        @click="handleClick"
      >
        <span class="badge-icon">{{ statusConfig.icon }}</span>
        <span class="badge-label">{{ statusConfig.label }}</span>
      </NTag>
    </template>
    {{ statusConfig.tooltip }}
  </NTooltip>
</template>

<style scoped>
.link-badge {
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.link-badge:hover {
  transform: translateY(-1px);
  filter: brightness(1.1);
}

.badge-icon {
  margin-right: 4px;
}

.badge-label {
  font-weight: 500;
}

/* Status-specific styles */
.badge-manual {
  background: rgba(45, 122, 62, 0.8) !important;
  border: 1px solid rgba(80, 180, 100, 0.5) !important;
}

.badge-linked {
  background: rgba(70, 100, 160, 0.8) !important;
  border: 1px solid rgba(120, 160, 220, 0.5) !important;
}

.badge-verify {
  background: rgba(180, 140, 50, 0.8) !important;
  border: 1px solid rgba(220, 180, 80, 0.5) !important;
  animation: pulse-attention 2s ease-in-out infinite;
}

.badge-unlinked {
  background: rgba(80, 80, 80, 0.6) !important;
  border: 1px solid rgba(120, 120, 120, 0.4) !important;
}

@keyframes pulse-attention {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>
