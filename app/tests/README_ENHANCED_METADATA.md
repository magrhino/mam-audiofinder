# Enhanced ABS Metadata Testing Guide

## Overview

This test suite validates whether Audiobookshelf's `/api/search/books` endpoint (with external provider integration) provides richer metadata than the current library-only approach.

**Goal**: Determine if the new endpoint can replace current `fetch_item_details()` logic.

## Setup

### 1. Install Test Dependencies

Install all required packages for running tests:

```bash
# From project root
pip install -r app/tests/test_requirements.txt
```

**Or use the dev requirements (includes all test dependencies):**
```bash
pip install -r build/requirements-dev.txt
```

**Required packages:**
- `pytest` - Test framework
- `pytest-asyncio` - Async test support (critical for ABS tests)
- `httpx` - HTTP client (used by abs_client.py)
- `sqlalchemy` - Database ORM
- `fastapi` - Required by app imports

### 2. Configure ABS in .env

Ensure your `.env` file has ABS credentials configured:

```bash
# .env - Add/verify these settings
ABS_BASE_URL=https://your-abs-instance.com
ABS_API_KEY=your-api-key-here
ABS_LIBRARY_ID=your-library-id
```

**Note**: Tests read environment variables from the container's .env file (same as production).

### 3. Find Your ABS Library ID

```bash
# Call ABS API to list libraries
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://your-abs-instance.com/api/libraries

# Response will include library IDs:
# [{"id": "lib_xyz123", "name": "Audiobooks", ...}]
```

## Running Tests

**⚠️  Important**: Tests must be run inside the Docker container where all dependencies and environment variables are configured.

### 1. Start and Enter Container

```bash
# Rebuild container with new schema
docker compose up -d --build

# Enter the running container
docker exec -it mam-audiofinder bash
```

### 2. Run Tests Inside Container

```bash
# Basic run (all tests)
cd /app
pytest tests/test_enhanced_abs_metadata.py -v

# Debug mode (verbose output - RECOMMENDED)
pytest tests/test_enhanced_abs_metadata.py -v --debug

# Test specific provider
pytest tests/test_enhanced_abs_metadata.py::TestEnhancedMetadataEndpoint::test_provider_audible -v --debug
pytest tests/test_enhanced_abs_metadata.py::TestEnhancedMetadataEndpoint::test_provider_google -v --debug
```

### Test All Providers Sequentially

```bash
pytest app/tests/test_enhanced_abs_metadata.py::TestAllProviders::test_all_providers_sequentially -v --debug
```

## How It Works

### 1. Random Item Selection

- First run: Selects random book from your ABS library
- Caches item ID to `/tmp/abs_test_item_id.txt`
- Caches item metadata to `/tmp/abs_test_item_data.json`
- Subsequent runs: Reuses cached item

**To test with different book:**
```bash
rm /tmp/abs_test_item_id.txt /tmp/abs_test_item_data.json
pytest app/tests/test_enhanced_abs_metadata.py -v --debug
```

### 2. Provider Testing

Tests try providers in order until **success criteria** is met:
- ✅ **Success**: Series array with numeric sequence returned
- ⚠️  **Partial**: Metadata returned but no series sequence
- ❌ **Failure**: No results from provider

**Providers tested:**
1. `audible` - Amazon Audible metadata
2. `google` - Google Books metadata
3. `openlibrary` - Open Library metadata
4. `itunes` - Apple Books metadata (optional)

### 3. Metadata Comparison

Tests compare **old method** vs **new method**:

**Old Method**: `fetch_item_details(item_id)` → Library data only
**New Method**: `/api/search/books?provider=X` → External provider data

**Fields Compared:**
- `narrator` - NEW (critical for audiobooks)
- `publisher` - NEW
- `rating` - NEW (e.g., "4.8")
- `region` - NEW (e.g., "us", "uk")
- `language` - ENHANCED (more accurate)
- `series` - ENHANCED (with sequence numbers)
- `description` - ENHANCED (longer, more detailed)
- `asin` / `isbn` - NEW (for future matching)

## Debug Output Example

