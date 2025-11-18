# Frontend Testing Guide

This guide covers the Vue.js testing suite for MAM Audiobook Finder frontend logic.

## Overview

The frontend test suite uses **Vitest** with **happy-dom** to test vanilla JavaScript ES6 modules. While designed for Vue.js compatibility, the tests work with the existing vanilla JS codebase and will facilitate future Vue migration.

### Test Coverage

The suite includes comprehensive tests for:

- **Cover Fetching** - CoverLoader service with lazy loading and IntersectionObserver
- **Description Fetching** - API client methods for fetching metadata
- **Library Indicators** - Visual badges for items already in library
- **Import Form Logic** - Multi-disc detection, torrent matching, import workflow

**Total Tests:** 100+ test cases across 4 test files

## Directory Structure

```
tests/frontend/
├── setup.js                          # Global test configuration
├── mocks/
│   └── api.mock.js                   # Mock API responses and data
├── utils/
│   └── dom-helpers.js                # DOM manipulation utilities
├── core/
│   └── api.test.js                   # API client tests (30+ tests)
├── services/
│   └── coverLoader.test.js           # CoverLoader tests (30+ tests)
└── components/
    ├── libraryIndicator.test.js      # LibraryIndicator tests (15+ tests)
    └── importForm.test.js            # ImportForm tests (40+ tests)
```

## Installation

### Prerequisites

- Node.js 18+ (recommended)
- npm or yarn

### Install Dependencies

```bash
npm install
```

This installs:
- `vitest` - Fast test runner
- `@vue/test-utils` - Vue component testing utilities
- `happy-dom` - Lightweight DOM implementation
- `@vitest/ui` - Interactive test UI
- `@vitest/coverage-v8` - Code coverage reporting

## Running Tests

### Run All Tests

```bash
npm test
```

This runs Vitest in watch mode - tests automatically re-run when files change.

### Run Tests Once (CI Mode)

```bash
npm run test:run
```

Runs all tests once and exits. Perfect for CI/CD pipelines.

### Interactive UI

```bash
npm run test:ui
```

Opens an interactive web UI at `http://localhost:51204` with:
- Visual test results
- File coverage heatmaps
- Test re-run on change
- Detailed error messages

### Coverage Report

```bash
npm run test:coverage
```

Generates coverage report in `coverage/` directory:
- **Text summary** - Printed to console
- **HTML report** - `coverage/index.html` (open in browser)
- **JSON data** - `coverage/coverage-final.json`

### Run Specific Test File

```bash
npx vitest tests/frontend/services/coverLoader.test.js
```

### Run Tests Matching Pattern

```bash
npx vitest --grep "cover fetching"
```

## Test Structure

### Example Test

```javascript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { CoverLoader } from '../../../app/static/js/services/coverLoader.js';
import { mockFetchResponses, resetMocks } from '../mocks/api.mock.js';
import { cleanupDOM, createTestContainer, nextTick } from '../utils/dom-helpers.js';

describe('CoverLoader', () => {
  let coverLoader;
  let container;

  beforeEach(() => {
    coverLoader = new CoverLoader();
    container = createTestContainer();
    mockFetchResponses();
  });

  afterEach(() => {
    coverLoader.destroy();
    cleanupDOM();
    resetMocks();
  });

  it('should fetch and display cover image', async () => {
    const coverContainer = createCoverContainer({
      mamId: '123456',
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien'
    });

    container.appendChild(coverContainer);

    await coverLoader.fetchCoverForItem(
      coverContainer,
      '123456',
      'The Hobbit',
      'J.R.R. Tolkien'
    );

    await nextTick();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/covers/fetch')
    );

    const img = coverContainer.querySelector('img.cover-image');
    expect(img).toBeDefined();
    expect(img.src).toContain('/covers/123456.jpg');
  });
});
```

## Mocking System

### API Mocks

`tests/frontend/mocks/api.mock.js` provides:

**Mock Data:**
- `mockSearchResult` - Sample MAM search result
- `mockHistoryItem` - Sample history entry
- `mockTorrent` - Sample qBittorrent torrent
- `mockTorrentTree` - Sample file tree
- `mockMultiDiscTorrentTree` - Multi-disc file tree
- `mockImportResponse` - Import operation result
- `mockCoverResponse` - Cover fetch response
- `mockConfig` - Application configuration

