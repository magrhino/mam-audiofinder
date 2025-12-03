#!/bin/sh
# run-tests.sh - Unified test runner for MAM Audiobook Finder
#
# Replaces the old Makefile with a more user-friendly interface
# Supports both local Python and Docker container execution
# Defaults to mock mode for safe, fast testing

set -e  # Exit on error

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.test.yml"
SERVICE_NAME="test"

# ============================================================================
# Global Variables
# ============================================================================

MODE=""
EXEC_MODE="auto"  # auto|local|docker
LIVE_API=""
MOCK_MODE=""
PYTEST_ARGS=""

# ============================================================================
# Help Text
# ============================================================================

show_help() {
  cat <<'EOF'
run-tests.sh - Unified test runner for MAM Audiobook Finder

USAGE:
  ./run-tests.sh [MODE] [OPTIONS] [-- PYTEST_ARGS]

MODES:
  (none)      Run full test suite (default)
  backend     Run backend tests only
  frontend    Run frontend tests (Selenium, Docker only)
  coverage    Generate coverage report (HTML + terminal)
  build       Build Docker test image
  shell       Open debug shell in test container

OPTIONS:
  --live      Force live API tests (local only, requires HARDCOVER_API_TOKEN)
  --mock      Force mock API tests (Docker only, uses fixtures)
  --docker    Force Docker execution
  --local     Force local Python execution
  --help      Show this help

PYTEST PASSTHROUGH:
  --          All arguments after -- pass directly to pytest
              Example: ./run-tests.sh -- -v -k hardcover

EXAMPLES:
  ./run-tests.sh                          # Full suite, auto-detect mode
  ./run-tests.sh backend                  # Backend tests only
  ./run-tests.sh --live                   # Force live API (local mode)
  ./run-tests.sh --docker --mock          # Force mock in Docker
  ./run-tests.sh coverage                 # Coverage report
  ./run-tests.sh build                    # Build test container
  ./run-tests.sh shell                    # Debug shell
  ./run-tests.sh -- -v                    # Verbose output
  ./run-tests.sh backend -- tests/test_verification.py  # Specific file

ENVIRONMENT:
  HARDCOVER_API_TOKEN    Required for --live mode
  LIVE_API_TESTS         Set to 1 for live API tests (auto-set by --live)

AUTO-DETECTION:
  - Local Python: If venv/ exists or VIRTUAL_ENV set
  - Docker: Otherwise (or forced via --docker)
  - Frontend/build/shell always use Docker

DUAL-MODE TESTING:
  Local tests (default: MOCK):
    - Uses pre-recorded JSON fixtures
    - Fast (~200ms per test)
    - No API token needed
    - Use --live to override

  Docker tests (default: LIVE):
    - Calls real Hardcover/ABS APIs
    - Integration testing with real services
    - Requires .env with API tokens
    - Use --mock to override

For more information, see docs/TESTING.md
EOF
}

# ============================================================================
# Argument Parsing
# ============================================================================

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      backend|frontend|coverage|build|shell)
        if [ -n "$MODE" ]; then
          echo "ERROR: Multiple modes specified. Choose only one."
          echo ""
          show_help
          exit 1
        fi
        MODE="$1"
        shift
        ;;
      --live)
        LIVE_API="1"
        shift
        ;;
      --mock)
        MOCK_MODE="1"
        shift
        ;;
      --docker)
        EXEC_MODE="docker"
        shift
        ;;
      --local)
        EXEC_MODE="local"
        shift
        ;;
      --help|-h)
        show_help
        exit 0
        ;;
      --)
        shift
        PYTEST_ARGS="$*"
        break
        ;;
      *)
        echo "ERROR: Unknown argument: $1"
        echo ""
        show_help
        exit 1
        ;;
    esac
  done
}

# ============================================================================
# Execution Mode Detection
# ============================================================================

detect_mode() {
  # Force Docker for certain modes
  case "$MODE" in
    frontend|build|shell)
      EXEC_MODE="docker"
      return
      ;;
  esac

  # Auto-detect if not explicitly set
  if [ "$EXEC_MODE" = "auto" ]; then
    if [ -d "$WORKSPACE_ROOT/build/venv" ] || [ -n "$VIRTUAL_ENV" ]; then
      EXEC_MODE="local"
    else
      EXEC_MODE="docker"
    fi
  fi
}

# ============================================================================
# Validators
# ============================================================================

validate_local_env() {
  if ! command -v pytest >/dev/null 2>&1; then
    echo "ERROR: pytest not found. Install with:"
    echo ""
    echo "  cd $WORKSPACE_ROOT/build"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements-dev.txt"
    echo ""
    exit 2
  fi
}

validate_live_mode() {
  if [ -n "$LIVE_API" ] && [ -z "$HARDCOVER_API_TOKEN" ]; then
    echo "ERROR: --live requires HARDCOVER_API_TOKEN environment variable"
    echo ""
    echo "Set your token:"
    echo "  export HARDCOVER_API_TOKEN=\"your_token_here\""
    echo ""
    echo "Or run in mock mode (default):"
    echo "  ./run-tests.sh"
    echo ""
    exit 2
  fi
}

