"""
qBittorrent session management and torrent operation dependencies.

Provides:
- get_qb_sync_client: Logged-in sync httpx client
- get_qb_async_client: Logged-in async httpx client
- require_torrent_info: Fetch torrent properties/files with error mapping
- map_qb_content_path: Shared path mapper with existence checks
"""

from typing import Generator, Dict, Any
from pathlib import Path
import httpx
from fastapi import HTTPException, Depends

from config import QB_URL, QB_USER, QB_PASS, DL_DIR, QB_INNER_DL_PREFIX
from qb_client import qb_login_sync, qb_login


def get_qb_sync_client() -> Generator[httpx.Client, None, None]:
    """
    Yields a logged-in synchronous qBittorrent httpx client.

    Handles authentication errors uniformly with proper HTTPException mapping.
    Uses per-request lifetime to avoid cookie leakage.

    Raises:
        HTTPException: 502 if qBittorrent is unreachable or login fails
    """
    client = httpx.Client(timeout=30.0)
    try:
        qb_login_sync(client)
        yield client
    except HTTPException:
        # Re-raise HTTPException from qb_login_sync
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"qBittorrent unavailable: {str(e)}"
        )
    finally:
        client.close()


async def get_qb_async_client():
    """
    Yields a logged-in asynchronous qBittorrent httpx client.

    Handles authentication errors uniformly with proper HTTPException mapping.
    Uses per-request lifetime to avoid cookie leakage.

    Raises:
        HTTPException: 502 if qBittorrent is unreachable or login fails
    """
    client = httpx.AsyncClient(timeout=30.0)
    try:
        await qb_login(client)
        yield client
    except HTTPException:
        # Re-raise HTTPException from qb_login
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"qBittorrent unavailable: {str(e)}"
        )
    finally:
        await client.aclose()


def require_torrent_info(
    torrent_hash: str,
    client: httpx.Client = Depends(get_qb_sync_client)
) -> Dict[str, Any]:
    """
    Fetches torrent properties, files, and content_path with error mapping.

    Args:
        torrent_hash: The torrent hash to fetch info for
        client: Logged-in qBittorrent client (injected)

    Returns:
        Dictionary containing:
            - properties: Torrent properties
            - files: List of files in torrent
            - content_path: Content path from properties

    Raises:
        HTTPException: 502 if qBittorrent request fails, 404 if torrent not found
    """
    try:
        # Fetch torrent properties
        props_resp = client.get(
            f"{QB_URL}/api/v2/torrents/properties",
            params={"hash": torrent_hash}
        )

        if props_resp.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Torrent {torrent_hash} not found"
            )

        props_resp.raise_for_status()
        properties = props_resp.json()

        # Fetch torrent files
        files_resp = client.get(
            f"{QB_URL}/api/v2/torrents/files",
            params={"hash": torrent_hash}
        )
        files_resp.raise_for_status()
        files = files_resp.json()

        return {
            "properties": properties,
            "files": files,
            "content_path": properties.get("content_path", "")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch torrent info: {str(e)}"
        )


def map_qb_content_path(content_path: str, validate_exists: bool = True) -> Path:
    """
    Maps qBittorrent content_path to container filesystem path.

    Handles QB_INNER_DL_PREFIX replacement, /media/ passthrough, and path normalization.
    This centralizes the logic that was duplicated across import_route.py and qbittorrent.py.

    Args:
        content_path: qBittorrent content_path from torrent properties
        validate_exists: Whether to validate that the mapped path exists (default: True)

    Returns:
        Resolved Path object pointing to content

    Raises:
        HTTPException: 404 if validate_exists=True and mapped path does not exist
    """
    # Normalize the path using the shared mapping logic
    mapped = content_path

    # Replace QB_INNER_DL_PREFIX with DL_DIR
    if QB_INNER_DL_PREFIX:
        prefix = QB_INNER_DL_PREFIX.rstrip("/")
        if mapped == prefix or mapped.startswith(prefix + "/"):
            mapped = mapped.replace(QB_INNER_DL_PREFIX, DL_DIR, 1)

    # Passthrough /media/ paths
    if mapped.startswith("/media/"):
        pass  # Already correct
    else:
        # Normalize /mnt/user/media and /mnt/media to /media
        mapped = mapped.replace("/mnt/user/media", "/media", 1)
        mapped = mapped.replace("/mnt/media", "/media", 1)

    resolved = Path(mapped)

    if validate_exists and not resolved.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Content path not found: {resolved} (original: {content_path})"
        )

    return resolved
