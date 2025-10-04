"""
Image Processing Utility Functions
"""

import logging
import os
from typing import Dict, Optional, Tuple, TypedDict, Union

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImageMetadata(TypedDict):
    """Metadata extracted from image file"""

    width: int
    height: int
    bit_depth: int  # 8 or 16
    mode: str  # PIL mode string
    file_size: int


def detect_bit_depth(image_path: str) -> int:
    """
    Detect image bit depth

    Args:
        image_path: Path to image file

    Returns:
        Bit depth (8 or 16)

    Raises:
        ValueError: Unsupported image format
    """
    try:
        with Image.open(image_path) as img:
            if img.mode == "I;16":
                return 16
            elif img.mode in ("L", "RGB", "RGBA"):
                return 8
            else:
                logger.warning(f"Unsupported image mode: {img.mode}, assuming 8-bit")
                return 8
    except FileNotFoundError as e:
        logger.error(f"Image file not found: {image_path}", exc_info=True)
        raise FileNotFoundError(f"Image file not found: {image_path}") from e
    except PermissionError as e:
        logger.error(f"Permission denied reading image: {image_path}", exc_info=True)
        raise PermissionError(f"Permission denied: {image_path}") from e
    except OSError as e:
        logger.error(
            f"OS error detecting bit depth: {image_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "os_error", "file": image_path}},
        )
        raise OSError(f"Cannot read image file: {image_path}") from e
    except Exception as e:
        logger.exception(f"Unexpected error detecting bit depth: {image_path}")
        raise ValueError(f"Cannot detect bit depth: {e}") from e


def load_image_as_array(image_path: str, target_dtype: Optional[np.dtype] = None) -> np.ndarray:
    """
    Load image as numpy array (memory efficient)

    Args:
        image_path: Path to image file
        target_dtype: Target data type (None for auto-detection)

    Returns:
        numpy array
    """
    try:
        with Image.open(image_path) as img:
            # Auto-detect dtype
            if target_dtype is None:
                if img.mode == "I;16":
                    target_dtype = np.uint16  # type: ignore[assignment]
                else:
                    target_dtype = np.uint8  # type: ignore[assignment]

            arr = np.array(img, dtype=target_dtype)
            return arr

    except FileNotFoundError as e:
        logger.error(f"Image file not found: {image_path}", exc_info=True)
        raise
    except PermissionError as e:
        logger.error(f"Permission denied reading image: {image_path}", exc_info=True)
        raise
    except MemoryError as e:
        logger.error(
            f"Out of memory loading image: {image_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "out_of_memory", "file": image_path}},
        )
        raise
    except OSError as e:
        logger.error(
            f"OS error loading image: {image_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "os_error", "file": image_path}},
        )
        raise
    except Exception as e:
        logger.exception(f"Unexpected error loading image: {image_path}")
        raise


def downsample_image(
    img_array: np.ndarray, factor: int = 2, method: str = "subsample"
) -> np.ndarray:
    """
    Downsample image

    Args:
        img_array: Input image array
        factor: Downsampling factor (default 2)
        method: 'subsample' (fast) or 'average' (better quality)

    Returns:
        Downsampled array
    """
    if method == "subsample":
        # Simple subsampling (fastest)
        return img_array[::factor, ::factor]

    elif method == "average":
        # Block averaging (better quality)
        h, w = img_array.shape[:2]
        new_h, new_w = h // factor, w // factor

        # Reshape into factor x factor blocks
        if len(img_array.shape) == 2:
            # Grayscale
            reshaped = img_array[: new_h * factor, : new_w * factor].reshape(
                new_h, factor, new_w, factor
            )
            return reshaped.mean(axis=(1, 3)).astype(img_array.dtype)  # type: ignore[no-any-return]
        else:
            # Color
            reshaped = img_array[: new_h * factor, : new_w * factor].reshape(
                new_h, factor, new_w, factor, -1
            )
            return reshaped.mean(axis=(1, 3)).astype(img_array.dtype)  # type: ignore[no-any-return]

    else:
        raise ValueError(f"Unknown method: {method}")


