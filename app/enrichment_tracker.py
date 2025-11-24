"""
Enrichment Tracker - Manages background enrichment jobs for series books.

Provides in-memory tracking of enrichment progress for series books,
allowing immediate response with basic data while enrichment happens in background.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class EnrichmentJob:
    """Represents a single enrichment job for a series."""

    def __init__(self, series_id: str, total_books: int):
        self.series_id = series_id
        self.total_books = total_books
        self.completed_books = 0
        self.enriched_books: List[Dict[str, Any]] = []
        self.status = "pending"  # pending, in_progress, complete, failed
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self._lock = asyncio.Lock()

    async def add_enriched_book(self, book: Dict[str, Any]):
        """Add an enriched book to the job results."""
        async with self._lock:
            self.enriched_books.append(book)
            self.completed_books += 1

            if self.completed_books >= self.total_books:
                self.status = "complete"
                self.completed_at = datetime.utcnow()
                duration = (self.completed_at - self.started_at).total_seconds()
                logger.info(f"✅ Enrichment complete for series {self.series_id}: "
                          f"{self.completed_books}/{self.total_books} books in {duration:.1f}s")

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        return {
            "total": self.total_books,
            "completed": self.completed_books,
            "percentage": int((self.completed_books / self.total_books * 100)) if self.total_books > 0 else 0
        }

    def is_expired(self, ttl_seconds: int = 300) -> bool:
        """Check if job is expired (default: 5 minutes)."""
        age = (datetime.utcnow() - self.started_at).total_seconds()
        return age > ttl_seconds


class EnrichmentTracker:
    """
    In-memory tracker for series enrichment jobs.

    Manages concurrent enrichment jobs, tracks progress, and stores results
    temporarily for progressive loading in the frontend.
    """

    def __init__(self, max_jobs: int = 100, job_ttl: int = 300):
        """
        Initialize enrichment tracker.

        Args:
            max_jobs: Maximum number of jobs to track (LRU eviction)
            job_ttl: Time-to-live for completed jobs in seconds (default: 5 minutes)
        """
        self._jobs: Dict[str, EnrichmentJob] = {}
        self._lock = asyncio.Lock()
        self.max_jobs = max_jobs
        self.job_ttl = job_ttl
        logger.info(f"📦 EnrichmentTracker initialized (max_jobs={max_jobs}, ttl={job_ttl}s)")

    async def start_job(self, series_id: str, total_books: int) -> EnrichmentJob:
        """
        Start a new enrichment job or return existing in-progress job.

        Args:
            series_id: Unique identifier for the series
            total_books: Total number of books to enrich

        Returns:
            EnrichmentJob instance
        """
        async with self._lock:
            # Check if job already exists and is still running
            existing_job = self._jobs.get(series_id)
            if existing_job:
                if existing_job.status in ("pending", "in_progress"):
                    logger.info(
                        f"⚠️  Enrichment job for series {series_id} already in progress "
                        f"(status={existing_job.status}, progress={existing_job.completed_books}/{existing_job.total_books}), "
                        f"reusing existing job"
                    )
                    return existing_job
                else:
                    logger.info(f"🔄 Replacing {existing_job.status} job for series {series_id} with new job")

            # Clean up expired jobs if at capacity
            if len(self._jobs) >= self.max_jobs:
                await self._cleanup_expired_jobs()

            # Create new job
            job = EnrichmentJob(series_id, total_books)
            job.status = "in_progress"
            self._jobs[series_id] = job

            logger.info(f"🔄 Started enrichment job for series {series_id} ({total_books} books)")
            return job

    async def update_progress(self, series_id: str, enriched_book: Dict[str, Any]):
        """
        Update progress for an enrichment job by adding an enriched book.

        Args:
            series_id: Series identifier
            enriched_book: Enriched book data
        """
        async with self._lock:
            job = self._jobs.get(series_id)
            if not job:
                logger.warning(f"⚠️ No job found for series {series_id}, cannot update progress")
                return

        # Add book (uses job's own lock internally)
        await job.add_enriched_book(enriched_book)

    async def mark_failed(self, series_id: str, error: str):
        """
        Mark a job as failed.

        Args:
            series_id: Series identifier
            error: Error message
        """
        async with self._lock:
            job = self._jobs.get(series_id)
            if job:
                job.status = "failed"
                job.error = error
                job.completed_at = datetime.utcnow()
                logger.error(f"❌ Enrichment failed for series {series_id}: {error}")

    async def get_status(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an enrichment job.

        Args:
            series_id: Series identifier

        Returns:
            Status dictionary or None if job not found
        """
        async with self._lock:
            job = self._jobs.get(series_id)
            if not job:
                return None

            return {
                "series_id": series_id,
                "status": job.status,
                "progress": job.get_progress(),
                "enriched_books": job.enriched_books.copy(),
                "started_at": job.started_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error": job.error
            }

    async def get_enriched_books(self, series_id: str) -> List[Dict[str, Any]]:
        """
        Get all enriched books for a series.

        Args:
            series_id: Series identifier

        Returns:
            List of enriched books (may be partial if job still in progress)
        """
        async with self._lock:
            job = self._jobs.get(series_id)
            if not job:
                return []
            return job.enriched_books.copy()

    async def cleanup_job(self, series_id: str):
        """
        Remove a job from tracking.

        Args:
            series_id: Series identifier
        """
        async with self._lock:
            if series_id in self._jobs:
                del self._jobs[series_id]
                logger.debug(f"🗑️ Cleaned up job for series {series_id}")

    async def _cleanup_expired_jobs(self):
        """Clean up expired jobs (internal, must be called with lock held)."""
        expired = [
            sid for sid, job in self._jobs.items()
            if job.status in ("complete", "failed") and job.is_expired(self.job_ttl)
        ]

        for sid in expired:
            del self._jobs[sid]

        if expired:
            logger.info(f"🗑️ Cleaned up {len(expired)} expired enrichment jobs")

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics (for debugging/monitoring)."""
        stats = {
            "total_jobs": len(self._jobs),
            "pending": sum(1 for j in self._jobs.values() if j.status == "pending"),
            "in_progress": sum(1 for j in self._jobs.values() if j.status == "in_progress"),
            "complete": sum(1 for j in self._jobs.values() if j.status == "complete"),
            "failed": sum(1 for j in self._jobs.values() if j.status == "failed"),
        }
        return stats


# Global singleton instance
_tracker: Optional[EnrichmentTracker] = None


def get_tracker() -> EnrichmentTracker:
    """Get the global enrichment tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = EnrichmentTracker()
    return _tracker
