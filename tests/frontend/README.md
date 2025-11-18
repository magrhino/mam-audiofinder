# Frontend Test Suite

Vue.js-compatible testing suite for MAM Audiobook Finder frontend logic.

## Quick Start

```bash
# Install dependencies
npm install

# Run all tests (watch mode)
npm test

# Run tests once
npm run test:run

# Interactive UI
npm run test:ui

# Coverage report
npm run test:coverage
```

## Test Files

### Core (30+ tests)
- **`core/api.test.js`** - API client methods (health, config, search, fetchCover, getHistory, verify, import, series, etc.)

### Services (30+ tests)
- **`services/coverLoader.test.js`** - CoverLoader class (initialization, IntersectionObserver, lazy loading, row state, fetching, cleanup)

### Components (55+ tests)
- **`components/libraryIndicator.test.js`** - Library status badges (creation, display, accessibility)
- **`components/importForm.test.js`** - Import workflow (rendering, torrent loading, multi-disc detection, file tree, import execution, validation, warnings)

## Test Utilities

### Mocks
- **`mocks/api.mock.js`** - Mock data and API responses (search, history, torrents, import, covers)

### Helpers
- **`utils/dom-helpers.js`** - DOM manipulation (containers, queries, user events, async helpers)

### Setup
- **`setup.js`** - Global configuration (IntersectionObserver mock, fetch mock, console overrides)

## Coverage

Run `npm run test:coverage` to generate detailed coverage report.

**Current Coverage:**
- Core API: ~95%
- CoverLoader: ~93%
- LibraryIndicator: 100%
- ImportForm: ~88%

## Documentation

See **[FRONTEND_TESTING.md](../../FRONTEND_TESTING.md)** for comprehensive guide including:
- Test patterns
- Mocking strategies
- DOM helpers
- Debugging
- Best practices
- CI/CD integration

## Key Features Tested

✅ **Cover Fetching** - Lazy loading with IntersectionObserver, API integration, error handling
✅ **Description Fetching** - API calls, metadata retrieval, caching
✅ **Library Indicators** - Visual badges, DOM manipulation, accessibility
✅ **Import Form** - Multi-disc detection, torrent matching, file tree rendering, validation
✅ **Error Handling** - Network failures, missing data, validation errors
✅ **User Interactions** - Input changes, button clicks, form submission

## Architecture

```
tests/frontend/
├── setup.js                   # Global test config
├── mocks/
│   └── api.mock.js           # Mock responses
├── utils/
│   └── dom-helpers.js        # Test utilities
├── core/
│   └── api.test.js           # API tests
├── services/
│   └── coverLoader.test.js   # Service tests
└── components/
    ├── libraryIndicator.test.js
    └── importForm.test.js    # Component tests
```

## Technology Stack

- **Test Runner:** Vitest 1.2+
- **DOM Environment:** happy-dom
- **Test Utils:** @vue/test-utils 2.4+
- **Coverage:** @vitest/coverage-v8
- **UI:** @vitest/ui

## Writing Tests

Example test structure:

```javascript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mockFetchResponses, resetMocks } from '../mocks/api.mock.js';
import { cleanupDOM, createTestContainer } from '../utils/dom-helpers.js';

describe('MyFeature', () => {
  let container;

  beforeEach(() => {
    container = createTestContainer();
    mockFetchResponses();
  });

  afterEach(() => {
    cleanupDOM();
    resetMocks();
  });

  it('should do something', async () => {
    // Test implementation
  });
});
```

## CI Integration

Tests are designed to run in CI/CD pipelines:

```yaml
- run: npm install
- run: npm run test:run
- run: npm run test:coverage
```

## Debugging

```bash
# Run specific test file
npx vitest tests/frontend/services/coverLoader.test.js

# Run tests matching pattern
npx vitest --grep "cover fetching"

# Verbose output
npx vitest --reporter=verbose

# Debug in VS Code
# Install Vitest extension and use "Debug" button
```

## Next Steps

1. **Run tests:** `npm test`
2. **Review coverage:** `npm run test:coverage`
3. **Explore UI:** `npm run test:ui`
4. **Read docs:** [FRONTEND_TESTING.md](../../FRONTEND_TESTING.md)

---

**Total Tests:** 100+
**Test Framework:** Vitest
**Environment:** happy-dom
**Designed for:** Vue.js migration readiness
