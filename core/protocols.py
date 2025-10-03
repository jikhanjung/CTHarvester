"""
Protocol definitions for type safety across thumbnail generation system.

This module defines Protocol classes that specify interfaces for duck-typed
objects used in the thumbnail generation pipeline, improving type safety
without requiring inheritance.
"""

from typing import Any, Dict, List, Protocol, Union


class ThumbnailParent(Protocol):
    """Protocol for objects that can be parents of thumbnail generation.

    This protocol defines the interface that parent objects (typically MainWindow)
    must implement to coordinate with thumbnail generation components.

    Attributes:
        sampled_estimate_seconds: Estimated time in seconds for thumbnail generation
        sampled_estimate_str: Human-readable time estimate string
        estimated_time_per_image: Average time to process one image
        estimated_total_time: Total estimated processing time
        measured_images_per_second: Actual processing speed measurement
        current_drive: Path to current working drive
        total_levels: Number of LoD levels for thumbnails
        level_work_distribution: Work distribution across LoD levels
        weighted_total_work: Total work weighted by level complexity
    """

    # Time estimation attributes
    sampled_estimate_seconds: float
    sampled_estimate_str: str
    estimated_time_per_image: float
    estimated_total_time: float
    measured_images_per_second: float

    # Drive and level configuration
    current_drive: str
    total_levels: int
    level_work_distribution: List[Dict[str, Union[int, float]]]
    weighted_total_work: float


class ProgressDialog(Protocol):
    """Protocol for progress dialog interface.

    Defines the interface for progress tracking dialogs used during
    thumbnail generation.

    Attributes:
        is_cancelled: Flag indicating user cancellation
        lbl_text: Label for main status text
        lbl_status: Label for detailed status
        lbl_detail: Label for additional details
        pb_progress: Progress bar widget
    """

    is_cancelled: bool
    lbl_text: Any  # QLabel or compatible
    lbl_status: Any  # QLabel or compatible
    lbl_detail: Any  # QLabel or compatible
    pb_progress: Any  # QProgressBar or compatible
