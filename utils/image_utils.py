"""
Image Processing Utility Functions
"""
from PIL import Image
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


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
            if img.mode == 'I;16':
                return 16
            elif img.mode in ('L', 'RGB', 'RGBA'):
                return 8
            else:
                logger.warning(f"Unsupported image mode: {img.mode}, assuming 8-bit")
                return 8
    except Exception as e:
        logger.error(f"Failed to detect bit depth for {image_path}: {e}")
        raise ValueError(f"Cannot detect bit depth: {e}") from e


def load_image_as_array(
    image_path: str,
    target_dtype: Optional[np.dtype] = None
) -> np.ndarray:
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
                if img.mode == 'I;16':
                    target_dtype = np.uint16
                else:
                    target_dtype = np.uint8

            arr = np.array(img, dtype=target_dtype)
            return arr

    except Exception as e:
        logger.error(f"Failed to load image {image_path}: {e}")
        raise


def downsample_image(
    img_array: np.ndarray,
    factor: int = 2,
    method: str = 'subsample'
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
    if method == 'subsample':
        # Simple subsampling (fastest)
        return img_array[::factor, ::factor]

    elif method == 'average':
        # Block averaging (better quality)
        h, w = img_array.shape[:2]
        new_h, new_w = h // factor, w // factor

        # Reshape into factor x factor blocks
        if len(img_array.shape) == 2:
            # Grayscale
            reshaped = img_array[:new_h*factor, :new_w*factor].reshape(
                new_h, factor, new_w, factor
            )
            return reshaped.mean(axis=(1, 3)).astype(img_array.dtype)
        else:
            # Color
            reshaped = img_array[:new_h*factor, :new_w*factor].reshape(
                new_h, factor, new_w, factor, -1
            )
            return reshaped.mean(axis=(1, 3)).astype(img_array.dtype)

    else:
        raise ValueError(f"Unknown method: {method}")


def average_images(
    img1: np.ndarray,
    img2: np.ndarray
) -> np.ndarray:
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
        temp_dtype = np.uint16
    elif img1.dtype == np.uint16:
        temp_dtype = np.uint32
    else:
        temp_dtype = np.float64

    # Calculate average
    avg = (img1.astype(temp_dtype) + img2.astype(temp_dtype)) // 2

    return avg.astype(img1.dtype)


def save_image_from_array(
    img_array: np.ndarray,
    output_path: str,
    compress: bool = True
) -> bool:
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
        # Determine PIL mode from dtype
        if img_array.dtype == np.uint16:
            mode = 'I;16'
        elif img_array.dtype == np.uint8:
            mode = 'L' if len(img_array.shape) == 2 else 'RGB'
        else:
            logger.warning(f"Converting from {img_array.dtype} to uint8")
            img_array = img_array.astype(np.uint8)
            mode = 'L'

        img = Image.fromarray(img_array, mode=mode)

        # TIFF compression settings
        if output_path.lower().endswith(('.tif', '.tiff')):
            if compress:
                img.save(output_path, compression='tiff_deflate')
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