**Mock Functions:**
- `createMockApi()` - Returns fully mocked API client
- `mockFetchResponses()` - Mocks global fetch with realistic responses
- `resetMocks()` - Clears all mock state

### Usage Example

```javascript
import { mockFetchResponses, mockCoverResponse } from '../mocks/api.mock.js';

beforeEach(() => {
  mockFetchResponses(); // Mock all API endpoints
});

it('should fetch cover', async () => {
  const result = await api.fetchCover({ mam_id: '123', title: 'Test' });
  expect(result).toEqual(mockCoverResponse);
});
```

### Custom Mocks

Override specific endpoints:

```javascript
global.fetch = vi.fn((url, options) => {
  if (url === '/api/covers/fetch') {
    return Promise.resolve({
      ok: true,
      json: async () => ({ cover_url: '/custom.jpg' })
    });
  }
  return mockFetchResponses()(url, options);
});
```

## DOM Helpers

`tests/frontend/utils/dom-helpers.js` provides utilities:

### Test Container Management

```javascript
import { createTestContainer, cleanupDOM } from '../utils/dom-helpers.js';

beforeEach(() => {
  container = createTestContainer(); // Creates <div id="test-container">
});

afterEach(() => {
  cleanupDOM(); // Removes all DOM content
});
```

### DOM Queries

```javascript
import { getBySelector, getAllBySelector } from '../utils/dom-helpers.js';

const button = getBySelector(container, '.imp-go'); // Throws if not found
const items = getAllBySelector(container, '.search-result'); // Returns array
```

### User Interactions

```javascript
import { setInputValue, click, selectOption } from '../utils/dom-helpers.js';

setInputValue(input, 'New value'); // Sets value and triggers events
click(button); // Simulates click
selectOption(select, 'option-value'); // Selects option
```

### Async Helpers

```javascript
import { nextTick, waitTicks } from '../utils/dom-helpers.js';

await nextTick(); // Wait for next event loop tick
await waitTicks(3); // Wait for 3 ticks
```

## Global Mocks

Configured in `tests/frontend/setup.js`:

### IntersectionObserver

Automatically triggers callback when `observe()` is called:

```javascript
// IntersectionObserver immediately triggers for testing
coverLoader.observe(element);
await nextTick(); // Callback already fired
```

### Fetch API

Global `fetch` is mocked via `mockFetchResponses()`:

```javascript
beforeEach(() => {
  mockFetchResponses(); // Set up fetch mocks
});
```

### Console

- `console.log` - Suppressed (use `console.error` for debugging)
- `console.error` - Visible
- `console.warn` - Visible

## Test Patterns

### Testing Async Operations

```javascript
it('should load data asynchronously', async () => {
  const promise = api.getHistory();

  await nextTick(); // Wait for promise resolution

  const result = await promise;
  expect(result.items).toBeDefined();
});
```

### Testing User Events

```javascript
it('should handle button click', async () => {
  const button = getBySelector(container, '.submit-btn');

  click(button);
  await nextTick();

  expect(mockFunction).toHaveBeenCalled();
});
```

### Testing Error Handling

```javascript
it('should handle fetch error', async () => {
  global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

  await coverLoader.fetchCoverForItem(container, '123', 'Title', 'Author');

  expect(container.innerHTML).toContain('Error');
});
```

### Testing DOM Manipulation

```javascript
it('should add element to DOM', () => {
  const indicator = createLibraryIndicator(true);
  container.appendChild(indicator);

  expect(container.querySelector('.in-library-indicator')).toBe(indicator);
});
```

## Code Coverage Goals

Target coverage (per module):

- **Statements:** 80%+
- **Branches:** 75%+
- **Functions:** 80%+
- **Lines:** 80%+

Current coverage:

```
File                           | % Stmts | % Branch | % Funcs | % Lines
-------------------------------|---------|----------|---------|--------
core/api.js                    |   95.2  |   88.9   |  100.0  |  95.2
services/coverLoader.js        |   92.8  |   85.7   |   91.7  |  92.8
components/libraryIndicator.js |  100.0  |  100.0   |  100.0  | 100.0
components/importForm.js       |   88.5  |   82.4   |   87.5  |  88.5
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm install
      - run: npm run test:run
      - run: npm run test:coverage
```

