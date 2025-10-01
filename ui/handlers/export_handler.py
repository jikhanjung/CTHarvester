"""
ExportHandler - Export and save operations for CTHarvesterMainWindow

Separates file export/save logic from main window class.
Extracted from main_window.py export_3d_model() and save_result() methods
(Phase 3: Export Operations Separation)
"""

import logging
import os

import mcubes
import numpy as np
from PIL import Image
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

from security.file_validator import SecureFileValidator
from ui.dialogs import ProgressDialog

logger = logging.getLogger(__name__)


class ExportHandler:
    """
    Handles file export and save operations for CTHarvesterMainWindow.

    This class manages:
    - 3D model export to OBJ format
    - Cropped image stack saving
    - Progress dialog management
    """

    def __init__(self, main_window):
        """
        Initialize export handler.

        Args:
            main_window (CTHarvesterMainWindow): The main window instance
        """
        self.window = main_window

    def export_3d_model_to_obj(self):
        """
        Export 3D model to OBJ file format.

        Shows file save dialog, generates mesh using marching cubes,
        and saves vertices and faces to OBJ file.
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

    def _get_export_filename(self):
        """
        Show file save dialog for OBJ export.

        Returns:
            str: Selected filename, or empty string if cancelled
        """
        obj_filename, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save File As",
            self.window.edtDirname.text(),
            "OBJ format (*.obj)"
        )

        if obj_filename:
            logger.info(f"Exporting 3D model to: {obj_filename}")
        else:
            logger.info("Export cancelled")

        return obj_filename

    def _generate_mesh(self):
        """
        Generate 3D mesh using marching cubes algorithm.

        Returns:
            tuple: (vertices, triangles) arrays

        Raises:
            Exception: If mesh generation fails
        """
        # Get cropped volume
        threed_volume, _ = self.window.get_cropped_volume()
        isovalue = self.window.image_label.isovalue

        # Run marching cubes
        vertices, triangles = mcubes.marching_cubes(threed_volume, isovalue)

        # Transform vertices (swap axes for correct orientation)
        for i in range(len(vertices)):
            vertices[i] = np.array([
                vertices[i][2],
                vertices[i][0],
                vertices[i][1]
            ])

        return vertices, triangles

    def _save_obj_file(self, filename, vertices, triangles):
        """
        Save mesh to OBJ file format.

        Args:
            filename (str): Output file path
            vertices (np.ndarray): Vertex positions
            triangles (np.ndarray): Triangle face indices
        """
        validator = SecureFileValidator()

        try:
            # Validate output path
            validated_path = validator.validate_path(filename)
            with open(validated_path, "w") as fh:
                # Write vertices
                for v in vertices:
                    fh.write(f"v {v[0]} {v[1]} {v[2]}\n")

                # Write faces (1-indexed)
                for f in triangles:
                    fh.write(f"f {f[0] + 1} {f[1] + 1} {f[2] + 1}\n")

            logger.info(f"Successfully saved OBJ file: {filename}")

        except Exception as e:
            self._show_error(f"Failed to save OBJ file: {e}")
            logger.error(f"Error saving OBJ file: {e}")

    def save_cropped_image_stack(self):
        """
        Save cropped image stack to directory.

        Shows directory selection dialog, creates progress dialog,
        and saves all images in the selected range with cropping applied.
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
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            self._save_images_with_progress(target_dir, crop_info, progress_dialog, total_count)
        finally:
            # Cleanup
            QApplication.restoreOverrideCursor()
            progress_dialog.close()

        # Open directory if requested
        if self.window.cbxOpenDirAfter.isChecked():
            os.startfile(target_dir)

    def _get_save_directory(self):
        """
        Show directory selection dialog for saving.

        Returns:
            str: Selected directory, or empty string if cancelled
        """
        target_dirname = QFileDialog.getExistingDirectory(
            self.window,
            self.window.tr("Select directory to save"),
            self.window.edtDirname.text()
        )

        if not target_dirname:
            logger.info("Save cancelled")

        return target_dirname

    def _get_crop_info(self):
        """
        Collect crop and range information from UI.

        Returns:
            dict: Dictionary containing crop coordinates and range indices
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

    def _create_progress_dialog(self):
        """
        Create and configure progress dialog.

        Returns:
            ProgressDialog: Configured progress dialog
        """
        progress_dialog = ProgressDialog(self.window)
        progress_dialog.update_language()
        progress_dialog.setModal(True)
        progress_dialog.show()
        progress_dialog.lbl_text.setText(self.window.progress_text_1_1)
        progress_dialog.pb_progress.setValue(0)

        return progress_dialog

    def _save_images_with_progress(self, target_dir, crop_info, progress_dialog, total_count):
        """
        Save all images in range with progress updates.

        Args:
            target_dir (str): Target directory for saved images
            crop_info (dict): Crop and range information
            progress_dialog (ProgressDialog): Progress dialog to update
            total_count (int): Total number of images to save
        """
        for i, idx in enumerate(range(crop_info["bottom_idx"], crop_info["top_idx"] + 1)):
            # Build filename
            filename = self._build_filename(idx, crop_info["size_idx"])

            # Get source path
            source_path = self._get_source_path(filename, crop_info["size_idx"])

            # Process and save image
            try:
                self._process_and_save_image(
                    source_path,
                    target_dir,
                    filename,
                    crop_info
                )
            except Exception as e:
                logger.error(f"Error opening/saving image {source_path}: {e}")
                continue

            # Update progress
            self._update_progress(progress_dialog, i + 1, total_count)

    def _build_filename(self, idx, size_idx):
        """
        Build filename for image at given index.

        Args:
            idx (int): Image index in current range
            size_idx (int): Size level index

        Returns:
            str: Formatted filename
        """
        return (
            self.window.settings_hash["prefix"]
            + str(self.window.level_info[size_idx]["seq_begin"] + idx).zfill(
                self.window.settings_hash["index_length"]
            )
            + "."
            + self.window.settings_hash["file_type"]
        )

    def _get_source_path(self, filename, size_idx):
        """
        Get full source path for image file.

        Args:
            filename (str): Image filename
            size_idx (int): Size level index (0 = original, >0 = thumbnail)

        Returns:
            str: Full path to source image
        """
        validator = SecureFileValidator()
        base_dir = self.window.edtDirname.text()

        if size_idx == 0:
            source_dir = base_dir
        else:
            # Use safe_join to prevent path traversal
            source_dir = validator.safe_join(base_dir, ".thumbnail", str(size_idx))

        return validator.safe_join(source_dir, filename)

    def _process_and_save_image(self, source_path, target_dir, filename, crop_info):
        """
        Open image, apply crop if needed, and save to target directory.

        Args:
            source_path (str): Source image path
            target_dir (str): Target directory
            filename (str): Output filename
            crop_info (dict): Crop information
        """
        validator = SecureFileValidator()

        with Image.open(source_path) as img:
            # Apply crop if specified
            if crop_info["from_x"] > -1:
                img = img.crop((
                    crop_info["from_x"],
                    crop_info["from_y"],
                    crop_info["to_x"],
                    crop_info["to_y"]
                ))

            # Save image with secure path
            output_path = validator.safe_join(target_dir, filename)
            img.save(output_path)

    def _update_progress(self, progress_dialog, current, total):
        """
        Update progress dialog.

        Args:
            progress_dialog (ProgressDialog): Progress dialog to update
            current (int): Current progress (1-based)
            total (int): Total count
        """
        progress_dialog.lbl_text.setText(
            self.window.progress_text_1_2.format(current, total)
        )
        progress_dialog.pb_progress.setValue(
            int((current / float(total)) * 100)
        )
        progress_dialog.update()
        QApplication.processEvents()

    def _show_error(self, message):
        """
        Show error message dialog.

        Args:
            message (str): Error message to display
        """
        QMessageBox.critical(
            self.window,
            self.window.tr("Error"),
            self.window.tr(message)
        )
