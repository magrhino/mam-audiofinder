"""
Database module for MAM Audiobook Finder.
Handles database engine setup and migration execution.
"""
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from config import HISTORY_DB_PATH, COVERS_DB_PATH, SERIES_DB_PATH

logger = logging.getLogger("mam-audiofinder")

# ---------------------------- Database Engines ----------------------------
# Main history database
engine = create_engine(f"sqlite:///{HISTORY_DB_PATH}", future=True)
# Alias for backward compatibility
history_engine = engine

# Covers database - separate from history to cache covers before adding to qBittorrent
# Configure connection pool to handle concurrent cover fetches better
covers_engine = create_engine(
    f"sqlite:///{COVERS_DB_PATH}",
    future=True,
    pool_size=20,  # Increased from default 5
    max_overflow=30,  # Increased from default 10
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600  # Recycle connections after 1 hour
)

# Series database - permanent cache for series metadata and resolved editions
# Separated from covers.db to provide dedicated storage for series operations
series_engine = create_engine(
    f"sqlite:///{SERIES_DB_PATH}",
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

def get_db_engine():
    """
    Get the database engine for covers and series cache operations.

    Returns:
        Engine: SQLAlchemy engine for covers.db (contains covers and series_cache tables)
    """
    return covers_engine

def get_series_engine():
    """
    Get the database engine for series metadata and resolved editions.

    Returns:
        Engine: SQLAlchemy engine for series.db (contains series_metadata, resolved_editions, book_metadata tables)
    """
    return series_engine

# ---------------------------- Migration System ----------------------------
MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def _ensure_migrations_table(target_engine):
    """Ensure the applied_migrations tracking table exists."""
    with target_engine.begin() as cx:
        cx.execute(text("""
            CREATE TABLE IF NOT EXISTS applied_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now'))
            )
        """))


def run_migrations():
    """
    Execute all SQL migration files in order.
    Migration files are named numerically (001_xxx.sql, 002_xxx.sql, etc.)
    and are executed in order. Each statement is executed independently
    to allow idempotent migrations (e.g., ALTER TABLE ADD COLUMN IF NOT EXISTS).
    """
    if not MIGRATIONS_DIR.exists():
        logger.warning(f"⚠️  Migrations directory not found: {MIGRATIONS_DIR}")
        return

    # Get all .sql files sorted numerically (skip DEPRECATED_* files)
    migration_files = sorted([
        f for f in MIGRATIONS_DIR.glob("*.sql")
        if not f.name.startswith("DEPRECATED_")
    ])

    if not migration_files:
        logger.info("ℹ️  No migration files found")
        return

    logger.info(f"🔧 Checking {len(migration_files)} migration(s)...")

    # Track which database each migration applies to
    # Migrations 001-004 are for history.db, 005+ are for covers.db, 011+ may be for series.db
    # Ensure tracking tables exist
    _ensure_migrations_table(engine)
    _ensure_migrations_table(covers_engine)
    _ensure_migrations_table(series_engine)

    pending = 0
    for migration_file in migration_files:
        # Determine target database by examining SQL content
        migration_num = int(migration_file.stem.split("_")[0])
        sql_content = migration_file.read_text().lower()

        # Smart routing: check which table the migration targets
        targets_history = any(pattern in sql_content for pattern in [
            "alter table history",
            "create table history",
            "create table if not exists history",
            "insert into history",
            "create index if not exists idx_history",
            "library_wishlist",
            "app_settings",
            "auto_import_tracking"
        ])

        targets_covers = any(pattern in sql_content for pattern in [
            "alter table covers",
            "create table covers",
            "create table if not exists covers",
            "insert into covers",
            "create index if not exists idx_covers",
            "series_cache"  # Series cache table belongs in covers.db
        ])

        targets_series = any(pattern in sql_content for pattern in [
            "series_metadata",
            "resolved_editions",
            "book_metadata",
            "alter table series_metadata",
            "alter table resolved_editions",
            "alter table book_metadata",
            "create table series_metadata",
            "create table resolved_editions",
            "create table book_metadata"
        ])

        # Determine target engine
        if targets_series:
            target_engine = series_engine
            db_name = "series.db"
        elif targets_history and not targets_covers:
            target_engine = engine
            db_name = "history.db"
        elif targets_covers and not targets_history:
            target_engine = covers_engine
            db_name = "covers.db"
        else:
            # Fallback to legacy logic for migrations that don't clearly target one table
            target_engine = covers_engine if migration_num >= 5 else engine
            db_name = "covers.db" if migration_num >= 5 else "history.db"

        with target_engine.begin() as cx:
            exists = cx.execute(
                text("SELECT 1 FROM applied_migrations WHERE filename = :filename"),
                {"filename": migration_file.name}
            ).fetchone()

        if exists:
            logger.debug(f"  ↺ Skipping already applied migration {migration_file.name}")
            continue

        pending += 1
        logger.info(f"  → {migration_file.name} (target: {db_name})")

        try:
            # Use already-read SQL content (avoid reading file twice)
            sql = migration_file.read_text()

            # Check if migration contains triggers (which have BEGIN/END blocks)
            contains_trigger = "CREATE TRIGGER" in sql.upper()

            if contains_trigger:
                # Use executescript for files with triggers (handles BEGIN/END properly)
                with target_engine.connect() as conn:
                    # Get raw sqlite connection
                    raw_conn = conn.connection.driver_connection
                    try:
                        raw_conn.executescript(sql)
                        conn.commit()
                    except Exception as e:
                        # Log error but don't fail (allows idempotent migrations)
                        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                            logger.debug(f"    ⊘ Skipped (already exists)")
                        else:
                            logger.warning(f"    ⚠️  Error executing migration: {e}")
            else:
                # Split into individual statements (handles multi-statement files)
                raw_statements = [s.strip() for s in sql.split(";") if s.strip()]

                # Clean comments from each statement
                statements = []
                for stmt in raw_statements:
                    # Remove comment-only lines but keep actual SQL
                    lines = [
                        line.strip()
                        for line in stmt.split("\n")
                        if line.strip() and not line.strip().startswith("--")
                    ]
                    clean_stmt = "\n".join(lines)
                    if clean_stmt:
                        statements.append(clean_stmt)

                # Execute each statement in its own transaction (SQLite requirement)
                # This prevents one failed statement from invalidating subsequent ones
                for statement in statements:
                    try:
                        with target_engine.begin() as cx:
                            cx.execute(text(statement))
                    except Exception as e:
                        # Log but don't fail - allows idempotent migrations
                        # (e.g., "ALTER TABLE ADD COLUMN" on already existing column)
                        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                            logger.debug(f"    ⊘ Skipped (already exists): {statement[:50]}...")
                        else:
                            logger.warning(f"    ⚠️  Error executing statement: {e}")
                            logger.debug(f"    Statement: {statement}")

            with target_engine.begin() as cx:
                cx.execute(
                    text("INSERT INTO applied_migrations (filename, applied_at) VALUES (:filename, :applied_at)"),
                    {"filename": migration_file.name, "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
                )

            logger.info(f"    ✓ {migration_file.name} completed")

        except Exception as e:
            logger.error(f"    ✗ Migration failed: {migration_file.name}: {e}")
            # Continue with other migrations instead of failing

    if pending == 0:
        logger.info("✓ Database migrations already up to date")
    else:
        logger.info("✓ Database migrations completed")

def _initialize_covers_db_from_schema():
    """
    Initialize covers.db from fresh schema file with validation.
    Auto-rebuilds if schema validation fails.
    """
    schema_file = Path(__file__).parent / "covers_schema.sql"
    if not schema_file.exists():
        logger.warning(f"⚠️  Covers schema file not found: {schema_file}")
        return

    expected_tables = ["covers", "series_cache", "library_items", "library_sync_status"]

    # Validate existing database
    db_path = Path(COVERS_DB_PATH)
    if db_path.exists():
        if _validate_database_schema(covers_engine, expected_tables, "covers.db"):
            logger.info("✓ covers.db schema up to date, skipping initialization")
            return
        else:
            logger.warning("⚠️  covers.db schema invalid, rebuilding...")
            logger.warning(f"⚠️  Deleting stale database: {db_path}")
            try:
                db_path.unlink()
                logger.info("✓ Deleted stale covers.db")
            except Exception as e:
                logger.error(f"✗ Failed to delete {db_path}: {e}")
                raise

    logger.info("🔧 Initializing covers.db from fresh schema...")

    try:
        sql = schema_file.read_text()
        with covers_engine.connect() as conn:
            raw_conn = conn.connection.driver_connection
            raw_conn.executescript(sql)
            conn.commit()

        logger.info("✓ Covers database schema initialized")

        # Verify initialization succeeded
        if not _validate_database_schema(covers_engine, expected_tables, "covers.db"):
            raise RuntimeError("covers.db schema initialization failed validation")
    except Exception as e:
        logger.error(f"✗ Failed to initialize covers.db from schema: {e}")
        raise

def _initialize_series_db_from_schema():
    """
    Initialize series.db from fresh schema file with validation.
    Auto-rebuilds if schema validation fails.
    """
    schema_file = Path(__file__).parent / "series_schema.sql"
    if not schema_file.exists():
        logger.warning(f"⚠️  Series schema file not found: {schema_file}")
        return

    expected_tables = ["series_metadata", "resolved_editions", "book_metadata"]

    # Validate existing database
    db_path = Path(SERIES_DB_PATH)
    if db_path.exists():
        if _validate_database_schema(series_engine, expected_tables, "series.db"):
            logger.info("✓ series.db schema up to date, skipping initialization")
            return
        else:
            logger.warning("⚠️  series.db schema invalid, rebuilding...")
            logger.warning(f"⚠️  Deleting stale database: {db_path}")
            try:
                db_path.unlink()
                logger.info("✓ Deleted stale series.db")
            except Exception as e:
                logger.error(f"✗ Failed to delete {db_path}: {e}")
                raise

    logger.info("🔧 Initializing series.db from fresh schema...")

    try:
        sql = schema_file.read_text()
        with series_engine.connect() as conn:
            raw_conn = conn.connection.driver_connection
            raw_conn.executescript(sql)
            conn.commit()

        logger.info("✓ Series database schema initialized")

        # Verify initialization succeeded
        if not _validate_database_schema(series_engine, expected_tables, "series.db"):
            raise RuntimeError("series.db schema initialization failed validation")
    except Exception as e:
        logger.error(f"✗ Failed to initialize series.db from schema: {e}")
        raise


def _validate_database_schema(engine, expected_tables, db_name):
    """
    Validate that all expected tables exist in the database.
    Returns True if valid, False if rebuild needed.
    """
    logger.info(f"🔍 Validating {db_name} schema...")

    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ))
            existing_tables = {row[0] for row in result.fetchall()}

            missing_tables = set(expected_tables) - existing_tables

            if missing_tables:
                logger.warning(
                    f"⚠️  {db_name} missing tables: {', '.join(sorted(missing_tables))}"
                )
                return False

            logger.info(f"✓ {db_name} schema valid ({len(expected_tables)} tables)")
            return True

    except Exception as e:
        logger.error(f"✗ Schema validation failed for {db_name}: {e}")
        return False


def initialize_databases():
    """Initialize database schemas by running migrations and fresh schemas."""
    # Initialize covers.db from fresh schema (replaces migrations 005, 008, 009)
    _initialize_covers_db_from_schema()

    # Initialize series.db from fresh schema
    _initialize_series_db_from_schema()

    # Run migrations for history.db and series.db (skips DEPRECATED_* files)
    run_migrations()

    logger.info("✓ Database schemas initialized")