def average_images(img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
    """
    Average two images (overflow safe)

    Args:
        img1: First image
        img2: Second image

    Returns:
        Averaged image
    """
    # Use larger dtype to prevent overflow
    if img1.dtype == np.uint8:
        temp_dtype = np.uint16  # type: ignore[assignment]
    elif img1.dtype == np.uint16:
        temp_dtype = np.uint32  # type: ignore[assignment]
    else:
        temp_dtype = np.float64  # type: ignore[assignment]

    # Calculate average
    avg = (img1.astype(temp_dtype) + img2.astype(temp_dtype)) // 2

    result: np.ndarray = avg.astype(img1.dtype)
    return result


def save_image_from_array(img_array: np.ndarray, output_path: str, compress: bool = True) -> bool:
    """
    Save numpy array as image file

    Args:
        img_array: Image array to save
        output_path: Output file path
        compress: Compression flag (TIFF)

    Returns:
        Success flag
    """
    try:
        # Convert dtype if needed for PIL compatibility
        if img_array.dtype == np.uint16:
            # PIL automatically detects 16-bit mode from uint16 arrays
            img = Image.fromarray(img_array)
        elif img_array.dtype == np.uint8:
            # PIL automatically detects L or RGB mode from shape
            img = Image.fromarray(img_array)
        else:
            logger.warning(f"Converting from {img_array.dtype} to uint8")
            img_array = img_array.astype(np.uint8)
            img = Image.fromarray(img_array)

        # TIFF compression settings
        if output_path.lower().endswith((".tif", ".tiff")):
            if compress:
                img.save(output_path, compression="tiff_deflate")
            else:
                img.save(output_path)
        else:
            img.save(output_path)

        return True

    except PermissionError as e:
        logger.error(f"Permission denied saving image: {output_path}", exc_info=True)
        return False
    except OSError as e:
        logger.error(
            f"OS error saving image: {output_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "os_error", "file": output_path}},
        )
        return False
    except MemoryError as e:
        logger.error(
            f"Out of memory saving image: {output_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "out_of_memory", "file": output_path}},
        )
        return False
    except Exception as e:
        logger.exception(f"Unexpected error saving image: {output_path}")
        return False


def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """
    Get image dimensions without full load

    Args:
        image_path: Path to image file

    Returns:
        (width, height)
    """
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            return (width, height)
    except FileNotFoundError as e:
        logger.error(f"Image file not found: {image_path}", exc_info=True)
        raise
    except PermissionError as e:
        logger.error(f"Permission denied reading image: {image_path}", exc_info=True)
        raise
    except OSError as e:
        logger.error(
            f"OS error reading image dimensions: {image_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "os_error", "file": image_path}},
        )
        raise
    except Exception as e:
        logger.exception(f"Unexpected error getting image dimensions: {image_path}")
        raise


def load_image_with_metadata(image_path: str) -> Tuple[np.ndarray, ImageMetadata]:
    """Load image and extract metadata in one operation

    This consolidated function combines image loading with metadata extraction
    to avoid redundant file operations when both are needed.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (image_array, metadata):
            - image_array: numpy array with appropriate dtype (uint8 or uint16)
            - metadata: Dictionary with width, height, bit_depth, mode, file_size

    Raises:
        FileNotFoundError: If image doesn't exist
        ValueError: If image format is unsupported

    Example:
        >>> arr, meta = load_image_with_metadata('slice_0001.tif')
        >>> print(f"{meta['width']}x{meta['height']}, {meta['bit_depth']}-bit")
        2048x2048, 16-bit
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        with Image.open(image_path) as img:
            width, height = img.size
            mode = img.mode
            bit_depth = 16 if mode in ("I;16", "I;16L", "I;16B") else 8

            # Convert to numpy array with appropriate dtype
            if bit_depth == 16:
                img_array = np.array(img, dtype=np.uint16)
            else:
                img_array = np.array(img, dtype=np.uint8)

            # Get file size
            file_size = os.path.getsize(image_path)

            metadata: ImageMetadata = {
                "width": width,
                "height": height,
                "bit_depth": bit_depth,
                "mode": mode,
                "file_size": file_size,
            }

            return img_array, metadata

    except FileNotFoundError as e:
        logger.error(f"Image file not found: {image_path}", exc_info=True)
        raise FileNotFoundError(f"Image file not found: {image_path}") from e
    except PermissionError as e:
        logger.error(f"Permission denied reading image: {image_path}", exc_info=True)
        raise PermissionError(f"Permission denied: {image_path}") from e
    except MemoryError as e:
        logger.error(
            f"Out of memory loading image with metadata: {image_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "out_of_memory", "file": image_path}},
        )
        raise
    except OSError as e:
        logger.error(
            f"OS error loading image with metadata: {image_path}",
            exc_info=True,
            extra={"extra_fields": {"error_type": "os_error", "file": image_path}},
        )
        raise
    except Exception as e:
        logger.exception(f"Unexpected error loading image with metadata: {image_path}")
        raise ValueError(f"Cannot load image: {e}") from e


def load_image_normalized(image_path: str, target_bit_depth: int = 8) -> np.ndarray:
    """Load image and normalize to target bit depth

    Handles conversion between 8-bit and 16-bit automatically, useful when
    you need consistent bit depth across a mixed dataset.

    Args:
        image_path: Path to image file
        target_bit_depth: Target bit depth (8 or 16)

    Returns:
        numpy array with target bit depth

    Raises:
        ValueError: If target_bit_depth is not 8 or 16

    Example:
        >>> # Force 8-bit output even if source is 16-bit
        >>> arr = load_image_normalized('16bit_image.tif', target_bit_depth=8)
        >>> arr.dtype
        dtype('uint8')
    """
    if target_bit_depth not in (8, 16):
        raise ValueError(f"target_bit_depth must be 8 or 16, got {target_bit_depth}")

    img_array, metadata = load_image_with_metadata(image_path)

    if metadata["bit_depth"] == target_bit_depth:
        return img_array
    elif metadata["bit_depth"] == 16 and target_bit_depth == 8:
        # Convert 16-bit to 8-bit by bit-shifting
        return (img_array >> 8).astype(np.uint8)
    elif metadata["bit_depth"] == 8 and target_bit_depth == 16:
        # Convert 8-bit to 16-bit by bit-shifting
        return img_array.astype(np.uint16) << 8
    else:
        raise ValueError(
            f"Unsupported bit depth conversion: {metadata['bit_depth']} -> {target_bit_depth}"
        )


class ImageLoadError(Exception):
    """Raised when image loading fails critically.

    Created during Phase 2 of quality improvement plan (devlog 072).
    """

    pass


def safe_load_image(
    file_path: str,
    convert_mode: Optional[str] = None,
    as_array: bool = True,
    handle_palette: bool = True,
) -> Optional[Union[np.ndarray, Image.Image]]:  # type: ignore[return]
    """Load image with standardized error handling.

    This function provides a centralized way to load images with consistent
    error handling across the codebase. It replaces the pattern of:
        try:
            with Image.open(path) as img:
                if img.mode == "P":
                    img = img.convert("L")
                arr = np.array(img)
        except FileNotFoundError:
            logger.warning(...)
        except OSError:
            logger.error(...)

    Args:
        file_path: Path to image file
        convert_mode: PIL mode to convert to (e.g., 'L', 'RGB').
                     If None, keeps original mode (after palette handling).
        as_array: If True, return as numpy array. If False, return PIL Image.
        handle_palette: If True, automatically convert palette mode ('P') to grayscale ('L')

    Returns:
        Loaded image as numpy array (if as_array=True) or PIL Image (if as_array=False).
        Returns None if file not found (logs warning).

    Raises:
        ImageLoadError: If loading fails critically (corrupted file, permission denied, etc.)

    Example:
        >>> # Basic usage - load as numpy array
        >>> arr = safe_load_image("image.png")
        >>> if arr is not None:
        ...     print(arr.shape)

        >>> # Load as RGB array
        >>> rgb = safe_load_image("image.png", convert_mode='RGB')

        >>> # Load as PIL Image
        >>> img = safe_load_image("image.png", as_array=False)

    Note:
        - FileNotFoundError returns None and logs warning (non-critical)
        - Other errors raise ImageLoadError (critical)
        - This is the recommended way to load images throughout the codebase

    Created during Phase 2 of quality improvement plan (devlog 072).
    """
    try:
        with Image.open(file_path) as img:
            # Handle palette mode
            if handle_palette and img.mode == "P":
                img = img.convert("L")
                logger.debug(f"Converted palette image to grayscale: {file_path}")

            # Apply conversion if requested
            if convert_mode and img.mode != convert_mode:
                img = img.convert(convert_mode)
                logger.debug(f"Converted image to {convert_mode}: {file_path}")

            # Return as requested format
            if as_array:
                return np.array(img)
            else:
                # Return a copy since we're in a context manager
                return img.copy()  # type: ignore[no-any-return]

    except FileNotFoundError:
        logger.warning(f"Image file not found: {file_path}")
        return None

    except PermissionError as e:
        logger.error(f"Permission denied accessing image: {file_path}", exc_info=True)
        raise ImageLoadError(f"Permission denied: {file_path}") from e

    except OSError as e:
        logger.error(
            f"OS error loading image: {file_path}",
            exc_info=True,
            extra={"error_type": type(e).__name__, "file_path": file_path},
        )
        raise ImageLoadError(f"Failed to load image: {file_path}") from e

    except Exception as e:
        logger.error(
            f"Unexpected error loading image: {file_path}",
            exc_info=True,
            extra={"error_type": type(e).__name__, "file_path": file_path},
        )
        raise ImageLoadError(f"Unexpected error loading {file_path}") from e
