"""File storage service interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from pathlib import Path


class IFileStorageService(ABC):
    """Port: File storage service interface."""

    @abstractmethod
    async def upload_file(
        self,
        file_path: Path,
        filename: str,
        content_type: str,
        folder: Optional[str] = None
    ) -> str:
        """
        Upload a file and return its URL.

        Args:
            file_path: Path to the file to upload
            filename: Original filename
            content_type: MIME type of the file
            folder: Optional folder/path prefix

        Returns:
            URL where the file can be accessed
        """
        pass

    @abstractmethod
    async def delete_file(self, file_url: str) -> bool:
        """
        Delete a file by its URL.

        Args:
            file_url: URL of the file to delete

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def get_file_size(self, file_url: str) -> Optional[int]:
        """Get file size in bytes."""
        pass

    @abstractmethod
    def is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        pass

    @abstractmethod
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        pass

    @abstractmethod
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
            Path where file was saved (relative or absolute)
        """
        pass
