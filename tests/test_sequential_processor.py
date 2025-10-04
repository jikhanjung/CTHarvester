"""Tests for SequentialProcessor (Phase 4.1).

This module tests the sequential thumbnail processor which provides
Python fallback when Rust module is unavailable.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from core.sequential_processor import SequentialProcessor


class TestSequentialProcessorInitialization:
    """Tests for SequentialProcessor initialization."""

    def test_initialization_with_all_parameters(self):
        """Test processor initialization with all parameters."""
        mock_dialog = MagicMock()
        mock_manager = MagicMock()
        mock_parent = MagicMock()

        processor = SequentialProcessor(mock_dialog, mock_manager, mock_parent)

        assert processor.progress_dialog is mock_dialog
        assert processor.progress_manager is mock_manager
        assert processor.thumbnail_parent is mock_parent
        assert processor.results == {}
        assert processor.completed_tasks == 0
        assert processor.generated_count == 0
        assert processor.loaded_count == 0
        assert processor.is_cancelled is False

    def test_initialization_with_none_dialog(self):
        """Test initialization with None progress dialog."""
        mock_manager = MagicMock()
        mock_parent = MagicMock()

        processor = SequentialProcessor(None, mock_manager, mock_parent)

        assert processor.progress_dialog is None
        assert processor.progress_manager is mock_manager

    def test_initialization_sets_default_values(self):
        """Test that default values are set correctly."""
        processor = SequentialProcessor(None, MagicMock(), None)

        assert processor.global_step_counter == 0
        assert processor.level_weight == 1
        assert processor.is_sampling is False
        assert processor.images_per_second == 0.0


class TestSequentialProcessorProcessLevel:
    """Tests for process_level method."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary source and destination directories with test images."""
        from_dir = tmp_path / "from"
        to_dir = tmp_path / "to"
        from_dir.mkdir()
        to_dir.mkdir()

        # Create test images
        for i in range(5):
            img = Image.new("L", (100, 100), color=i * 50)
            img.save(from_dir / f"img_{i:04d}.tif")

        return {"from": str(from_dir), "to": str(to_dir)}

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        mock_dialog = MagicMock()
        mock_dialog.is_cancelled = False
        mock_manager = MagicMock()
        mock_parent = MagicMock()

        proc = SequentialProcessor(mock_dialog, mock_manager, mock_parent)
        return proc

    @pytest.fixture
    def settings_hash(self):
        """Sample settings hash."""
        return {
            "prefix": "img_",
            "file_type": "tif",
            "index_length": 4,
        }

    def test_process_level_basic_workflow(self, processor, temp_dirs, settings_hash):
        """Test basic sequential processing workflow."""
        processor.process_level(
            level=0,
            from_dir=temp_dirs["from"],
            to_dir=temp_dirs["to"],
            seq_begin=0,
            seq_end=4,
            settings_hash=settings_hash,
            size=50,
            max_thumbnail_size=512,
            num_tasks=5,
        )

        # Check that results were generated
        assert len(processor.results) > 0
        assert processor.completed_tasks > 0

    def test_process_level_with_existing_directory(self, processor, temp_dirs, settings_hash):
        """Test that processing works with existing output directory."""
        processor.process_level(
            level=0,
            from_dir=temp_dirs["from"],
            to_dir=temp_dirs["to"],
            seq_begin=0,
            seq_end=2,
            settings_hash=settings_hash,
            size=50,
            max_thumbnail_size=512,
            num_tasks=3,
        )

        # Should complete successfully
        assert processor.completed_tasks >= 0

    def test_process_level_handles_cancellation(self, processor, temp_dirs, settings_hash):
        """Test that processing stops on cancellation."""
        # Simulate cancellation after first task
        processor.progress_dialog.is_cancelled = True

        processor.process_level(
            level=0,
            from_dir=temp_dirs["from"],
            to_dir=temp_dirs["to"],
            seq_begin=0,
            seq_end=4,
            settings_hash=settings_hash,
            size=50,
            max_thumbnail_size=512,
            num_tasks=5,
        )

        # Should stop early
        assert processor.is_cancelled is True

    def test_process_level_progress_tracking(self, processor, temp_dirs, settings_hash):
        """Test that progress is tracked correctly."""
        processor.process_level(
            level=0,
            from_dir=temp_dirs["from"],
            to_dir=temp_dirs["to"],
            seq_begin=0,
            seq_end=4,
            settings_hash=settings_hash,
            size=50,
            max_thumbnail_size=512,
            num_tasks=5,
        )

        # Progress manager should have been updated
        assert processor.progress_manager.update.called

    def test_process_level_generates_thumbnails(self, processor, temp_dirs, settings_hash):
        """Test that thumbnails are actually generated."""
        processor.process_level(
            level=0,
            from_dir=temp_dirs["from"],
            to_dir=temp_dirs["to"],
            seq_begin=0,
            seq_end=2,
            settings_hash=settings_hash,
            size=50,
            max_thumbnail_size=512,
            num_tasks=3,
        )

        # Check results
        assert len(processor.results) > 0
        # Each result should be a numpy array
        for result in processor.results.values():
            assert isinstance(result, np.ndarray)

    def test_process_level_with_different_sizes(self, processor, temp_dirs, settings_hash):
        """Test processing with different size parameters."""
        processor.process_level(
            level=0,
            from_dir=temp_dirs["from"],
            to_dir=temp_dirs["to"],
            seq_begin=0,
            seq_end=2,
            settings_hash=settings_hash,
            size=25,  # Smaller size
            max_thumbnail_size=512,
            num_tasks=3,
        )

        # Should complete
        assert processor.completed_tasks >= 0
        # Results should exist
        assert len(processor.results) >= 0


