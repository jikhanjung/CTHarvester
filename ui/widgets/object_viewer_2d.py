"""
ObjectViewer2D - 2D image viewer with ROI selection

Extracted from CTHarvester.py during Phase 4 UI refactoring.
"""

import logging
import os

import numpy as np
from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
)
from PyQt5.QtWidgets import QApplication, QLabel

from config.view_modes import (
    DISTANCE_THRESHOLD,
    MODE_ADD_BOX,
    MODE_EDIT_BOX,
    MODE_EDIT_BOX_PROGRESS,
    MODE_EDIT_BOX_READY,
    MODE_MOVE_BOX,
    MODE_MOVE_BOX_PROGRESS,
    MODE_MOVE_BOX_READY,
    MODE_VIEW,
)

logger = logging.getLogger(__name__)


# MODE dictionary for backward compatibility
MODE = {
    "VIEW": MODE_VIEW,
    "ADD_BOX": MODE_ADD_BOX,
    "MOVE_BOX": MODE_MOVE_BOX,
    "EDIT_BOX": MODE_EDIT_BOX,
    "EDIT_BOX_READY": MODE_EDIT_BOX_READY,
    "EDIT_BOX_PROGRESS": MODE_EDIT_BOX_PROGRESS,
    "MOVE_BOX_PROGRESS": MODE_MOVE_BOX_PROGRESS,
    "MOVE_BOX_READY": MODE_MOVE_BOX_READY,
}


