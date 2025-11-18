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

## Migration Note

These composables replace legacy implementations:
- `useCover` replaces `CoverLoader` class and `useCovers` from legacy code
- `useMAMSearchDataTable` replaces manual table rendering in legacy views
