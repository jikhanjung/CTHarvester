"""Export and save operations handler for CTHarvester.

This module handles file export and save operations for the main window,
including 3D model export and image stack saving.

Extracted from main_window.py during Phase 3 refactoring to separate
export/save logic from the main window class.

Classes:
    ExportHandler: Manages file export and save operations

Example:
    >>> handler = ExportHandler(main_window)
    >>> handler.export_3d_model_to_obj()  # Export 3D model
    >>> handler.save_cropped_image_stack()  # Save image stack

Note:
    This handler requires a reference to the main window for UI access
    and uses atomic file writes for data integrity.

See Also:
    security.file_validator: Path validation and security
    ui.dialogs: Progress dialog for long operations
"""

import logging
import os
from typing import TYPE_CHECKING, Dict, Tuple

import mcubes
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

from security.file_validator import SecureFileValidator
from ui.dialogs import ProgressDialog
from utils.ui_utils import wait_cursor

if TYPE_CHECKING:
    from ui.main_window import CTHarvesterMainWindow

logger = logging.getLogger(__name__)


class ExportHandler:
    """Handles file export and save operations for CTHarvester main window.

    This class manages:
    - 3D model export to OBJ format (marching cubes algorithm)
    - Cropped image stack saving with progress tracking
    - Atomic file writes for data integrity
    - Progress dialog management

    Args:
        main_window: The main window instance

    Attributes:
        window: Reference to the main window for UI access

    Example:
        >>> handler = ExportHandler(main_window)
        >>> handler.export_3d_model_to_obj()
        >>> handler.save_cropped_image_stack()
    """

    def __init__(self, main_window: "CTHarvesterMainWindow") -> None:
        """Initialize export handler with main window reference.

        Args:
            main_window: The CTHarvester main window instance
        """
        self.window: "CTHarvesterMainWindow" = main_window

    def export_3d_model_to_obj(self) -> None:
        """Export 3D model to OBJ file format using marching cubes.

        Opens a file save dialog, generates a 3D mesh from the current volume
        using the marching cubes algorithm, and saves the result as an OBJ file.

        The process includes:
        1. File save dialog for output path selection
        2. Mesh generation using marching cubes
        3. Vertex coordinate transformation for correct orientation
        4. Atomic file write with error handling

        Note:
            Uses atomic writes (temp file + rename) to prevent corruption.
            Shows error dialog on failure.
        """
        # Get save filename
        obj_filename = self._get_export_filename()
        if not obj_filename:
            return

        # Generate mesh
        try:
            vertices, triangles = self._generate_mesh()
        except Exception as e:
            self._show_error(f"Failed to generate 3D mesh: {e}")
            return

        # Save to OBJ file
        self._save_obj_file(obj_filename, vertices, triangles)

    def _get_export_filename(self) -> str:
        """Show file save dialog for OBJ export.

        Returns:
            Selected filename path, or empty string if cancelled

        Example:
            >>> filename = handler._get_export_filename()
            >>> if filename:
            ...     # User selected a file
        """
        obj_filename, _ = QFileDialog.getSaveFileName(
            self.window, "Save File As", self.window.edtDirname.text(), "OBJ format (*.obj)"
        )

        if obj_filename:
            logger.info(f"Exporting 3D model to: {obj_filename}")
        else:
            logger.info("Export cancelled")

        return obj_filename

    def _generate_mesh(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate 3D mesh using marching cubes algorithm.

        Extracts the cropped volume and isovalue from the UI, runs the
        marching cubes algorithm, and transforms vertices for correct orientation.

        Returns:
            Tuple containing:
                - vertices: Nx3 array of vertex positions
                - triangles: Mx3 array of triangle face indices

        Raises:
            Exception: If mesh generation fails (e.g., invalid volume data)

        Note:
            Vertices are transformed with axis swap: [x,y,z] -> [z,x,y]
            for correct orientation in 3D viewers.
        """
        # Get cropped volume
        threed_volume, _ = self.window.get_cropped_volume()
        isovalue = self.window.image_label.isovalue

        # Run marching cubes
        vertices, triangles = mcubes.marching_cubes(threed_volume, isovalue)

        # Transform vertices (swap axes for correct orientation)
        for i in range(len(vertices)):
            vertices[i] = np.array([vertices[i][2], vertices[i][0], vertices[i][1]])

        return vertices, triangles

    def _save_obj_file(self, filename: str, vertices: np.ndarray, triangles: np.ndarray) -> None:
        """Save mesh to OBJ file format with atomic writes.

        Writes mesh data to a temporary file first, then atomically renames it
        to the target filename to prevent corruption from interrupted writes.

        Args:
            filename: Output file path
            vertices: Nx3 array of vertex positions
            triangles: Mx3 array of triangle face indices (0-indexed)

        Note:
            - Uses atomic file writes (temp + rename) for data integrity
            - Face indices are converted to 1-indexed for OBJ format
            - Temporary file is cleaned up on error
            - Shows error dialog on failure
        """
        validator = SecureFileValidator()
        temp_file = None

        try:
            # Validate output path (use parent directory as base)
            import os
            import tempfile

            base_dir = os.path.dirname(filename) or "."
            validated_path = validator.validate_path(filename, base_dir)

            # Write to temporary file first (atomic write)
            temp_fd, temp_file = tempfile.mkstemp(suffix=".obj", dir=base_dir, text=True)

            with os.fdopen(temp_fd, "w") as fh:
                # Write vertices
                for v in vertices:
                    fh.write(f"v {v[0]} {v[1]} {v[2]}\n")

                # Write faces (1-indexed)
                for f in triangles:
                    fh.write(f"f {f[0] + 1} {f[1] + 1} {f[2] + 1}\n")

            # Atomic rename
            os.replace(temp_file, validated_path)
            temp_file = None  # Successfully moved, don't cleanup

            logger.info(f"Successfully saved OBJ file: {filename}")

        except OSError as e:
            error_msg = f"Failed to save OBJ file (I/O error): {e}"
            self._show_error(error_msg)
            logger.error(error_msg, exc_info=True)
        except ValueError as e:
            error_msg = f"Failed to save OBJ file (invalid data): {e}"
            self._show_error(error_msg)
            logger.error(error_msg, exc_info=True)
        except Exception as e:
            error_msg = f"Failed to save OBJ file (unexpected error): {e}"
            self._show_error(error_msg)
            logger.error(error_msg, exc_info=True)
        finally:
            # Cleanup temporary file if it still exists
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except OSError as e:
                    logger.warning(f"Failed to cleanup temporary file {temp_file}: {e}")

    def save_cropped_image_stack(self) -> None:
        """Save cropped image stack to directory with progress tracking.

        Opens a directory selection dialog, creates a progress dialog,
        and saves all images in the selected range with optional cropping applied.

        The process includes:
        1. Directory selection via dialog
        2. Crop and range information collection
        3. Progress dialog creation and display
        4. Image-by-image processing and saving
        5. Optional directory opening when complete

        Note:
            - Shows progress dialog during save operation
            - Optionally opens target directory after completion
            - Uses wait cursor during processing
            - Platform-specific directory opening (Windows/macOS/Linux)
        """
        # Get save directory
        target_dir = self._get_save_directory()
        if not target_dir:
            return

        # Collect save parameters
        crop_info = self._get_crop_info()
        total_count = crop_info["top_idx"] - crop_info["bottom_idx"] + 1

        # Create and show progress dialog
        progress_dialog = self._create_progress_dialog()

        # Save images
        with wait_cursor():
            try:
                self._save_images_with_progress(target_dir, crop_info, progress_dialog, total_count)
            finally:
                # Cleanup
                progress_dialog.close()

        # Open directory if requested
        if self.window.cbxOpenDirAfter.isChecked():
            import platform
            import subprocess

            if platform.system() == "Windows":
                os.startfile(target_dir)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", target_dir], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", target_dir], check=False)

    def _get_save_directory(self) -> str:
        """Show directory selection dialog for saving image stack.

        Returns:
            Selected directory path, or empty string if cancelled
        """
        target_dirname = QFileDialog.getExistingDirectory(
            self.window, self.window.tr("Select directory to save"), self.window.edtDirname.text()
        )

        if not target_dirname:
            logger.info("Save cancelled")

        return target_dirname

    def _get_crop_info(self) -> Dict[str, int]:
        """Collect crop and range information from UI widgets.

        Returns:
            Dictionary containing crop coordinates and range indices:
                - from_x, from_y: Top-left corner of crop region
                - to_x, to_y: Bottom-right corner of crop region
                - size_idx: Selected thumbnail level index
                - bottom_idx, top_idx: Image range to save
        """
        return {
            "from_x": self.window.image_label.crop_from_x,
            "from_y": self.window.image_label.crop_from_y,
            "to_x": self.window.image_label.crop_to_x,
            "to_y": self.window.image_label.crop_to_y,
            "size_idx": self.window.comboLevel.currentIndex(),
            "top_idx": self.window.image_label.top_idx,
            "bottom_idx": self.window.image_label.bottom_idx,
        }

    def _create_progress_dialog(self) -> ProgressDialog:
        """Create and configure progress dialog for save operation.

        Returns:
            Configured and displayed progress dialog instance

        Note:
            The dialog is modal and shown immediately with 0% progress.
        """
        progress_dialog = ProgressDialog(self.window)
        progress_dialog.update_language()
        progress_dialog.setModal(True)
        progress_dialog.show()
        progress_dialog.lbl_text.setText(self.window.progress_text_1_1)
        progress_dialog.pb_progress.setValue(0)

        return progress_dialog

    def _save_images_with_progress(
        self,
        target_dir: str,
        crop_info: Dict[str, int],
        progress_dialog: ProgressDialog,
        total_count: int,
    ) -> None:
        """Save all images in range with progress updates.

        Iterates through the selected image range, processes each image
        (crop if needed), saves to target directory, and updates progress.

        Args:
            target_dir: Target directory for saved images
            crop_info: Crop and range information dictionary
            progress_dialog: Progress dialog to update
            total_count: Total number of images to save

        Note:
            Continues processing even if individual images fail (logs errors).
        """
        for i, idx in enumerate(range(crop_info["bottom_idx"], crop_info["top_idx"] + 1)):
            # Build filename
            filename = self._build_filename(idx, crop_info["size_idx"])

            # Get source path
            source_path = self._get_source_path(filename, crop_info["size_idx"])

            # Process and save image
            try:
                self._process_and_save_image(source_path, target_dir, filename, crop_info)
            except Exception as e:
                logger.error(f"Error opening/saving image {source_path}: {e}")
                continue

            # Update progress
            self._update_progress(progress_dialog, i + 1, total_count)

    def _build_filename(self, idx: int, size_idx: int) -> str:
        """Build filename for image at given index.

        Constructs filename using prefix, zero-padded index, and file extension
        from the settings hash.

        Args:
            idx: Image index in current range (0-based offset)
            size_idx: Size level index (0=original, 1+=thumbnail levels)

        Returns:
            Formatted filename (e.g., "image_0042.tif")

        Example:
            >>> handler._build_filename(42, 0)
            'image_0042.tif'
        """
        prefix = str(self.window.settings_hash["prefix"])
        seq_begin = int(self.window.level_info[size_idx]["seq_begin"])
        index_length = int(self.window.settings_hash["index_length"])
        file_type = str(self.window.settings_hash["file_type"])

        return prefix + str(seq_begin + idx).zfill(index_length) + "." + file_type

    def _get_source_path(self, filename: str, size_idx: int) -> str:
        """Get full validated source path for image file.

        Constructs the full path to the source image, handling both original
        images and thumbnail levels. Uses secure path joining to prevent
        path traversal attacks.

        Args:
            filename: Image filename (without path)
            size_idx: Size level index (0=original, 1+=thumbnail levels)

        Returns:
            Full validated path to source image

        Note:
            Uses SecureFileValidator.safe_join() to prevent path traversal.
        """
        validator = SecureFileValidator()
        base_dir = self.window.edtDirname.text()

        if size_idx == 0:
            source_dir = base_dir
        else:
            # Use safe_join to prevent path traversal
            source_dir = validator.safe_join(base_dir, ".thumbnail", str(size_idx))

        return validator.safe_join(source_dir, filename)

    def _process_and_save_image(
        self, source_path: str, target_dir: str, filename: str, crop_info: Dict[str, int]
    ) -> None:
        """Open image, apply crop if needed, and save to target directory.

        Args:
            source_path: Source image path (full path)
            target_dir: Target directory for output
            filename: Output filename (without path)
            crop_info: Crop information dictionary with from_x, from_y, to_x, to_y

        Note:
            - Crop is only applied if from_x > -1
            - Uses SecureFileValidator for path validation
            - Image is opened and closed within context manager
        """
        validator = SecureFileValidator()

        with Image.open(source_path) as img:
            # Apply crop if specified
            if crop_info["from_x"] > -1:
                img = img.crop(
                    (crop_info["from_x"], crop_info["from_y"], crop_info["to_x"], crop_info["to_y"])
                )

            # Save image with secure path
            output_path = validator.safe_join(target_dir, filename)
            img.save(output_path)

    def _update_progress(self, progress_dialog: ProgressDialog, current: int, total: int) -> None:
        """Update progress dialog with current progress.

        Args:
            progress_dialog: Progress dialog to update
            current: Current progress (1-based index)
            total: Total number of items

        Note:
            Calls QApplication.processEvents() to keep UI responsive.
        """
        progress_dialog.lbl_text.setText(self.window.progress_text_1_2.format(current, total))
        progress_dialog.pb_progress.setValue(int((current / float(total)) * 100))
        progress_dialog.update()
        QApplication.processEvents()

    def _show_error(self, message: str) -> None:
        """Show error message dialog to user.

        Args:
            message: Error message to display

        Note:
            The message is translated using window.tr() before display.
        """
        QMessageBox.critical(self.window, self.window.tr("Error"), self.window.tr(message))
