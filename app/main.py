"""
MAM Audiobook Finder - Main Application Bootstrap
A lightweight web application for searching MAM audiobooks,
adding them to qBittorrent, and importing to Audiobookshelf.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import configuration first
from config import LOG_MAX_MB, LOG_MAX_FILES, LOG_DIR, DEBUG_MODE

# ---------------------------- Logging Setup ----------------------------
# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create logger
logger = logging.getLogger("mam-audiofinder")

# Set log level based on DEBUG_MODE environment variable
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# Clear any existing handlers
logger.handlers.clear()

# Console handler for Docker (always active)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
console_formatter = logging.Formatter('%(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler with rotation
log_file = LOG_DIR / "app.log"
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=LOG_MAX_MB * 1024 * 1024,  # Convert MB to bytes
    backupCount=LOG_MAX_FILES
)
file_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

logger.info(f"Logging initialized: {log_file} (max {LOG_MAX_MB}MB, {LOG_MAX_FILES} files)")
if DEBUG_MODE:
    logger.debug("🔍 Debug mode enabled")

# ---------------------------- Database Initialization ----------------------------
from db import initialize_databases
from config import DATA_DIR

try:
    logger.info("="*70)
    logger.info("🗃️  Initializing database schemas...")
    logger.info("="*70)
    initialize_databases()
    logger.info("="*70)
    logger.info("✅ All database schemas initialized successfully")
    logger.info("="*70)
except Exception as e:
    logger.error("="*70)
    logger.error(f"❌ Database initialization failed: {e}")
    logger.error("="*70)
    logger.error("💡 Tip: Check for stale databases or schema mismatches")
    logger.error(f"📁 Data directory: {DATA_DIR}")
    raise

# ---------------------------- FastAPI Application ----------------------------
app = FastAPI(title="MAM Audiobook Finder", version="0.4.0")

# Mount static files (including Vue build output at /static/dist)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include all routes
from routes import main_router
app.include_router(main_router)

# ---------------------------- SPA Fallback ----------------------------
# Serve Vue SPA for any route not matched by API endpoints
# This must come AFTER all API routes are registered

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """
    Fallback route for Vue Router history mode.
    Serves the SPA index.html for any GET request not handled by API routes.
    """
    return FileResponse("static/dist/index.html")

# ---------------------------- Startup Event ----------------------------
from abs_client import abs_client

@app.on_event("startup")
async def startup_event():
    """Run startup tests."""
    logger.info("🚀 Starting MAM Audiobook Finder v0.4.0")
    await abs_client.test_connection()
    logger.info("✅ Application startup complete")
