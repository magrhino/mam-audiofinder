# Makefile for MAM Audiobook Finder - Test & Build Automation
#
# This Makefile provides targets for running tests in different modes:
# - Local testing (fast iteration, development)
# - Container testing (integration, Docker networking)
# - Dual-mode testing (mock vs live API)

.PHONY: help test-backend test-coverage test-mock test-live \
        docker-test-build docker-test-run docker-test-backend \
        docker-test-frontend docker-test-shell

# Default target
help:
	@echo "MAM Audiobook Finder - Test Automation"
	@echo ""
	@echo "Local Testing (fast, requires virtual environment):"
	@echo "  make test-backend          Run all backend tests (mock mode)"
	@echo "  make test-coverage         Run tests with HTML coverage report"
	@echo "  make test-mock             Run tests in MOCK mode (fixture data)"
	@echo "  make test-live             Run tests in LIVE mode (real API)"
	@echo ""
	@echo "Container Testing (integration, Docker networking):"
	@echo "  make docker-test-build     Build test container (first time)"
	@echo "  make docker-test-run       Run full test suite in container"
	@echo "  make docker-test-backend   Backend tests only (in container)"
	@echo "  make docker-test-frontend  Frontend tests / Selenium (in container)"
	@echo "  make docker-test-shell     Debug shell in test container"
	@echo ""
	@echo "Dual-Mode Testing:"
	@echo "  LIVE_API_TESTS=0 (default) - Use mock fixtures"
	@echo "  LIVE_API_TESTS=1           - Use real Hardcover API"

# ============================================================================
# LOCAL TESTING (requires virtual environment activated)
# ============================================================================

test-backend:
	@echo "Running backend tests (mock mode)..."
	cd .. && pytest app/tests/ -v --tb=short

test-coverage:
	@echo "Running tests with coverage report..."
	cd .. && pytest app/tests/ -v --cov=app --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"

test-mock:
	@echo "Running tests in MOCK mode (fixture data)..."
	cd .. && LIVE_API_TESTS=0 pytest app/tests/ -v --tb=short

test-live:
	@echo "Running tests in LIVE mode (real API)..."
	@echo "NOTE: Requires HARDCOVER_API_TOKEN in environment"
	cd .. && LIVE_API_TESTS=1 pytest app/tests/ -v --tb=short

# ============================================================================
# CONTAINER TESTING (Docker-based, integration)
# ============================================================================

docker-test-build:
	@echo "Building test container..."
	cd .. && docker compose -f build/docker-compose.test.yml build

docker-test-run:
	@echo "Running full test suite in container..."
	cd .. && docker compose -f build/docker-compose.test.yml run --rm test

docker-test-backend:
	@echo "Running backend tests in container..."
	cd .. && docker compose -f build/docker-compose.test.yml run --rm test pytest app/tests/ -v --tb=short

docker-test-frontend:
	@echo "Running frontend tests (Selenium) in container..."
	cd .. && docker compose -f build/docker-compose.test.yml run --rm test pytest app/tests/frontend/ -v --tb=short

docker-test-shell:
	@echo "Opening debug shell in test container..."
	cd .. && docker compose -f build/docker-compose.test.yml run --rm test sh
