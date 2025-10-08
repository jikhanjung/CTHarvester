"""
FileHandler - Handles file operations and directory management

Extracted from ui/main_window.py during Phase 1 refactoring.
Provides file listing, sorting, and metadata extraction for CT image stacks.
"""

import logging
import os
import re
from typing import Dict, List, Optional

from PIL import Image

from security.file_validator import FileSecurityError, SecureFileValidator
from utils.image_utils import get_image_dimensions

logger = logging.getLogger(__name__)


class FileHandlerError(Exception):
    """Base exception for FileHandler errors"""

    pass


class NoImagesFoundError(FileHandlerError):
    """Raised when no valid CT images found in directory"""

    pass


class InvalidImageFormatError(FileHandlerError):
    """Raised when image format is not supported"""

    pass


class CorruptedImageError(FileHandlerError):
    """Raised when image file is corrupted or unreadable"""

    pass


class FileHandler:
    """Manages file operations for CT image stacks

    This class provides robust file handling for CT image sequences,
    including pattern detection, natural sorting, and metadata extraction.

    Features:
        - Directory scanning with security validation
        - Automatic file pattern detection (prefix, extension, numbering)
        - Image metadata extraction (dimensions, sequence range)
        - Natural sorting (1, 2, 10 not 1, 10, 2)
        - Support for multiple image formats (TIFF, BMP, JPEG, PNG)

    Example:
        >>> handler = FileHandler()
        >>> settings = handler.open_directory('/path/to/ct/images')
        >>> if settings:
        ...     print(f"Found {settings['seq_end'] - settings['seq_begin'] + 1} images")
        ...     print(f"Image size: {settings['image_width']}x{settings['image_height']}")
        ...     files = handler.get_file_list('/path/to/ct/images', settings)

    Thread Safety:
        This class is thread-safe for read operations. Multiple instances
        can be used concurrently without issues.
    """

    # Supported image extensions
    SUPPORTED_EXTENSIONS = {".tif", ".tiff", ".bmp", ".jpg", ".jpeg", ".png"}

    def __init__(self) -> None:
        """Initialize file handler"""
        self.validator = SecureFileValidator()

    def open_directory(self, directory_path: str) -> Dict:
        """Open and analyze a directory containing CT images

        Args:
            directory_path (str): Path to directory to analyze

        Returns:
            Dict: Settings dictionary with file information
                {
                    'prefix': str,
                    'file_type': str,
                    'image_width': int,
                    'image_height': int,
                    'seq_begin': int,
                    'seq_end': int,
                    'index_length': int
                }

        Raises:
            FileSecurityError: If path validation fails
            FileNotFoundError: If directory does not exist
            NotADirectoryError: If path is not a directory
            PermissionError: If directory is not accessible
            NoImagesFoundError: If no valid CT images found
            OSError: For other OS-level errors
        """
        # Validate directory path
        validated_path = self.validator.validate_path(directory_path, directory_path)

        if not os.path.exists(validated_path):
            logger.error(f"Directory does not exist: {validated_path}")
            raise FileNotFoundError(f"Directory does not exist: {validated_path}")

        if not os.path.isdir(validated_path):
            logger.error(f"Path is not a directory: {validated_path}")
            raise NotADirectoryError(f"Path is not a directory: {validated_path}")

        logger.info(f"Opening directory: {validated_path}")

        # Analyze files in directory
        settings_hash = self.sort_file_list_from_dir(validated_path)

        logger.info(
            f"Directory analysis complete: {settings_hash['prefix']}*.{settings_hash['file_type']}, "
            f"{settings_hash['seq_end'] - settings_hash['seq_begin'] + 1} images, "
            f"{settings_hash['image_width']}x{settings_hash['image_height']}"
        )

        return settings_hash

    def sort_file_list_from_dir(self, directory_path: str) -> Dict:
        """Analyze and sort files in directory to detect CT image stack pattern

        Detects the most common file prefix and extension pattern, then extracts
        sequence information and image metadata.

        Args:
            directory_path (str): Path to directory containing CT images

        Returns:
            Dict: Settings dictionary with detected pattern
                {
                    'prefix': str - Common file prefix (e.g., 'slice_')
                    'file_type': str - File extension (e.g., 'tif')
                    'image_width': int - Image width in pixels
                    'image_height': int - Image height in pixels
                    'seq_begin': int - First sequence number
                    'seq_end': int - Last sequence number
                    'index_length': int - Number of digits in sequence (e.g., 4 for '0001')
                }

        Raises:
            NoImagesFoundError: If no valid CT images found
            InvalidImageFormatError: If no supported image formats found
            CorruptedImageError: If image files are unreadable
            PermissionError: If directory access is denied
            OSError: For other OS-level errors

        Algorithm:
            1. List all files in directory
            2. Extract prefix and extension using regex: (prefix)(number).(ext)
            3. Find most common prefix and extension
            4. Filter files matching the pattern
            5. Extract sequence range and image metadata
        """
        # Step 1: Get all files in directory
        all_files = [
            f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))
        ]

        if not all_files:
            logger.warning(f"No files found in directory: {directory_path}")
            raise NoImagesFoundError(f"No files found in directory: {directory_path}")

        logger.info(f"Found {len(all_files)} files in directory")

        # Step 2: Regular expression pattern to match: (prefix)(digits).(extension)
        # Example: "slice_0001.tif" -> prefix="slice_", digits="0001", extension="tif"
        pattern = r"^(.*?)(\d+)\.(\w+)$"

        ct_stack_files = []
        matching_files = []
        other_files = []
        prefix_hash: Dict[str, int] = {}
        extension_hash: Dict[str, int] = {}

        # Step 3: Analyze all files
        for file in all_files:
            match = re.match(pattern, file)
            if match:
                matching_files.append(file)

                # Count prefix occurrences
                prefix = match.group(1)
                if prefix in prefix_hash:
                    prefix_hash[prefix] += 1
                else:
                    prefix_hash[prefix] = 1

                # Count extension occurrences
                extension = match.group(3).lower()
                if extension in extension_hash:
                    extension_hash[extension] += 1
                else:
                    extension_hash[extension] = 1
            else:
                other_files.append(file)

        if not matching_files:
            logger.warning("No files matching CT stack pattern found")
            raise NoImagesFoundError(
                f"No files matching CT stack pattern found in: {directory_path}"
            )

        # Step 4: Determine most common prefix
        max_prefix_count = 0
        max_prefix = ""
        for prefix, count in prefix_hash.items():
            if count > max_prefix_count:
                max_prefix_count = count
                max_prefix = prefix

        logger.info(f"Most common prefix: '{max_prefix}' ({max_prefix_count} files)")

        # Step 5: Determine most common extension (and validate it's supported)
        max_extension_count = 0
        max_extension = ""
        for extension, count in extension_hash.items():
            ext_with_dot = f".{extension}"
            if ext_with_dot.lower() in self.SUPPORTED_EXTENSIONS and count > max_extension_count:
                max_extension_count = count
                max_extension = extension

        if not max_extension:
            logger.warning("No supported image format found")
            raise InvalidImageFormatError(
                f"No supported image formats found in: {directory_path}. "
                f"Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        logger.info(f"Most common extension: '{max_extension}' ({max_extension_count} files)")

        # Step 6: Filter files matching the most common prefix and extension
        for file in matching_files:
            match = re.match(pattern, file)
            if (
                match
                and match.group(1) == max_prefix
                and match.group(3).lower() == max_extension.lower()
            ):
                ct_stack_files.append(file)

        if not ct_stack_files:
            logger.warning("No CT stack files matched the pattern")
            raise NoImagesFoundError(f"No CT stack files matched the pattern in: {directory_path}")

        # Sort files naturally (by numeric value, not string)
        ct_stack_files = self._natural_sort(ct_stack_files, pattern)

        logger.info(f"Found {len(ct_stack_files)} files in CT stack")

        # Step 7: Extract metadata from first and last files
        first_file = ct_stack_files[0]
        last_file = ct_stack_files[-1]
        first_file_path = os.path.join(directory_path, first_file)

        # Get image dimensions from first file
        try:
            width, height = get_image_dimensions(first_file_path)
        except Exception as e:
            logger.error(f"Failed to read image dimensions from {first_file_path}: {e}")
            raise CorruptedImageError(
                f"Failed to read image file: {first_file}. File may be corrupted."
            ) from e

        # Extract sequence information
        match1 = re.match(pattern, first_file)
        match2 = re.match(pattern, last_file)

        if not match1 or not match2:
            logger.error("Failed to match pattern for first/last files")
            raise NoImagesFoundError("Failed to extract sequence information from file names")

        start_index = int(match1.group(2))
        end_index = int(match2.group(2))
        seq_length = len(match1.group(2))

        # Build settings dictionary
        settings_hash = {
            "prefix": max_prefix,
            "image_width": width,
            "image_height": height,
            "file_type": max_extension,
            "index_length": seq_length,
            "seq_begin": start_index,
            "seq_end": end_index,
        }

        return settings_hash

    def _natural_sort(self, file_list: List[str], pattern: str) -> List[str]:
        """Sort files naturally by numeric sequence

        Example: ['file1.tif', 'file10.tif', 'file2.tif']
        -> ['file1.tif', 'file2.tif', 'file10.tif']

        Args:
            file_list (List[str]): List of filenames to sort
            pattern (str): Regex pattern to extract numeric part

        Returns:
            List[str]: Naturally sorted file list
        """

        def extract_number(filename: str) -> int:
            match = re.match(pattern, filename)
            if match:
                return int(match.group(2))  # Extract numeric part
            return 0

        return sorted(file_list, key=extract_number)

    def get_file_list(self, directory_path: str, settings_hash: Dict) -> List[str]:
        """Get sorted list of CT image file paths based on detected pattern

        Args:
            directory_path (str): Base directory path
            settings_hash (Dict): Settings from sort_file_list_from_dir()

        Returns:
            List[str]: Full paths to image files in sequence
        """
        prefix = settings_hash["prefix"]
        extension = settings_hash["file_type"]
        seq_begin = settings_hash["seq_begin"]
        seq_end = settings_hash["seq_end"]
        index_length = settings_hash["index_length"]

        file_list = []
        missing_files = []
        MAX_MISSING_WARNINGS = 10  # Only log first N missing files

        for i in range(seq_begin, seq_end + 1):
            # Format with leading zeros based on index_length
            filename = f"{prefix}{i:0{index_length}d}.{extension}"
            filepath = os.path.join(directory_path, filename)

            if os.path.exists(filepath):
                file_list.append(filepath)
            else:
                missing_files.append(filename)
                # Only log first few missing files to avoid log spam
                if len(missing_files) <= MAX_MISSING_WARNINGS:
                    logger.warning(f"Expected file not found: {filename}")

        # Summary log for missing files
        if missing_files:
            total_missing = len(missing_files)
            total_expected = seq_end - seq_begin + 1
            logger.info(
                f"File list generated: {len(file_list)}/{total_expected} files found, "
                f"{total_missing} missing"
            )
            if total_missing > MAX_MISSING_WARNINGS:
                logger.warning(
                    f"... and {total_missing - MAX_MISSING_WARNINGS} more files not found "
                    f"(showing first {MAX_MISSING_WARNINGS} only)"
                )
        else:
            logger.info(f"Generated file list: {len(file_list)} files")

        return file_list

    def validate_directory_structure(self, directory_path: str) -> bool:
        """Validate that directory is suitable for CT processing

        Checks:
        - Directory exists and is readable
        - Contains at least some image files
        - No security violations

        Args:
            directory_path (str): Directory to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Security validation
            validated_path = self.validator.validate_path(directory_path, directory_path)

            # Existence check
            if not os.path.exists(validated_path):
                logger.error(f"Directory does not exist: {validated_path}")
                return False

            if not os.path.isdir(validated_path):
                logger.error(f"Path is not a directory: {validated_path}")
                return False

            # Readability check
            if not os.access(validated_path, os.R_OK):
                logger.error(f"Directory is not readable: {validated_path}")
                return False

            # Check for image files
            files = os.listdir(validated_path)
            image_files = [
                f
                for f in files
                if any(f.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)
            ]

            if not image_files:
                logger.warning(f"No image files found in directory: {validated_path}")
                return False

            logger.info(f"Directory validation passed: {len(image_files)} image files found")
            return True

        except FileSecurityError as e:
            logger.error(f"Security validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Directory validation error: {e}")
            return False

    def find_log_file(self, directory_path: str) -> Optional[str]:
        """Find CT scanner log file in directory

        Looks for common log file patterns (e.g., .log, .txt with specific names)

        Args:
            directory_path (str): Directory to search

        Returns:
            Optional[str]: Path to log file if found, None otherwise
        """
        try:
            # Common log file patterns
            log_patterns = ["*.log", "reconstruction*.txt", "scan*.txt"]

            files = os.listdir(directory_path)
            for file in files:
                file_lower = file.lower()
                if file_lower.endswith(".log"):
                    log_path = os.path.join(directory_path, file)
                    logger.info(f"Found log file: {file}")
                    return log_path

            logger.info("No log file found in directory")
            return None

        except (OSError, PermissionError) as e:
            logger.error(f"Error searching for log file: {e}")
            return None

    def count_files_in_directory(self, directory_path: str, extension: Optional[str] = None) -> int:
        """Count files in directory, optionally filtered by extension

        Args:
            directory_path (str): Directory to count files in
            extension (Optional[str]): File extension filter (e.g., '.tif')

        Returns:
            int: Number of files found
        """
        try:
            if not os.path.exists(directory_path):
                return 0

            files = os.listdir(directory_path)

            if extension:
                files = [f for f in files if f.lower().endswith(extension.lower())]

            return len(files)

        except (OSError, PermissionError) as e:
            logger.error(f"Error counting files: {e}")
            return 0
