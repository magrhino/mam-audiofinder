<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="customTheme">
    <n-dialog-provider>
      <n-message-provider>
        <n-global-style />

        <!-- Atmospheric background with gradient -->
        <div class="atmospheric-background"></div>

        <!-- Ember particle system - drifting golden particles -->
        <div class="particle-container">
          <div
            v-for="i in 10"
            :key="`ember-${i}`"
            class="ember-particle"
            :style="getParticleStyle(i)"
          ></div>
        </div>

        <!-- Main app content -->
        <div id="app">
          <NavBar v-if="showNavBar" :health="healthStatus" />
          <RouterView />
        </div>
      </n-message-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { darkTheme, NConfigProvider, NGlobalStyle, NDialogProvider, NMessageProvider } from 'naive-ui'
import { customTheme } from './theme/naive'
import NavBar from '@components/NavBar.vue'
import { useApi } from '@composables/useApi'
import { useAuth } from '@composables/useAuth'

const route = useRoute()
const healthStatus = ref({ ok: false, checking: true })
const api = useApi()
const { isAuthenticated, requiresAuth } = useAuth()

// Show navbar when not on login page and either authenticated or auth not required
const showNavBar = computed(() => {
  // Don't show on login page
  if (route.name === 'login') return false
  // Show if authenticated or auth not required
  return isAuthenticated.value || !requiresAuth.value
})

const checkHealth = async () => {
  try {
    const health = await api.health()
    healthStatus.value = { ok: health.ok, checking: false }
  } catch (error) {
    console.error('Health check failed:', error)
    healthStatus.value = { ok: false, checking: false }
  }
}

// Generate randomized particle styles for natural, varied movement
const getParticleStyle = (index) => {
  // Randomize horizontal starting position (0-100% of viewport width)
  const startX = Math.random() * 100

  // Randomize drift direction (left or right) and distance
  const driftDirection = Math.random() > 0.5 ? 1 : -1
  const driftDistance = (20 + Math.random() * 40) * driftDirection

  // Randomize horizontal sway
  const swayDistance = (10 + Math.random() * 20) * (Math.random() > 0.5 ? 1 : -1)

  // Randomize particle size (3-6px diameter)
  const size = 3 + Math.random() * 3

  // Randomize animation duration (15-20s for slow drift)
  const driftDuration = 15 + Math.random() * 5
  const swayDuration = 6 + Math.random() * 4
  const glowDuration = 2.5 + Math.random() * 1.5

  // Stagger animation start (delay 0-18s for natural distribution)
  const delay = Math.random() * 18

  return {
    left: `${startX}%`,
    width: `${size}px`,
    height: `${size}px`,
    '--drift-x': `${driftDistance}px`,
    '--sway-distance': `${swayDistance}px`,
    animationDuration: `${driftDuration}s, ${swayDuration}s, ${glowDuration}s`,
    animationDelay: `${delay}s, ${delay}s, ${delay}s`,
  }
}

onMounted(() => {
  checkHealth()
  // Check health every 30 seconds
  setInterval(checkHealth, 30000)
})
</script>

<style scoped>
/**
 * Atmospheric Background - Charcoal to Maroon Gradient
 * Creates the base atmospheric effect with vertical gradient
 */
.atmospheric-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  /* Vertical gradient: matte charcoal (#0a0a0a) → oxblood maroon (#6a0000) */
  background: linear-gradient(180deg, #0a0a0a 0%, #6a0000 100%);
  z-index: -2;
  pointer-events: none;
}

/**
 * Particle Container - Holds all drifting ember particles
 * Fixed positioning to cover entire viewport
 */
.particle-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  pointer-events: none; /* Allow clicking through particles */
  z-index: -1; /* Behind all content but above background */
}

/**
 * Ember Particle - Individual golden glowing embers
 * GPU-accelerated animations for smooth performance:
 * 1. drift-up: Vertical rise from bottom to top (15-20s)
 * 2. sway: Gentle horizontal movement (6-10s)
 * 3. glow-pulse: Soft pulsing glow effect (2.5-4s)
 */
.ember-particle {
  position: absolute;
  bottom: 0;
  border-radius: 50%;
  background: radial-gradient(circle, #ffb366 0%, rgba(255, 179, 102, 0.6) 50%, transparent 100%);

  /* Soft golden glow with layered shadows */
  box-shadow:
    0 0 8px rgba(255, 179, 102, 0.3),
    0 0 12px rgba(255, 85, 0, 0.2);

  /* GPU-accelerated animations (transform + opacity) */
  animation-name: drift-up, sway, glow-pulse;
  animation-timing-function: ease-in-out, ease-in-out, ease-in-out;
  animation-iteration-count: infinite, infinite, infinite;

  /* Will-change hint for GPU optimization */
  will-change: transform, opacity;
}

/**
 * Keyframe: drift-up
 * Vertical movement from below viewport to above
 * Includes opacity fade-in at start and fade-out at end
 * Uses CSS variable --drift-x for horizontal offset variation
 */
@keyframes drift-up {
  0% {
    transform: translate(0, 0) translateY(100vh);
    opacity: 0;
  }
  10% {
    opacity: 0.6; /* Fade in */
  }
  90% {
    opacity: 0.4; /* Start fading out */
  }
  100% {
    transform: translate(var(--drift-x, 0), 0) translateY(-20vh);
    opacity: 0; /* Fully faded */
  }
}

/**
 * Keyframe: sway
 * Gentle horizontal oscillation for natural drift effect
 * Uses CSS variable --sway-distance for varied movement
 */
@keyframes sway {
  0%, 100% {
    transform: translateX(0);
  }
  50% {
    transform: translateX(var(--sway-distance, 20px));
  }
}

/**
 * Keyframe: glow-pulse
 * Soft pulsing glow effect for ember-like appearance
 * Alternates between dim and bright glow
 */
@keyframes glow-pulse {
  0%, 100% {
    box-shadow:
      0 0 8px rgba(255, 179, 102, 0.3),
      0 0 12px rgba(255, 85, 0, 0.2);
  }
  50% {
    box-shadow:
      0 0 12px rgba(255, 179, 102, 0.5),
      0 0 20px rgba(255, 85, 0, 0.4);
  }
}

/**
 * Main App Container
 * Positioned relatively to allow proper z-index stacking
 */
#app {
  position: relative;
  z-index: 1; /* Above particles and background */
}
</style>
