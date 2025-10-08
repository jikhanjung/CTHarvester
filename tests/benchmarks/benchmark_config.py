"""
Benchmark configuration and test scenarios

Defines standard benchmark scenarios for performance testing.
Created during Phase 3 (Performance & Robustness).
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class BenchmarkScenario:
    """Benchmark test scenario definition"""

    name: str
    description: str
    image_count: int
    image_size: Tuple[int, int]  # (width, height)
    bit_depth: int  # 8 or 16
    expected_memory_mb: float  # Expected peak memory usage
    expected_time_seconds: float  # Expected processing time


class BenchmarkScenarios:
    """Standard benchmark scenarios for CTHarvester"""

    # Small dataset - Quick smoke test
    SMALL = BenchmarkScenario(
        name="Small",
        description="Small dataset for quick smoke testing",
        image_count=10,
        image_size=(512, 512),
        bit_depth=8,
        expected_memory_mb=50.0,
        expected_time_seconds=5.0,
    )

    # Medium dataset - Typical usage
    MEDIUM = BenchmarkScenario(
        name="Medium",
        description="Medium dataset representing typical usage",
        image_count=100,
        image_size=(1024, 1024),
        bit_depth=8,
        expected_memory_mb=200.0,
        expected_time_seconds=30.0,
    )

    # Large dataset - Stress test
    LARGE = BenchmarkScenario(
        name="Large",
        description="Large dataset for stress testing",
        image_count=500,
        image_size=(2048, 2048),
        bit_depth=16,
        expected_memory_mb=2000.0,
        expected_time_seconds=180.0,
    )

    # Extra large dataset - Maximum capacity test
    XLARGE = BenchmarkScenario(
        name="XLarge",
        description="Extra large dataset for maximum capacity testing",
        image_count=1000,
        image_size=(2048, 2048),
        bit_depth=16,
        expected_memory_mb=4000.0,
        expected_time_seconds=600.0,
    )

    @classmethod
    def get_all_scenarios(cls):
        """Get all benchmark scenarios"""
        return [cls.SMALL, cls.MEDIUM, cls.LARGE, cls.XLARGE]

    @classmethod
    def get_quick_scenarios(cls):
        """Get quick benchmark scenarios (for CI/CD)"""
        return [cls.SMALL, cls.MEDIUM]


class PerformanceThresholds:
    """Performance threshold definitions"""

    # Memory usage thresholds (MB per image)
    MEMORY_PER_IMAGE_8BIT = 2.0  # 2 MB per 1024x1024 8-bit image
    MEMORY_PER_IMAGE_16BIT = 4.0  # 4 MB per 1024x1024 16-bit image

    # Processing time thresholds (seconds per image)
    TIME_PER_IMAGE_THUMBNAIL = 0.1  # 100ms per image for thumbnails
    TIME_PER_IMAGE_FULL = 0.5  # 500ms per image for full processing

    # Thumbnail generation thresholds
    THUMBNAIL_TIME_RUST = 0.05  # 50ms per image with Rust
    THUMBNAIL_TIME_PYTHON = 0.2  # 200ms per image with Python

    @classmethod
    def get_expected_memory(cls, scenario: BenchmarkScenario) -> float:
        """
        Calculate expected memory usage for scenario

        Args:
            scenario: Benchmark scenario

        Returns:
            Expected memory in MB
        """
        width, height = scenario.image_size
        pixels = width * height
        bytes_per_pixel = scenario.bit_depth // 8

        # Memory per image
        image_size_mb = (pixels * bytes_per_pixel) / (1024 * 1024)

        # Conservative estimate: 3x image size for processing overhead
        return image_size_mb * scenario.image_count * 3

    @classmethod
    def get_expected_time(cls, scenario: BenchmarkScenario, operation: str = "thumbnail") -> float:
        """
        Calculate expected processing time for scenario

        Args:
            scenario: Benchmark scenario
            operation: Operation type ('thumbnail', 'full')

        Returns:
            Expected time in seconds
        """
        if operation == "thumbnail":
            return scenario.image_count * cls.TIME_PER_IMAGE_THUMBNAIL
        elif operation == "full":
            return scenario.image_count * cls.TIME_PER_IMAGE_FULL
        else:
            return scenario.expected_time_seconds