```
================================================================================
PROVIDER TEST: audible
================================================================================
  Item ID: ccfac95f-b0fa-43da-b442-455568c03c7a
  Title: Mistborn: The Final Empire
  Author: Brandon Sanderson

REQUEST:
  URL: https://abs.example.com/api/search/books
  Params:
    provider: audible
    fallbackTitleOnly: 1
    title: Mistborn: The Final Empire
    id: ccfac95f-b0fa-43da-b442-455568c03c7a

RESPONSE (200):
  Results: 9 book(s)

FIRST RESULT:
  Title: Mistborn: The Final Empire
  Author: Brandon Sanderson
  Narrator: ✅ Michael Kramer
  Publisher: ✅ Macmillan Audio
  Series: ✅ The Mistborn Saga #1
  Rating: ✅ 4.8
  Region: ✅ us
  Language: ✅ English
  ASIN: ✅ B002V0QCYU
  ISBN: ✅ 9781427206374

✅ SUCCESS: Series with sequence found!

================================================================================
COMPARISON: Old vs New Metadata
================================================================================
Field                | Old Value                 | New Value                 | Status
--------------------------------------------------------------------------------
narrator             | (missing)                 | Michael Kramer            | ✅ NEW
publisher            | (missing)                 | Macmillan Audio           | ✅ NEW
series               | 1 items                   | 1 items                   | ✅ ENHANCED
rating               | (missing)                 | 4.8                       | ✅ NEW
region               | (missing)                 | us                        | ✅ NEW
language             | English                   | English                   | → SAME
asin                 | (missing)                 | B002V0QCYU                | ✅ NEW
isbn                 | (missing)                 | 9781427206374             | ✅ NEW
description          | 1,234 chars               | 4,567 chars               | ✅ ENHANCED
================================================================================
```

## Success Criteria

For the new endpoint to replace the old logic, it must provide:

1. ✅ **Series with sequence numbers** (critical)
2. ✅ **Narrator** (critical for audiobooks)
3. ✅ **Publisher** (important)
4. ✅ **Rating** (nice to have)
5. ✅ **Region** (nice to have)
6. ✅ **Enhanced descriptions** (longer, more detailed)

## Interpreting Results

### ✅ Full Success

All fields populated, series has sequence numbers:

```
SUCCESS: audible returned series with sequence!
Comparison: 5+ new fields, series enhanced
```

**Action**: New endpoint is sufficient, can replace old logic

### ⚠️  Partial Success

Some fields populated, but missing series sequence:

```
NO SERIES SEQUENCE: Will try next provider
Comparison: 3+ new fields, series missing sequence
```

**Action**: Try other providers, evaluate if partial data is acceptable

### ❌ Failure

No results or insufficient data:

```
Provider audible failed: HTTP 404
No provider returned series with sequence
```

**Action**: Investigate API connectivity, check item type compatibility

## Troubleshooting

### No Items in Library

```
⚠️  No items in ABS library
```

**Fix**: Add books to your ABS library first

### ABS Not Configured

```
⚠️  ABS not configured (check ABS_BASE_URL and ABS_API_KEY in .env)
```

**Fix**: Add ABS credentials to your `.env` file in the project root

### Connection Refused

```
❌ Failed to fetch from provider: ConnectionRefusedError
```

**Fix**: Verify `ABS_BASE_URL` is correct and accessible

### All Providers Fail

```
⚠️  No provider returned series with sequence
```

**Possible causes:**
1. Book not in provider databases (try different book)
2. Providers rate-limiting requests
3. Item is not an audiobook (some providers audiobook-only)

**Solution**: Clear cache and test with well-known book:
```bash
rm /tmp/abs_test_item_*.txt
# Manually edit cache file to test specific book:
echo "your-known-good-item-id" > /tmp/abs_test_item_id.txt
pytest app/tests/test_enhanced_abs_metadata.py -v --debug
```

## Next Steps

After testing:

1. **If tests pass**: Implement new endpoint in production code
2. **If tests fail**: Document gaps, decide if acceptable
3. **Document findings**: Update CLAUDE.md with results

## Files Modified

- `app/db/covers_schema.sql` - New schema with enhanced fields
- `app/db/db.py` - Initialize covers.db from fresh schema
- `app/db/migrations/DEPRECATED_*.sql` - Old migrations marked deprecated
- `app/abs_client.py` - Added `fetch_enhanced_metadata_test()` method
- `app/tests/test_enhanced_abs_metadata.py` - Comprehensive test suite

## Migration Fields (If Tests Pass)

New fields to add to covers.db:

```sql
narrator TEXT
publisher TEXT
region TEXT
rating TEXT
description_plain TEXT
```

(Already included in new `covers_schema.sql`)