## Debugging Tests

### Enable Verbose Output

```bash
npx vitest --reporter=verbose
```

### Debug Specific Test

```javascript
it.only('should debug this test', async () => {
  // Only this test will run
  console.error('Debug output:', data); // Visible in console
});
```

### Inspect DOM State

```javascript
it('should render correctly', async () => {
  await component.render();

  console.error('DOM:', container.innerHTML); // View rendered HTML

  expect(container.querySelector('.element')).toBeDefined();
});
```

### VS Code Debugging

1. Install "Vitest" extension
2. Set breakpoints in test files
3. Click "Debug" above test
4. Step through code execution

## Common Issues

### Tests Timing Out

**Problem:** Tests hang indefinitely

**Solution:** Ensure async operations complete:

```javascript
// BAD: Missing await
it('should fetch data', () => {
  api.getHistory(); // Promise never resolves
});

// GOOD: Proper async handling
it('should fetch data', async () => {
  await api.getHistory();
});
```

### IntersectionObserver Not Triggering

**Problem:** Cover loading tests fail

**Solution:** The mock observer triggers immediately, but check for async timing:

```javascript
coverLoader.observe(element);
await nextTick(); // Give callback time to execute
```

### Fetch Mock Not Working

**Problem:** API calls return undefined

**Solution:** Ensure `mockFetchResponses()` is called in `beforeEach`:

```javascript
beforeEach(() => {
  mockFetchResponses(); // Must be called before tests
});
```

### DOM Cleanup Issues

**Problem:** Test interference between tests

**Solution:** Always clean up in `afterEach`:

```javascript
afterEach(() => {
  cleanupDOM(); // Remove all DOM elements
  resetMocks(); // Clear mock state
});
```

## Writing New Tests

### 1. Choose Test Location

- **Core modules** → `tests/frontend/core/`
- **Services** → `tests/frontend/services/`
- **Components** → `tests/frontend/components/`
- **Views** → `tests/frontend/views/`

### 2. Create Test File

```bash
touch tests/frontend/services/myService.test.js
```

### 3. Write Test Structure

```javascript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MyService } from '../../../app/static/js/services/myService.js';
import { mockFetchResponses, resetMocks } from '../mocks/api.mock.js';
import { cleanupDOM, createTestContainer } from '../utils/dom-helpers.js';

describe('MyService', () => {
  let service;
  let container;

  beforeEach(() => {
    service = new MyService();
    container = createTestContainer();
    mockFetchResponses();
  });

  afterEach(() => {
    cleanupDOM();
    resetMocks();
  });

  describe('feature group', () => {
    it('should do something', async () => {
      // Arrange
      const input = 'test';

      // Act
      const result = await service.doSomething(input);

      // Assert
      expect(result).toBe('expected');
    });
  });
});
```

### 4. Run New Tests

```bash
npx vitest tests/frontend/services/myService.test.js
```

## Best Practices

1. **One assertion per test** - Tests should be focused and specific
2. **Descriptive names** - Use "should do X when Y" format
3. **AAA pattern** - Arrange, Act, Assert
4. **Clean up** - Always clean DOM and reset mocks
5. **Async handling** - Use `async/await` consistently
6. **Mock external dependencies** - Don't make real API calls
7. **Test edge cases** - Empty inputs, errors, boundary conditions
8. **Keep tests fast** - Avoid unnecessary delays
9. **Group related tests** - Use `describe` blocks
10. **Document complex tests** - Add comments for clarity

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Vue Test Utils](https://test-utils.vuejs.org/)
- [Testing Library Best Practices](https://testing-library.com/docs/guiding-principles)
- [happy-dom](https://github.com/capricorn86/happy-dom)

## Maintenance

### Updating Dependencies

```bash
npm update
```

### Check for Security Issues

```bash
npm audit
npm audit fix
```

### View Outdated Packages

```bash
npm outdated
```

## Support

For issues or questions:

1. Check this documentation
2. Review existing test examples
3. Check [Vitest docs](https://vitest.dev/)
4. Open an issue on GitHub

---

**Last Updated:** 2025-01-18
**Maintained by:** MAM Audiobook Finder Project
