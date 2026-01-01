<script setup>
import { computed } from 'vue'
import { NTooltip } from 'naive-ui'

const props = defineProps({
  percentage: {
    type: Number,
    default: 100,
  },
  owned: {
    type: Number,
    default: 0,
  },
  total: {
    type: Number,
    default: 0,
  },
  size: {
    type: Number,
    default: 32,
  },
})

// Calculate the stroke dash for the progress ring
const circumference = 2 * Math.PI * 14 // radius = 14
const strokeDasharray = computed(() => {
  const progress = (props.percentage / 100) * circumference
  return `${progress} ${circumference}`
})

// Determine color based on completion percentage
const statusClass = computed(() => {
  if (props.percentage >= 100) return 'ring-complete'
  if (props.percentage >= 50) return 'ring-partial'
  return 'ring-low'
})

const tooltipText = computed(() => {
  if (props.total === 0) return 'No book count data'
  if (props.percentage >= 100) return `Complete: ${props.owned} books`
  return `${props.owned} of ${props.total} books (${props.percentage}%)`
})
</script>

<template>
  <NTooltip trigger="hover">
    <template #trigger>
      <div
        class="completion-ring"
        :class="statusClass"
        :style="{ width: `${size}px`, height: `${size}px` }"
      >
        <svg :viewBox="`0 0 ${size} ${size}`" class="ring-svg">
          <!-- Background ring -->
          <circle
            class="ring-bg"
            :cx="size / 2"
            :cy="size / 2"
            r="14"
            fill="none"
            stroke-width="3"
          />
          <!-- Progress ring -->
          <circle
            class="ring-progress"
            :cx="size / 2"
            :cy="size / 2"
            r="14"
            fill="none"
            stroke-width="3"
            stroke-linecap="round"
            :stroke-dasharray="strokeDasharray"
            :stroke-dashoffset="0"
            transform="rotate(-90, 16, 16)"
          />
        </svg>
        <span class="ring-text">{{ percentage }}%</span>
      </div>
    </template>
    {{ tooltipText }}
  </NTooltip>
</template>

<style scoped>
.completion-ring {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: help;
}

.ring-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  stroke: rgba(255, 255, 255, 0.1);
}

.ring-progress {
  transition: stroke-dasharray 0.6s ease-in-out;
}

.ring-text {
  font-size: 9px;
  font-weight: 600;
  color: var(--text-primary, #fff);
  z-index: 1;
}

/* Status colors using CSS variables */
.ring-complete .ring-progress {
  stroke: var(--completion-full, rgba(45, 122, 62, 0.9));
}

.ring-partial .ring-progress {
  stroke: var(--completion-partial, rgba(180, 140, 50, 0.9));
}

.ring-low .ring-progress {
  stroke: var(--completion-low, rgba(180, 70, 70, 0.9));
}

/* Hover glow effect */
.completion-ring:hover .ring-progress {
  filter: drop-shadow(0 0 4px currentColor);
}

.ring-complete:hover .ring-progress {
  filter: drop-shadow(0 0 6px var(--completion-full));
}

.ring-partial:hover .ring-progress {
  filter: drop-shadow(0 0 6px var(--completion-partial));
}

.ring-low:hover .ring-progress {
  filter: drop-shadow(0 0 6px var(--completion-low));
}
</style>