class ObjectViewer2D(QLabel):
    def __init__(self, widget):
        super().__init__(widget)
        self.setMinimumSize(512, 512)
        self.image_canvas_ratio = 1.0
        self.scale = 1.0
        self.mouse_down_x = 0
        self.mouse_down_y = 0
        self.mouse_curr_x = 0
        self.mouse_curr_y = 0
        self.edit_mode = MODE["ADD_BOX"]
        self.orig_pixmap = None
        self.curr_pixmap = None
        self.distance_threshold = self._2imgx(5)
        self.setMouseTracking(True)
        self.object_dialog = None
        self.top_idx = -1
        self.bottom_idx = -1
        self.curr_idx = 0
        self.move_x = 0
        self.move_y = 0
        self.threed_view = None
        self.isovalue = 60
        self.is_inverse = False
        self.reset_crop()

    def get_pixmap_geometry(self):
        if self.curr_pixmap:
            return self.curr_pixmap.rect()

    def set_isovalue(self, isovalue):
        self.isovalue = isovalue
        self.update()

    def set_threed_view(self, threed_view):
        self.threed_view = threed_view

    def reset_crop(self):
        self.crop_from_x = -1
        self.crop_from_y = -1
        self.crop_to_x = -1
        self.crop_to_y = -1
        self.temp_x1 = -1
        self.temp_y1 = -1
        self.temp_x2 = -1
        self.temp_y2 = -1
        self.edit_x1 = False
        self.edit_x2 = False
        self.edit_y1 = False
        self.edit_y2 = False
        self.canvas_box = None
        # If an image is loaded, default ROI to full image
        if self.orig_pixmap is not None:
            self.set_full_roi()

    def set_full_roi(self):
        if self.orig_pixmap is None:
            return
        self.crop_from_x = 0
        self.crop_from_y = 0
        self.crop_to_x = self.orig_pixmap.width()
        self.crop_to_y = self.orig_pixmap.height()
        # canvas_box will be set on next calculate_resize; ensure it's available now as well
        if self.image_canvas_ratio != 0:
            self.canvas_box = QRect(
                self._2canx(self.crop_from_x),
                self._2cany(self.crop_from_y),
                self._2canx(self.crop_to_x - self.crop_from_x),
                self._2cany(self.crop_to_y - self.crop_from_y),
            )

    def is_roi_full_or_empty(self):
        """Check if ROI is not set or covers the entire image."""
        if self.orig_pixmap is None:
            return True
        # Check if ROI is not set
        if (
            self.crop_from_x == -1
            or self.crop_from_y == -1
            or self.crop_to_x == -1
            or self.crop_to_y == -1
        ):
            return True
        # Check if ROI covers entire image
        return (
            self.crop_from_x == 0
            and self.crop_from_y == 0
            and self.crop_to_x == self.orig_pixmap.width()
            and self.crop_to_y == self.orig_pixmap.height()
        )

    def _2canx(self, coord):
        return round((float(coord) / self.image_canvas_ratio) * self.scale)

    def _2cany(self, coord):
        return round((float(coord) / self.image_canvas_ratio) * self.scale)

    def _2imgx(self, coord):
        return round(((float(coord)) / self.scale) * self.image_canvas_ratio)

    def _2imgy(self, coord):
        return round(((float(coord)) / self.scale) * self.image_canvas_ratio)

    def set_mode(self, mode):
        self.edit_mode = mode
        if self.edit_mode == MODE["ADD_BOX"]:
            self.setCursor(Qt.CrossCursor)
        elif self.edit_mode in [
            MODE["MOVE_BOX"],
            MODE["MOVE_BOX_READY"],
            MODE["MOVE_BOX_PROGRESS"],
        ]:
            self.setCursor(Qt.OpenHandCursor)
        elif self.edit_mode in [
            MODE["EDIT_BOX"],
            MODE["EDIT_BOX_READY"],
            MODE["EDIT_BOX_PROGRESS"],
        ]:
            pass
        else:
            self.setCursor(Qt.ArrowCursor)

    def distance_check(self, x, y):
        x = self._2imgx(x)
        y = self._2imgy(y)
        if (
            self.crop_from_x - self.distance_threshold >= x
            or self.crop_to_x + self.distance_threshold <= x
            or self.crop_from_y - self.distance_threshold >= y
            or self.crop_to_y + self.distance_threshold <= y
        ):
            self.edit_x1 = False
            self.edit_x2 = False
            self.edit_y1 = False
            self.edit_y2 = False
            self.inside_box = False
        else:
            if (
                self.crop_from_x + self.distance_threshold <= x
                and self.crop_to_x - self.distance_threshold >= x
                and self.crop_from_y + self.distance_threshold <= y
                and self.crop_to_y - self.distance_threshold >= y
            ):
                self.edit_x1 = False
                self.edit_x2 = False
                self.edit_y1 = False
                self.edit_y2 = False
                self.inside_box = True
                # print("move box ready")
            else:
                self.inside_box = False
            if abs(self.crop_from_x - x) <= self.distance_threshold:
                self.edit_x1 = True
            else:
                self.edit_x1 = False
            if abs(self.crop_to_x - x) <= self.distance_threshold:
                self.edit_x2 = True
            else:
                self.edit_x2 = False
            if abs(self.crop_from_y - y) <= self.distance_threshold:
                self.edit_y1 = True
            else:
                self.edit_y1 = False
            if abs(self.crop_to_y - y) <= self.distance_threshold:
                self.edit_y2 = True
            else:
                self.edit_y2 = False
        self.set_cursor_mode()

    def set_cursor_mode(self):
        if self.edit_x1 and self.edit_y1:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edit_x2 and self.edit_y2:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edit_x1 and self.edit_y2:
            self.setCursor(Qt.SizeBDiagCursor)
        elif self.edit_x2 and self.edit_y1:
            self.setCursor(Qt.SizeBDiagCursor)
        elif self.edit_x1 or self.edit_x2:
            self.setCursor(Qt.SizeHorCursor)
        elif self.edit_y1 or self.edit_y2:
            self.setCursor(Qt.SizeVerCursor)
        elif self.inside_box:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(event)
        if me.buttons() == Qt.LeftButton:
            if self.edit_mode == MODE["ADD_BOX"]:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.temp_x2 = self._2imgx(self.mouse_curr_x)
                self.temp_y2 = self._2imgy(self.mouse_curr_y)
            elif self.edit_mode in [MODE["EDIT_BOX_PROGRESS"], MODE["MOVE_BOX_PROGRESS"]]:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.move_x = self.mouse_curr_x - self.mouse_down_x
                self.move_y = self.mouse_curr_y - self.mouse_down_y
            self.calculate_resize()
        else:
            if self.edit_mode == MODE["EDIT_BOX"]:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    self.set_mode(MODE["EDIT_BOX_READY"])
                elif self.inside_box:
                    self.set_mode(MODE["MOVE_BOX_READY"])
            elif self.edit_mode == MODE["EDIT_BOX_READY"]:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    pass  # self.set_mode(MODE['EDIT_BOX_PROGRESS'])
                elif self.inside_box:
                    self.set_mode(MODE["MOVE_BOX_READY"])
                else:
                    self.set_mode(MODE["EDIT_BOX"])
            elif self.edit_mode == MODE["MOVE_BOX_READY"]:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    self.set_mode(MODE["EDIT_BOX_READY"])
                elif self.inside_box == False:
                    self.set_mode(MODE["EDIT_BOX"])
        self.object_dialog.update_status()
        self.repaint()

    def mousePressEvent(self, event):
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(event)
        if me.button() == Qt.LeftButton:
            # If ROI is full or empty, automatically start creating a new box
            if self.is_roi_full_or_empty():
                self.set_mode(MODE["ADD_BOX"])
                img_x = self._2imgx(me.x())
                img_y = self._2imgy(me.y())
                if (
                    img_x < 0
                    or img_x > self.orig_pixmap.width()
                    or img_y < 0
                    or img_y > self.orig_pixmap.height()
                ):
                    return
                self.temp_x1 = img_x
                self.temp_y1 = img_y
                self.temp_x2 = img_x
                self.temp_y2 = img_y
            elif self.edit_mode == MODE["ADD_BOX"] or self.edit_mode == MODE["EDIT_BOX"]:
                self.set_mode(MODE["ADD_BOX"])
                img_x = self._2imgx(me.x())
                img_y = self._2imgy(me.y())
                if (
                    img_x < 0
                    or img_x > self.orig_pixmap.width()
                    or img_y < 0
                    or img_y > self.orig_pixmap.height()
                ):
                    return
                self.temp_x1 = img_x
                self.temp_y1 = img_y
                self.temp_x2 = img_x
                self.temp_y2 = img_y
            elif self.edit_mode == MODE["EDIT_BOX_READY"]:
                self.mouse_down_x = me.x()
                self.mouse_down_y = me.y()
                self.move_x = 0
                self.move_y = 0
                self.temp_x1 = self.crop_from_x
                self.temp_y1 = self.crop_from_y
                self.temp_x2 = self.crop_to_x
                self.temp_y2 = self.crop_to_y
                self.set_mode(MODE["EDIT_BOX_PROGRESS"])
            elif self.edit_mode == MODE["MOVE_BOX_READY"]:
                self.mouse_down_x = me.x()
                self.mouse_down_y = me.y()
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.move_x = 0
                self.move_y = 0
                self.temp_x1 = self.crop_from_x
                self.temp_y1 = self.crop_from_y
                self.temp_x2 = self.crop_to_x
                self.temp_y2 = self.crop_to_y
                self.set_mode(MODE["MOVE_BOX_PROGRESS"])
        self.object_dialog.update_status()
        self.repaint()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(ev)
        if self.mouse_down_x == me.x() and self.mouse_down_y == me.y():
            return
        if me.button() == Qt.LeftButton:
            if self.edit_mode == MODE["ADD_BOX"]:
                img_x = self._2imgx(self.mouse_curr_x)
                img_y = self._2imgy(self.mouse_curr_y)
                if (
                    img_x < 0
                    or img_x > self.orig_pixmap.width()
                    or img_y < 0
                    or img_y > self.orig_pixmap.height()
                ):
                    return
                self.crop_from_x = min(self.temp_x1, self.temp_x2)
                self.crop_to_x = max(self.temp_x1, self.temp_x2)
                self.crop_from_y = min(self.temp_y1, self.temp_y2)
                self.crop_to_y = max(self.temp_y1, self.temp_y2)
                self.set_mode(MODE["EDIT_BOX"])
            elif self.edit_mode == MODE["EDIT_BOX_PROGRESS"]:
                if self.edit_x1:
                    self.crop_from_x = min(self.temp_x1, self.temp_x2) + self._2imgx(self.move_x)
                if self.edit_x2:
                    self.crop_to_x = max(self.temp_x1, self.temp_x2) + self._2imgx(self.move_x)
                if self.edit_y1:
                    self.crop_from_y = min(self.temp_y1, self.temp_y2) + self._2imgy(self.move_y)
                if self.edit_y2:
                    self.crop_to_y = max(self.temp_y1, self.temp_y2) + self._2imgy(self.move_y)
                self.move_x = 0
                self.move_y = 0
                self.set_mode(MODE["EDIT_BOX"])
            elif self.edit_mode == MODE["MOVE_BOX_PROGRESS"]:
                self.crop_from_x = self.temp_x1 + self._2imgx(self.move_x)
                self.crop_to_x = self.temp_x2 + self._2imgx(self.move_x)
                self.crop_from_y = self.temp_y1 + self._2imgy(self.move_y)
                self.crop_to_y = self.temp_y2 + self._2imgy(self.move_y)
                self.move_x = 0
                self.move_y = 0
                self.set_mode(MODE["MOVE_BOX_READY"])

            from_x = min(self.crop_from_x, self.crop_to_x)
            to_x = max(self.crop_from_x, self.crop_to_x)
            from_y = min(self.crop_from_y, self.crop_to_y)
            to_y = max(self.crop_from_y, self.crop_to_y)
            self.crop_from_x = from_x
            self.crop_from_y = from_y
            self.crop_to_x = to_x
            self.crop_to_y = to_y
            self.canvas_box = QRect(
                self._2canx(from_x),
                self._2cany(from_y),
                self._2canx(to_x - from_x),
                self._2cany(to_y - from_y),
            )
            self.calculate_resize()

        self.object_dialog.update_status()
        self.object_dialog.update_3D_view(True)
        self.repaint()

    def get_crop_area(self, imgxy=False):
        from_x = -1
        to_x = -1
        from_y = -1
        to_y = -1
        if self.edit_mode == MODE["ADD_BOX"]:
            from_x = self._2canx(min(self.temp_x1, self.temp_x2))
            to_x = self._2canx(max(self.temp_x1, self.temp_x2))
            from_y = self._2cany(min(self.temp_y1, self.temp_y2))
            to_y = self._2cany(max(self.temp_y1, self.temp_y2))
            # return [from_x, from_y, to_x, to_y]
        elif self.edit_mode in [MODE["EDIT_BOX_PROGRESS"], MODE["MOVE_BOX_PROGRESS"]]:
            from_x = self._2canx(min(self.temp_x1, self.temp_x2))
            to_x = self._2canx(max(self.temp_x1, self.temp_x2))
            from_y = self._2cany(min(self.temp_y1, self.temp_y2))
            to_y = self._2cany(max(self.temp_y1, self.temp_y2))
            if self.edit_x1 or self.edit_mode == MODE["MOVE_BOX_PROGRESS"]:
                from_x += self.move_x
            if self.edit_x2 or self.edit_mode == MODE["MOVE_BOX_PROGRESS"]:
                to_x += self.move_x
            if self.edit_y1 or self.edit_mode == MODE["MOVE_BOX_PROGRESS"]:
                from_y += self.move_y
            if self.edit_y2 or self.edit_mode == MODE["MOVE_BOX_PROGRESS"]:
                to_y += self.move_y
        elif self.crop_from_x > -1:
            from_x = self._2canx(min(self.crop_from_x, self.crop_to_x))
            to_x = self._2canx(max(self.crop_from_x, self.crop_to_x))
            from_y = self._2cany(min(self.crop_from_y, self.crop_to_y))
            to_y = self._2cany(max(self.crop_from_y, self.crop_to_y))

        if imgxy == True:
            if from_x <= 0 and from_y <= 0 and to_x <= 0 and to_y <= 0 and self.orig_pixmap:
                return [0, 0, self.orig_pixmap.width(), self.orig_pixmap.height()]
            else:
                return [
                    self._2imgx(from_x),
                    self._2imgy(from_y),
                    self._2imgx(to_x),
                    self._2imgy(to_y),
                ]
        else:
            # default to full canvas if ROI not yet defined
            if from_x <= 0 and from_y <= 0 and to_x <= 0 and to_y <= 0 and self.curr_pixmap:
                return [0, 0, self.curr_pixmap.width(), self.curr_pixmap.height()]
            return [from_x, from_y, to_x, to_y]

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.curr_pixmap is not None:
            painter.drawPixmap(0, 0, self.curr_pixmap)

        # overlay: filename, current index, bounds on separate lines
        try:
            file_name = os.path.basename(getattr(self, "fullpath", "") or "")
        except (AttributeError, TypeError):
            file_name = ""
        curr_txt = str(self.curr_idx) if isinstance(self.curr_idx, int) else "-"
        low_txt = (
            str(self.bottom_idx)
            if isinstance(self.bottom_idx, int) and self.bottom_idx >= 0
            else "-"
        )
        up_txt = str(self.top_idx) if isinstance(self.top_idx, int) and self.top_idx >= 0 else "-"
        lines = [
            f"filename: {file_name}",
            f"index: {curr_txt}",
            f"bounds: {low_txt}~{up_txt}",
        ]
        if any(s.strip() for s in lines):
            painter.setRenderHint(QPainter.Antialiasing)
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            fm = QFontMetrics(font)
            pad_x, pad_y, vgap = 8, 4, 2
            tw = max(fm.width(s) for s in lines)
            line_h = fm.height()
            total_h = len(lines) * line_h + (len(lines) - 1) * vgap

            # Decide left/right based on 3D preview position. Use top row, opposite x side.
            x_left = 6
            x_right = max(6, self.width() - (tw + pad_x * 2) - 6)
            x = x_left
            if self.threed_view is not None:
                try:
                    tv = self.threed_view
                    # treat preview on left half → place overlay on right, else left
                    if tv.x() <= self.width() // 2:
                        x = x_right
                    else:
                        x = x_left
                except (AttributeError, TypeError, RuntimeError):
                    x = x_left
            y = 6
            bg_rect = QRect(x, y, tw + pad_x * 2, total_h + pad_y * 2)
            painter.fillRect(bg_rect, QColor(0, 0, 0, 140))
            painter.setPen(QPen(QColor(255, 255, 255)))
            tx = x + pad_x
            ty = y + pad_y + fm.ascent()
            for i, s in enumerate(lines):
                painter.drawText(tx, ty + i * (line_h + vgap), s)

        if self.curr_idx > self.top_idx or self.curr_idx < self.bottom_idx:
            painter.setPen(QPen(QColor(128, 0, 0), 2, Qt.DotLine))
        else:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        [x1, y1, x2, y2] = self.get_crop_area()
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def apply_threshold_and_colorize(
        self, qt_pixmap, threshold, color=np.array([0, 255, 0], dtype=np.uint8)
    ):
        qt_image = qt_pixmap.toImage()
        width = qt_image.width()
        height = qt_image.height()
        buffer = qt_image.bits()
        buffer.setsize(qt_image.byteCount())
        qt_image_array = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))

        # Extract the alpha channel (if present)
        if qt_image_array.shape[2] == 4:
            qt_image_array = qt_image_array[:, :, :3]  # Remove the alpha channel

        color = np.array([0, 255, 0], dtype=np.uint8)

        # Check the dtype of image_array
        if qt_image_array.dtype != np.uint8:
            raise ValueError("image_array should have dtype np.uint8")

        # Check the threshold value (example threshold)
        threshold = self.isovalue
        if not 0 <= threshold <= 255:
            raise ValueError("Threshold should be in the range 0-255")

        [x1, y1, x2, y2] = self.get_crop_area()
        if x1 == x2 == y1 == y2 == 0:
            # whole pixmap is selected
            x1, x2, y1, y2 = 0, qt_image_array.shape[1], 0, qt_image_array.shape[0]

        if self.is_inverse:
            region_mask = qt_image_array[y1 : y2 + 1, x1 : x2 + 1, 0] <= threshold
        else:
            region_mask = qt_image_array[y1 : y2 + 1, x1 : x2 + 1, 0] > threshold

        # Apply the threshold and colorize
        qt_image_array[y1 : y2 + 1, x1 : x2 + 1][region_mask] = color

        # Convert the NumPy array back to a QPixmap
        height, width, channel = qt_image_array.shape
        bytes_per_line = 3 * width
        qt_image = QImage(
            np.copy(qt_image_array.data), width, height, bytes_per_line, QImage.Format_RGB888
        )

        # Convert the QImage to a QPixmap
        modified_pixmap = QPixmap.fromImage(qt_image)
        return modified_pixmap

    def set_image(self, file_path):
        # print("set_image", file_path)
        # check if file exists (try lowercase extension if original doesn't exist)
        actual_path = file_path
        if not os.path.exists(file_path):
            # Try with lowercase extension
            base, ext = os.path.splitext(file_path)
            alt_path = base + ext.lower()
            if os.path.exists(alt_path):
                actual_path = alt_path
            else:
                self.curr_pixmap = None
                self.orig_pixmap = None
                self.crop_from_x = -1
                self.crop_from_y = -1
                self.crop_to_x = -1
                self.crop_to_y = -1
                self.canvas_box = None
                return
        self.fullpath = actual_path
        self.curr_pixmap = self.orig_pixmap = QPixmap(actual_path)

        self.setPixmap(self.curr_pixmap)
        self.calculate_resize()
        # If ROI not yet set, set to full image by default
        if self.crop_from_x < 0 or self.crop_to_x < 0 or self.crop_from_y < 0 or self.crop_to_y < 0:
            self.set_full_roi()
        if self.canvas_box:
            self.crop_from_x = self._2imgx(self.canvas_box.x())
            self.crop_from_y = self._2imgy(self.canvas_box.y())
            self.crop_to_x = self._2imgx(self.canvas_box.x() + self.canvas_box.width())
            self.crop_to_y = self._2imgy(self.canvas_box.y() + self.canvas_box.height())

    def set_top_idx(self, top_idx):
        self.top_idx = top_idx

    def set_curr_idx(self, curr_idx):
        self.curr_idx = curr_idx

    def set_bottom_idx(self, bottom_idx):
        self.bottom_idx = bottom_idx

    def calculate_resize(self):
        # print("objectviewer calculate resize")
        if self.orig_pixmap is not None:
            self.distance_threshold = self._2imgx(DISTANCE_THRESHOLD)
            self.orig_width = self.orig_pixmap.width()
            self.orig_height = self.orig_pixmap.height()
            image_wh_ratio = self.orig_width / self.orig_height
            label_wh_ratio = self.width() / self.height()
            if image_wh_ratio > label_wh_ratio:
                self.image_canvas_ratio = self.orig_width / self.width()
            else:
                self.image_canvas_ratio = self.orig_height / self.height()

            self.curr_pixmap = self.orig_pixmap.scaled(
                int(self.orig_width * self.scale / self.image_canvas_ratio),
                int(self.orig_width * self.scale / self.image_canvas_ratio),
                Qt.KeepAspectRatio,
            )
            # Always colorize current slice by threshold. If range not set, treat as full stack
            if self.isovalue > 0:
                if self.bottom_idx < 0 or self.top_idx < 0 or self.bottom_idx > self.top_idx:
                    # default to full range
                    pass
                self.curr_pixmap = self.apply_threshold_and_colorize(
                    self.curr_pixmap, self.isovalue
                )

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.calculate_resize()
        self.object_dialog.mcube_widget.reposition_self()

        if self.canvas_box:
            self.canvas_box = QRect(
                self._2canx(self.crop_from_x),
                self._2cany(self.crop_from_y),
                self._2canx(self.crop_to_x - self.crop_from_x),
                self._2cany(self.crop_to_y - self.crop_from_y),
            )
        self.threed_view.resize_self()
        return super().resizeEvent(a0)
