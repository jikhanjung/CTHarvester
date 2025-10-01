"""
Unit tests for MCubeWidget (limited - OpenGL testing)

Tests basic functionality of 3D mesh visualization widget.
Note: OpenGL rendering tests are limited as they require display context.
"""

import os
import sys

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QWidget

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

if PYQT_AVAILABLE:
    try:
        from ui.widgets.mcube_widget import MeshGenerationThread

        OPENGL_AVAILABLE = True
    except ImportError:
        OPENGL_AVAILABLE = False
else:
    OPENGL_AVAILABLE = False


@pytest.mark.skipif(not PYQT_AVAILABLE or not OPENGL_AVAILABLE, reason="PyQt5 or OpenGL not available")
@pytest.mark.qt
class TestMeshGenerationThread:
    """Tests for MeshGenerationThread (non-OpenGL parts)"""

    def test_initialization(self):
        """Should initialize with correct parameters"""
        volume = np.ones((10, 10, 10), dtype=np.uint8) * 128
        isovalue = 100
        scale_factor = 0.5
        is_inverse = False

        thread = MeshGenerationThread(volume, isovalue, scale_factor, is_inverse)

        assert thread.volume is not None
        assert thread.isovalue == 100
        assert thread.scale_factor == 0.5
        assert thread.is_inverse is False

    def test_thread_signals_exist(self):
        """Should have required signals"""
        volume = np.ones((10, 10, 10), dtype=np.uint8)
        thread = MeshGenerationThread(volume, 50, 1.0, False)

        # Verify signals exist
        assert hasattr(thread, 'finished')
        assert hasattr(thread, 'error')
        assert hasattr(thread, 'progress')

    def test_inverse_mode(self):
        """Should accept inverse mode flag"""
        volume = np.ones((10, 10, 10), dtype=np.uint8)

        thread_normal = MeshGenerationThread(volume, 50, 1.0, False)
        assert thread_normal.is_inverse is False

        thread_inverse = MeshGenerationThread(volume, 50, 1.0, True)
        assert thread_inverse.is_inverse is True

    def test_scale_factor_values(self):
        """Should accept different scale factors"""
        volume = np.ones((10, 10, 10), dtype=np.uint8)

        scales = [0.25, 0.5, 1.0, 2.0]
        for scale in scales:
            thread = MeshGenerationThread(volume, 50, scale, False)
            assert thread.scale_factor == scale

    def test_isovalue_range(self):
        """Should accept different isovalue ranges"""
        volume = np.ones((10, 10, 10), dtype=np.uint8)

        isovalues = [0, 50, 128, 200, 255]
        for iso in isovalues:
            thread = MeshGenerationThread(volume, iso, 1.0, False)
            assert thread.isovalue == iso


@pytest.mark.skipif(not PYQT_AVAILABLE or not OPENGL_AVAILABLE, reason="PyQt5 or OpenGL not available")
@pytest.mark.qt
@pytest.mark.slow
class TestMeshGeneration:
    """Tests for actual mesh generation (slow tests)"""

    def test_mesh_generation_small_volume(self, qtbot):
        """Should generate mesh from small volume"""
        # Create simple test volume (sphere-like)
        volume = np.zeros((20, 20, 20), dtype=np.uint8)
        center = 10
        for x in range(20):
            for y in range(20):
                for z in range(20):
                    dist = np.sqrt((x-center)**2 + (y-center)**2 + (z-center)**2)
                    if dist < 5:
                        volume[x, y, z] = 200

        thread = MeshGenerationThread(volume, 100, 1.0, False)

        # Connect to finished signal
        with qtbot.waitSignal(thread.finished, timeout=10000) as blocker:
            thread.start()

        # Should complete
        assert blocker.signal_triggered

    def test_mesh_generation_progress_signal(self, qtbot):
        """Should emit progress signals during generation"""
        volume = np.ones((15, 15, 15), dtype=np.uint8) * 150
        thread = MeshGenerationThread(volume, 100, 1.0, False)

        progress_values = []

        def on_progress(value):
            progress_values.append(value)

        thread.progress.connect(on_progress)

        with qtbot.waitSignal(thread.finished, timeout=10000):
            thread.start()

        # Should have emitted multiple progress values
        assert len(progress_values) > 0

    def test_mesh_generation_with_inverse(self, qtbot):
        """Should generate mesh with inverse mode"""
        volume = np.ones((15, 15, 15), dtype=np.uint8) * 100
        thread = MeshGenerationThread(volume, 50, 1.0, True)

        with qtbot.waitSignal(thread.finished, timeout=10000) as blocker:
            thread.start()

        assert blocker.signal_triggered


@pytest.mark.skipif(not PYQT_AVAILABLE or not OPENGL_AVAILABLE, reason="PyQt5 or OpenGL not available")
@pytest.mark.qt
class TestMeshGenerationEdgeCases:
    """Edge case tests for mesh generation"""

    def test_empty_volume(self):
        """Should handle empty volume"""
        volume = np.zeros((10, 10, 10), dtype=np.uint8)
        thread = MeshGenerationThread(volume, 50, 1.0, False)

        # Should initialize without error
        assert thread.volume.shape == (10, 10, 10)

    def test_uniform_volume(self):
        """Should handle uniform volume (no mesh)"""
        volume = np.ones((10, 10, 10), dtype=np.uint8) * 128
        thread = MeshGenerationThread(volume, 50, 1.0, False)

        # Should initialize without error
        assert thread.isovalue == 50

    def test_very_small_volume(self):
        """Should handle very small volume"""
        volume = np.ones((2, 2, 2), dtype=np.uint8)
        thread = MeshGenerationThread(volume, 50, 1.0, False)

        assert thread.volume.shape == (2, 2, 2)

    def test_extreme_isovalue(self):
        """Should handle extreme isovalue"""
        volume = np.ones((10, 10, 10), dtype=np.uint8) * 128

        # Very low isovalue
        thread_low = MeshGenerationThread(volume, 1, 1.0, False)
        assert thread_low.isovalue == 1

        # Very high isovalue
        thread_high = MeshGenerationThread(volume, 254, 1.0, False)
        assert thread_high.isovalue == 254

    def test_small_scale_factor(self):
        """Should handle very small scale factor"""
        volume = np.ones((20, 20, 20), dtype=np.uint8)
        thread = MeshGenerationThread(volume, 50, 0.1, False)

        assert thread.scale_factor == 0.1
