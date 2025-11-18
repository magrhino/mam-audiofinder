# NaiveUI Composables

This directory contains composables specifically designed for use with NaiveUI components.

## Files

### `useCover.js`
Composable for fetching cover images from the backend API. Used with the `CoverImage` component which wraps NaiveUI's `n-image` component.

**Usage:**
```js
import { useCover } from '@composables/naive/useCover'

const { coverUrl, loading, error, fetchCover } = useCover({
  mamId: '12345',
  title: 'Book Title',
  author: 'Author Name'
})

await fetchCover()
```

### `useMAMSearchDataTable.js`
Composable for managing NaiveUI `n-data-table` instances with predefined column configurations customized for MAM Audiobook Finder search functionality. Includes responsive column widths and mobile-optimized display.

**Usage:**
```js
import { useMAMSearchDataTable } from '@composables/naive/useMAMSearchDataTable'

const {
  tableRef,
  data,
  columns,
  pagination,
  loading,
  setData,
  clearData,
  sort,
  filter
} = useMAMSearchDataTable({
  viewType: 'search',
  onAdd: handleAdd,
  defaultPageSize: 25
})
```

## Why Separate?

NaiveUI composables are kept separate from general composables to:
1. Make the migration from legacy code clearer
2. Indicate dependency on NaiveUI library
3. Allow for easier refactoring if UI library changes
4. Keep NaiveUI-specific logic isolated

## Responsive Design Patterns

### Using @vueuse/core for Breakpoints

For responsive behavior in components using NaiveUI, use `useBreakpoints` from @vueuse/core:

```js
import { useBreakpoints } from '@vueuse/core'
import { computed } from 'vue'

// Define breakpoints (consistent across project)
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Dynamic scroll-x for n-data-table
const scrollX = computed(() => {
  if (breakpoints.greater('desktop').value) {
    return 1400 // Desktop: expanded layout
  } else if (breakpoints.greater('tablet').value) {
    return 1200 // Tablet: standard layout
  } else {
    return 900 // Mobile: compact layout
  }
})
```

### Best Practices

1. **Consistent Breakpoints**: Use mobile (0), tablet (768), desktop (1024) across the app
2. **Computed Properties**: Wrap responsive values in `computed()` for reactivity
3. **CSS for Styling**: Use CSS media queries for visual changes, JavaScript for behavior
4. **Progressive Enhancement**: Start with mobile, enhance for larger screens

### Example: Responsive Table

```vue
<template>
  <n-data-table :scroll-x="scrollX" :columns="columns" :data="data" />
</template>

<script setup>
import { useBreakpoints } from '@vueuse/core'
import { computed } from 'vue'

const breakpoints = useBreakpoints({ mobile: 0, tablet: 768, desktop: 1024 })
const scrollX = computed(() =>
  breakpoints.greater('desktop').value ? 1400 :
  breakpoints.greater('tablet').value ? 1200 : 900
)
</script>
```

## Migration Note

These composables replace legacy implementations:
- `useCover` replaces `CoverLoader` class and `useCovers` from legacy code
- `useMAMSearchDataTable` replaces manual table rendering in legacy views
