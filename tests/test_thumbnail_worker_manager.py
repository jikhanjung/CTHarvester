"""Tests for core/thumbnail_worker_manager.py - Worker management.

Part of Phase 3 architectural refactoring (devlog 072)
"""

import tempfile
import time
from unittest.mock import Mock, patch

import pytest
from PyQt5.QtCore import QThreadPool

from core.thumbnail_progress_tracker import ThumbnailProgressTracker
from core.thumbnail_worker import ThumbnailWorker
from core.thumbnail_worker_manager import ThumbnailWorkerManager


class TestThumbnailWorkerManager:
    """Test suite for ThumbnailWorkerManager class"""

    @pytest.fixture
    def progress_tracker(self):
        """Create a progress tracker"""
        return ThumbnailProgressTracker(sample_size=5, level_weight=1.0)

    @pytest.fixture
    def progress_dialog(self):
        """Create a mock progress dialog"""
        dialog = Mock()
        dialog.is_cancelled = False
        dialog.lbl_text = Mock()
        dialog.lbl_text.setText = Mock()
        return dialog

    @pytest.fixture
    def threadpool(self):
        """Create a QThreadPool"""
        return QThreadPool()

    @pytest.fixture
    def worker_manager(self, threadpool, progress_tracker, progress_dialog):
        """Create a worker manager"""
        return ThumbnailWorkerManager(
            threadpool=threadpool,
            progress_tracker=progress_tracker,
            progress_dialog=progress_dialog,
            level_weight=1.0,
        )

    def test_initialization_basic(self, threadpool, progress_tracker, progress_dialog):
        """Test basic initialization"""
        manager = ThumbnailWorkerManager(
            threadpool=threadpool,
            progress_tracker=progress_tracker,
            progress_dialog=progress_dialog,
            level_weight=1.0,
        )

        assert manager.threadpool == threadpool
        assert manager.progress_tracker == progress_tracker
        assert manager.progress_dialog == progress_dialog
        assert manager.level_weight == 1.0
        assert manager.is_cancelled is False
        assert manager.global_step_counter == 0.0
        assert manager.workers_submitted == 0
        assert len(manager.results) == 0

    def test_initialization_custom_weight(self, threadpool, progress_tracker, progress_dialog):
        """Test initialization with custom level weight"""
        manager = ThumbnailWorkerManager(
            threadpool=threadpool,
            progress_tracker=progress_tracker,
            progress_dialog=progress_dialog,
            level_weight=0.25,
        )

        assert manager.level_weight == 0.25

    def test_initialization_no_dialog(self, threadpool, progress_tracker):
        """Test initialization without progress dialog"""
        manager = ThumbnailWorkerManager(
            threadpool=threadpool,
            progress_tracker=progress_tracker,
            progress_dialog=None,
            level_weight=1.0,
        )

        assert manager.progress_dialog is None

    def test_submit_worker(self, worker_manager):
        """Test submitting a worker to thread pool"""
        # Create a mock worker
        worker = Mock(spec=ThumbnailWorker)
        worker.signals = Mock()
        worker.signals.progress = Mock()
        worker.signals.result = Mock()
        worker.signals.error = Mock()
        worker.signals.finished = Mock()
        worker.signals.progress.connect = Mock()
        worker.signals.result.connect = Mock()
        worker.signals.error.connect = Mock()
        worker.signals.finished.connect = Mock()

        # Submit worker
        initial_count = worker_manager.workers_submitted
        worker_manager.submit_worker(worker)

        # Verify connections were made
        worker.signals.progress.connect.assert_called_once()
        worker.signals.result.connect.assert_called_once()
        worker.signals.error.connect.assert_called_once()
        worker.signals.finished.connect.assert_called_once()

        # Verify worker count incremented
        assert worker_manager.workers_submitted == initial_count + 1

    def test_set_global_step_offset(self, worker_manager):
        """Test setting global step offset"""
        worker_manager.set_global_step_offset(100.0)
        assert worker_manager.global_step_counter == 100.0

    def test_clear_results(self, worker_manager):
        """Test clearing results"""
        # Add some results
        worker_manager.results[0] = "result0"
        worker_manager.results[1] = "result1"

        # Clear
        worker_manager.clear_results()

        assert len(worker_manager.results) == 0

    def test_on_worker_progress_updates_counter(self, worker_manager):
        """Test on_worker_progress updates global counter"""
        initial_counter = worker_manager.global_step_counter

        worker_manager.on_worker_progress(0)

        assert worker_manager.global_step_counter == initial_counter + worker_manager.level_weight

    def test_on_worker_progress_updates_ui(self, worker_manager):
        """Test on_worker_progress updates UI text"""
        worker_manager.on_worker_progress(0)

        worker_manager.progress_dialog.lbl_text.setText.assert_called_with("Generating thumbnails")

    def test_on_worker_progress_multiple_calls(self, worker_manager):
        """Test multiple worker progress calls"""
        for i in range(5):
            worker_manager.on_worker_progress(i)

        expected_counter = 5 * worker_manager.level_weight
        assert worker_manager.global_step_counter == expected_counter

    def test_on_worker_result_basic(self, worker_manager):
        """Test on_worker_result with basic result"""
        result = (0, "image_array", True)  # idx, img_array, was_generated

        worker_manager.on_worker_result(result)

        assert 0 in worker_manager.results
        assert worker_manager.results[0] == "image_array"

    def test_on_worker_result_legacy_format(self, worker_manager):
        """Test on_worker_result with legacy 2-tuple format"""
        result = (0, "image_array")  # No was_generated flag

        worker_manager.on_worker_result(result)

        assert 0 in worker_manager.results
        assert worker_manager.results[0] == "image_array"

    def test_on_worker_result_duplicate(self, worker_manager):
        """Test on_worker_result ignores duplicates"""
        result1 = (0, "image_array1", True)
        result2 = (0, "image_array2", True)  # Same idx

        worker_manager.on_worker_result(result1)
        worker_manager.on_worker_result(result2)

        # Should keep first result
        assert worker_manager.results[0] == "image_array1"

    def test_on_worker_result_none_image(self, worker_manager):
        """Test on_worker_result with None image array"""
        result = (0, None, False)

        worker_manager.on_worker_result(result)

        assert 0 in worker_manager.results
        assert worker_manager.results[0] is None

    def test_on_worker_error_logs_error(self, worker_manager):
        """Test on_worker_error logs error information"""
        error_tuple = (ValueError, ValueError("test error"), "traceback here")

        # Should not raise exception
        worker_manager.on_worker_error(error_tuple)

    def test_on_worker_finished(self, worker_manager):
        """Test on_worker_finished is a no-op"""
        # Should not raise exception
        worker_manager.on_worker_finished()

    def test_get_ordered_results_basic(self, worker_manager):
        """Test get_ordered_results returns results in order"""
        worker_manager.results[0] = "result0"
        worker_manager.results[1] = "result1"
        worker_manager.results[2] = "result2"

        results = worker_manager.get_ordered_results(total_tasks=3)

        assert results == ["result0", "result1", "result2"]

    def test_get_ordered_results_sparse(self, worker_manager):
        """Test get_ordered_results with sparse results"""
        worker_manager.results[0] = "result0"
        # Skip 1
        worker_manager.results[2] = "result2"

        results = worker_manager.get_ordered_results(total_tasks=3)

        # Should only include existing results
        assert results == ["result0", "result2"]

    def test_get_ordered_results_with_none(self, worker_manager):
        """Test get_ordered_results skips None values"""
        worker_manager.results[0] = "result0"
        worker_manager.results[1] = None
        worker_manager.results[2] = "result2"

        results = worker_manager.get_ordered_results(total_tasks=3)

        # Should skip None
        assert results == ["result0", "result2"]

    def test_check_cancellation_false(self, worker_manager):
        """Test _check_cancellation returns False when not cancelled"""
        worker_manager.progress_dialog.is_cancelled = False

        assert worker_manager._check_cancellation() is False

    def test_check_cancellation_true(self, worker_manager):
        """Test _check_cancellation returns True when cancelled"""
        worker_manager.progress_dialog.is_cancelled = True

        assert worker_manager._check_cancellation() is True

    def test_check_cancellation_no_dialog(self, threadpool, progress_tracker):
        """Test _check_cancellation returns False when no dialog"""
        manager = ThumbnailWorkerManager(
            threadpool=threadpool, progress_tracker=progress_tracker, progress_dialog=None
        )

        assert manager._check_cancellation() is False

    def test_wait_for_completion_completes_normally(self, worker_manager):
        """Test wait_for_completion returns False when tasks complete"""
        # Simulate all tasks completed
        worker_manager.progress_tracker.completed_tasks = 10

        cancelled = worker_manager.wait_for_completion(total_tasks=10)

        assert cancelled is False
        assert worker_manager.is_cancelled is False

    def test_wait_for_completion_cancelled(self, worker_manager):
        """Test wait_for_completion returns True when cancelled"""
        # Set up cancellation
        worker_manager.progress_dialog.is_cancelled = True
        worker_manager.progress_tracker.completed_tasks = 5

        cancelled = worker_manager.wait_for_completion(total_tasks=10)

        assert cancelled is True
        assert worker_manager.is_cancelled is True

    @pytest.mark.parametrize(
        "level_weight,expected_increment",
        [
            (1.0, 1.0),
            (0.25, 0.25),
            (0.0625, 0.0625),
        ],
    )
    def test_progress_increment_by_weight(
        self, threadpool, progress_tracker, progress_dialog, level_weight, expected_increment
    ):
        """Parametrized test for progress increment by weight"""
        manager = ThumbnailWorkerManager(
            threadpool=threadpool,
            progress_tracker=progress_tracker,
            progress_dialog=progress_dialog,
            level_weight=level_weight,
        )

        initial = manager.global_step_counter
        manager.on_worker_progress(0)

        assert manager.global_step_counter == initial + expected_increment

    def test_thread_safety_multiple_results(self, worker_manager):
        """Test thread-safe handling of multiple concurrent results"""
        # Simulate multiple workers completing simultaneously
        results = [
            (0, "result0", True),
            (1, "result1", True),
            (2, "result2", False),
        ]

        for result in results:
            worker_manager.on_worker_result(result)

        assert len(worker_manager.results) == 3
        assert worker_manager.results[0] == "result0"
        assert worker_manager.results[1] == "result1"
        assert worker_manager.results[2] == "result2"

    def test_results_preserved_across_operations(self, worker_manager):
        """Test that results are preserved across multiple operations"""
        # Add result
        worker_manager.on_worker_result((0, "result0", True))

        # Update progress
        worker_manager.on_worker_progress(1)

        # Add another result
        worker_manager.on_worker_result((1, "result1", True))

        # Verify both results still exist
        assert len(worker_manager.results) == 2
        assert worker_manager.results[0] == "result0"
        assert worker_manager.results[1] == "result1"
