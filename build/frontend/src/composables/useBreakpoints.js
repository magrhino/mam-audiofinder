/**
 * Centralized Breakpoint System - Single Source of Truth
 *
 * Exports standardized responsive breakpoints for the entire application.
 * All components should use this composable instead of defining their own breakpoints.
 *
 * Breakpoint Definitions:
 * - mobile: 0-767px (phones, small tablets)
 * - tablet: 768-1023px (tablets, small laptops)
 * - desktop: 1024px+ (laptops, desktops)
 */

import { useBreakpoints as useVueUseBreakpoints } from '@vueuse/core'
import { computed } from 'vue'

/**
 * Get reactive breakpoint state
 * @returns {object} Reactive breakpoint flags
 */
export function useBreakpoints() {
  // Define breakpoint thresholds (single source of truth)
  const breakpoints = useVueUseBreakpoints({
    mobile: 0,      // 0-767px
    tablet: 768,    // 768-1023px
    desktop: 1024   // 1024px+
  })

  // Export computed properties for easier usage
  const isMobile = computed(() => breakpoints.smaller('tablet').value)
  const isTablet = computed(() => breakpoints.between('tablet', 'desktop').value)
  const isDesktop = computed(() => breakpoints.greaterOrEqual('desktop').value)

  return {
    breakpoints,
    isMobile,
    isTablet,
    isDesktop
  }
}
