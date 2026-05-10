"""Local file storage service implementation."""

import os
import aiofiles
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.domain.interfaces.file_storage import IFileStorageService
from app.infrastructure.config import settings


class LocalFileStorageService(IFileStorageService):
    """Local file system implementation of file storage."""

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the file storage service.

        Args:
            base_dir: Base directory for file storage (defaults to settings.upload_dir)
        """
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        ext = Path(filename).suffix.lower()
        return ext in settings.allowed_file_extensions

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Get extension
        path = Path(filename)
        ext = path.suffix.lower()

        # Sanitize the stem (filename without extension)
        stem = path.stem
        # Remove special characters, keep spaces, letters, numbers, hyphens, underscores
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ")
        safe_stem = "".join(c if c in safe_chars else "_" for c in stem)

        # Add timestamp to prevent conflicts
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{safe_stem}_{timestamp}{ext}"

        return safe_filename[:255]  # Limit filename length

    async def save_upload(
        self,
        file_content: bytes,
        filename: str,
        folder: Optional[str] = None
    ) -> str:
        """
        Save uploaded file content and return the file path.

        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            folder: Optional subfolder

        Returns:
            Path where file was saved (relative to base_dir)
        """
        if not self.is_allowed_extension(filename):
            raise ValueError(f"File type not allowed: {filename}")

        # Validate file size
        if len(file_content) > settings.max_upload_size:
            raise ValueError(
                f"File size exceeds maximum allowed size of "
                f"{settings.max_upload_size / (1024 * 1024)}MB"
            )

        # Create folder if specified
        target_dir = self.base_dir
        if folder:
            target_dir = target_dir / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_filename = self.sanitize_filename(filename)
        file_path = target_dir / safe_filename

        # Write file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        # Return relative path
        relative_path = file_path.relative_to(self.base_dir)
        return str(relative_path).replace("\\", "/")

    async def upload_file(
        self,
        file_path: Path,
        filename: str,
        content_type: str,
        folder: Optional[str] = None
    ) -> str:
        """
        Upload a file and return its URL.

        For local storage, returns a file:// URL or relative path.
        """
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()

        relative_path = await self.save_upload(content, filename, folder)

        # For local files, return a path that can be served via static files
        return f"/static/uploads/{relative_path}"

    async def delete_file(self, file_url: str) -> bool:
        """Delete a file by its URL."""
        try:
            # Extract path from URL
            if file_url.startswith("/static/uploads/"):
                relative_path = file_url.replace("/static/uploads/", "")
                file_path = self.base_dir / relative_path

                if file_path.exists():
                    file_path.unlink()
                    return True
            return False
        except Exception:
            return False

    async def get_file_size(self, file_url: str) -> Optional[int]:
        """Get file size in bytes."""
        try:
            if file_url.startswith("/static/uploads/"):
                relative_path = file_url.replace("/static/uploads/", "")
                file_path = self.base_dir / relative_path

                if file_path.exists():
                    return file_path.stat().st_size
            return None
        except Exception:
            return None
