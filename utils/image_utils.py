"""
Image Processing Utility Functions
"""

import logging
import os
from typing import Dict, Optional, Tuple, TypedDict

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
    except Exception as e:
        logger.error(f"Failed to detect bit depth for {image_path}: {e}")
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

    except Exception as e:
        logger.error(f"Failed to load image {image_path}: {e}")
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

    return avg.astype(img1.dtype)


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

    except Exception as e:
        logger.error(f"Failed to save image to {output_path}: {e}")
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
            return img.size
    except Exception as e:
        logger.error(f"Failed to get image dimensions: {e}")
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

    except Exception as e:
        logger.error(f"Failed to load image with metadata from {image_path}: {e}")
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