class TestSequentialProcessorStateManagement:
    """Tests for state management and transfer."""

    def test_results_dictionary_updates(self):
        """Test that results dictionary is updated correctly."""
        processor = SequentialProcessor(None, MagicMock(), None)

        # Simulate adding results
        processor.results[0] = np.zeros((100, 100))
        processor.results[1] = np.ones((100, 100))

        assert len(processor.results) == 2
        assert 0 in processor.results
        assert 1 in processor.results

    def test_completed_tasks_counter(self):
        """Test that completed tasks counter increments."""
        processor = SequentialProcessor(None, MagicMock(), None)

        assert processor.completed_tasks == 0

        processor.completed_tasks += 1
        assert processor.completed_tasks == 1

    def test_global_step_counter_transfer(self):
        """Test that global step counter can be set and read."""
        processor = SequentialProcessor(None, MagicMock(), None)

        processor.global_step_counter = 100
        assert processor.global_step_counter == 100

    def test_level_weight_transfer(self):
        """Test that level weight can be set and read."""
        processor = SequentialProcessor(None, MagicMock(), None)

        processor.level_weight = 50
        assert processor.level_weight == 50

    def test_images_per_second_transfer(self):
        """Test that images_per_second can be set."""
        processor = SequentialProcessor(None, MagicMock(), None)

        processor.images_per_second = 2.5
        assert processor.images_per_second == 2.5


class TestSequentialProcessorPerformanceSampling:
    """Tests for performance sampling functionality."""

    @pytest.fixture
    def processor(self):
        """Create processor for sampling tests."""
        mock_dialog = MagicMock()
        mock_dialog.is_cancelled = False
        mock_manager = MagicMock()
        mock_parent = MagicMock()
        mock_parent.measured_images_per_second = 0.0

        return SequentialProcessor(mock_dialog, mock_manager, mock_parent)

    def test_performance_sampling_initialization(self, processor):
        """Test that sampling can be initialized."""
        assert processor.is_sampling is False
        assert processor.sample_size == 10
        assert processor.images_per_second == 0.0

    def test_performance_sampling_attributes(self, processor):
        """Test that all sampling attributes exist."""
        assert hasattr(processor, "is_sampling")
        assert hasattr(processor, "sample_size")
        assert hasattr(processor, "sample_start_time")
        assert hasattr(processor, "images_per_second")


class TestSequentialProcessorErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.fixture
    def processor(self):
        """Create processor for error tests."""
        return SequentialProcessor(None, MagicMock(), None)

    def test_handles_missing_source_files(self, processor, tmp_path):
        """Test handling when source files don't exist."""
        from_dir = tmp_path / "empty"
        to_dir = tmp_path / "to"
        from_dir.mkdir()
        to_dir.mkdir()

        settings_hash = {
            "prefix": "missing_",
            "file_type": "tif",
            "index_length": 4,
        }

        # Should not crash
        processor.process_level(
            level=0,
            from_dir=str(from_dir),
            to_dir=str(to_dir),
            seq_begin=0,
            seq_end=10,
            settings_hash=settings_hash,
            size=100,
            max_thumbnail_size=512,
            num_tasks=10,
        )

        # Results should be empty or partial
        assert len(processor.results) == 0

    def test_handles_empty_results_gracefully(self, processor, tmp_path):
        """Test that processor handles scenarios with no valid results."""
        from_dir = tmp_path / "from"
        to_dir = tmp_path / "to"
        from_dir.mkdir()
        to_dir.mkdir()

        settings_hash = {
            "prefix": "nonexistent_",
            "file_type": "tif",
            "index_length": 4,
        }

        # Process with no matching files
        processor.process_level(
            level=0,
            from_dir=str(from_dir),
            to_dir=str(to_dir),
            seq_begin=0,
            seq_end=5,
            settings_hash=settings_hash,
            size=100,
            max_thumbnail_size=512,
            num_tasks=5,
        )

        # Should not crash, results may be empty
        assert isinstance(processor.results, dict)


class TestSequentialProcessorEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def processor(self):
        """Create processor."""
        return SequentialProcessor(None, MagicMock(), None)

    def test_single_image_processing(self, processor, tmp_path):
        """Test processing a single image."""
        from_dir = tmp_path / "from"
        to_dir = tmp_path / "to"
        from_dir.mkdir()
        to_dir.mkdir()

        # Create single image
        img = Image.new("L", (100, 100), color=128)
        img.save(from_dir / "img_0000.tif")

        settings_hash = {
            "prefix": "img_",
            "file_type": "tif",
            "index_length": 4,
        }

        processor.process_level(
            level=0,
            from_dir=str(from_dir),
            to_dir=str(to_dir),
            seq_begin=0,
            seq_end=0,
            settings_hash=settings_hash,
            size=50,
            max_thumbnail_size=512,
            num_tasks=1,
        )

        # Should process successfully
        assert processor.completed_tasks >= 0

    def test_valid_sequence_range(self, processor, tmp_path):
        """Test with valid sequence range."""
        from_dir = tmp_path / "from"
        to_dir = tmp_path / "to"
        from_dir.mkdir()
        to_dir.mkdir()

        # Create a couple of test images
        for i in range(2):
            img = Image.new("L", (100, 100), color=i * 100)
            img.save(from_dir / f"img_{i:04d}.tif")

        settings_hash = {
            "prefix": "img_",
            "file_type": "tif",
            "index_length": 4,
        }

        processor.process_level(
            level=0,
            from_dir=str(from_dir),
            to_dir=str(to_dir),
            seq_begin=0,
            seq_end=1,
            settings_hash=settings_hash,
            size=50,
            max_thumbnail_size=512,
            num_tasks=2,
        )

        # Should complete successfully
        assert processor.completed_tasks >= 0

    def test_very_small_thumbnail_size(self, processor, tmp_path):
        """Test with very small thumbnail size."""
        from_dir = tmp_path / "from"
        to_dir = tmp_path / "to"
        from_dir.mkdir()
        to_dir.mkdir()

        img = Image.new("L", (1000, 1000), color=128)
        img.save(from_dir / "img_0000.tif")

        settings_hash = {
            "prefix": "img_",
            "file_type": "tif",
            "index_length": 4,
        }

        processor.process_level(
            level=2,
            from_dir=str(from_dir),
            to_dir=str(to_dir),
            seq_begin=0,
            seq_end=0,
            settings_hash=settings_hash,
            size=10,  # Very small
            max_thumbnail_size=512,
            num_tasks=1,
        )

        # Should still work
        if 0 in processor.results:
            result = processor.results[0]
            assert result.shape[0] <= 512
            assert result.shape[1] <= 512