validate_flags() {
  # Check for conflicting flags
  if [ -n "$LIVE_API" ] && [ -n "$MOCK_MODE" ]; then
    echo "ERROR: Cannot use both --live and --mock flags"
    echo ""
    exit 1
  fi

  # Warn if using --mock with local mode
  if [ -n "$MOCK_MODE" ] && [ "$EXEC_MODE" = "local" ]; then
    echo "WARNING: --mock flag is for Docker mode. Local tests are mock by default."
    echo ""
  fi

  # Warn if using --live with Docker mode
  if [ -n "$LIVE_API" ] && [ "$EXEC_MODE" = "docker" ]; then
    echo "WARNING: --live flag is for local mode. Docker tests are live by default."
    echo ""
  fi
}

validate_docker_available() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker command not found"
    echo "Install Docker: https://docs.docker.com/get-docker/"
    exit 2
  fi

  if ! docker ps >/dev/null 2>&1; then
    echo "ERROR: Docker daemon not running"
    echo "Start Docker and try again"
    exit 2
  fi
}

# ============================================================================
# Local Execution
# ============================================================================

run_local() {
  cd "$WORKSPACE_ROOT/app"

  # Set environment for live API tests if requested
  if [ -n "$LIVE_API" ]; then
    export LIVE_API_TESTS="1"
  else
    export LIVE_API_TESTS="0"
  fi

  case "$MODE" in
    backend|"")
      echo "Running backend tests (local Python)..."
      pytest tests/ -v --tb=short $PYTEST_ARGS
      ;;
    coverage)
      echo "Running tests with coverage report (local Python)..."
      pytest tests/ -v --cov=. --cov-report=html --cov-report=term $PYTEST_ARGS
      echo ""
      echo "Coverage report generated at: file://$WORKSPACE_ROOT/app/htmlcov/index.html"
      ;;
    *)
      echo "ERROR: Mode '$MODE' not supported in local execution"
      echo "Use --docker flag for frontend/build/shell modes"
      exit 1
      ;;
  esac
}

# ============================================================================
# Docker Execution
# ============================================================================

run_docker() {
  cd "$WORKSPACE_ROOT"

  # Build environment arguments for docker compose
  # Docker defaults to LIVE mode (set in docker-compose.test.yml)
  # Only override if --mock flag is explicitly set
  ENV_ARGS=""
  if [ -n "$MOCK_MODE" ]; then
    ENV_ARGS="-e LIVE_API_TESTS=0"
  fi
  # Pass through token if set (for live mode)
  if [ -n "$HARDCOVER_API_TOKEN" ]; then
    ENV_ARGS="$ENV_ARGS -e HARDCOVER_API_TOKEN=$HARDCOVER_API_TOKEN"
  fi

  case "$MODE" in
    build)
      echo "Building Docker test image..."
      echo "Docker Compose file: $COMPOSE_FILE"
      echo "Service: $SERVICE_NAME"
      echo ""
      docker compose -f "$COMPOSE_FILE" build "$SERVICE_NAME"
      echo ""
      echo "Test image built successfully!"
      echo "Run tests with: ./run-tests.sh --docker"
      ;;
    shell)
      echo "Opening debug shell in test container..."
      docker compose -f "$COMPOSE_FILE" run --rm $ENV_ARGS $SERVICE_NAME sh
      ;;
    backend|"")
      echo "Running backend tests (Docker container)..."
      echo "🧹 Test databases managed by tmpfs volume (auto-cleaned)..."
      docker compose -f "$COMPOSE_FILE" run --rm $ENV_ARGS $SERVICE_NAME \
        pytest tests/ -v --tb=short $PYTEST_ARGS
      ;;
    frontend)
      echo "Running frontend tests (Docker container with Selenium)..."
      docker compose -f "$COMPOSE_FILE" run --rm $ENV_ARGS $SERVICE_NAME \
        pytest tests/frontend/ -v --tb=short $PYTEST_ARGS
      ;;
    coverage)
      echo "Running tests with coverage report (Docker container)..."
      docker compose -f "$COMPOSE_FILE" run --rm $ENV_ARGS $SERVICE_NAME \
        pytest tests/ -v --cov=. --cov-report=html --cov-report=term $PYTEST_ARGS
      echo ""
      echo "Coverage report is inside the container at: /app/htmlcov/index.html"
      echo "To extract: docker cp mam-test:/app/htmlcov ./htmlcov"
      ;;
  esac
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
  # Parse command-line arguments
  parse_args "$@"

  # Detect execution mode (local vs Docker)
  detect_mode

  # Validate flags and environment
  validate_flags
  validate_live_mode

  if [ "$EXEC_MODE" = "local" ]; then
    validate_local_env
    echo "▶ Execution mode: Local Python"
    [ -n "$LIVE_API" ] && echo "▶ API mode: Live (real API)" || echo "▶ API mode: Mock (fixtures)"
    echo ""
    run_local
  else
    validate_docker_available
    echo "▶ Execution mode: Docker container"
    # Docker defaults to live mode unless --mock is set
    [ -n "$MOCK_MODE" ] && echo "▶ API mode: Mock (fixtures)" || echo "▶ API mode: Live (real API)"
    echo ""
    run_docker
  fi
}

# Run main function with all arguments
main "$@"
