from PyQt5 import QtCore, QtGui, QtWidgets
from enum import IntEnum


class VerticalTimeline(QtWidgets.QWidget):
    lowerChanged = QtCore.pyqtSignal(int)
    upperChanged = QtCore.pyqtSignal(int)
    currentChanged = QtCore.pyqtSignal(int)
    rangeChanged  = QtCore.pyqtSignal(int, int)

    class Thumb(IntEnum):
        NONE   = 0
        LOWER  = 1
        CURRENT= 2
        UPPER  = 3

    def __init__(self, minimum=0, maximum=100, parent=None):
        super().__init__(parent)
        # extra width to accommodate left current tag and right bound marks
        self.setMinimumWidth(56)
        # geometry and visual tuning
        self._margin_left = 24
        self._margin_right = 28
        self._shaft_width = 3
        self._shade_width = 12
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # model
        self._min = int(minimum)
        self._max = int(maximum)
        self._lower = self._min
        self._upper = self._max
        self._current = self._min
        self._step = 1
        self._page = 10

        # interaction
        self._drag_target = self.Thumb.NONE
        self._drag_offset = 0
        self._shift_slip  = False

        # snap
        self._snap_points = []
        self._snap_tol = 0

    # ---------- public API ----------
    def setRange(self, minimum, maximum):
        minimum, maximum = int(minimum), int(maximum)
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        self._min, self._max = minimum, maximum
        self._lower = max(self._min, min(self._lower, self._max))
        self._upper = max(self._min, min(self._upper, self._max))
        if self._lower > self._upper:
            self._lower, self._upper = self._upper, self._lower
        self._current = max(self._min, min(self._current, self._max))
        self.update()
        self.rangeChanged.emit(self._lower, self._upper)

    def setLower(self, v):
        v = self._coerce(v)
        if v > self._upper: v = self._upper
        if v != self._lower:
            self._lower = v
            self.lowerChanged.emit(self._lower)
            self.rangeChanged.emit(self._lower, self._upper)
            self.update()

    def setUpper(self, v):
        v = self._coerce(v)
        if v < self._lower: v = self._lower
        if v != self._upper:
            self._upper = v
            self.upperChanged.emit(self._upper)
            self.rangeChanged.emit(self._lower, self._upper)
            self.update()

    def setCurrent(self, v):
        v = self._coerce(v)
        # current is independent of lower/upper; clamp only to [min, max]
        if v != self._current:
            self._current = v
            self.currentChanged.emit(self._current)
            self.update()

    def values(self):
        return self._lower, self._current, self._upper

    def setStep(self, single=1, page=10):
        self._step, self._page = max(1, int(single)), max(1, int(page))

    def setSnapPoints(self, points, tol=3):
        self._snap_points = sorted(set(int(p) for p in points))
        self._snap_tol = max(0, int(tol))

    # convenience getters/setters
    def minimum(self):
        return self._min

    def maximum(self):
        return self._max

    def getRange(self):
        return self._lower, self._upper

    def setRangeValues(self, lower, upper):
        self.setLower(lower)
        self.setUpper(upper)

    def setValues(self, lower=None, current=None, upper=None):
        if lower is not None:
            self.setLower(lower)
        if upper is not None:
            self.setUpper(upper)
        if current is not None:
            self.setCurrent(current)

    # ---------- QWidget overrides ----------
    def sizeHint(self):
        return QtCore.QSize(32, 240)

    def minimumSizeHint(self):
        return QtCore.QSize(28, 120)

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        track = self._track_rect()
        # shading band (wider than shaft)
        shade = QtCore.QRectF(track.center().x() - self._shade_width/2.0, track.top(), self._shade_width, track.height())

        # range shading
        y_lower = self._val_to_y(self._lower, track)
        y_upper = self._val_to_y(self._upper, track)
        inside  = QtCore.QRectF(shade.left(), y_upper, shade.width(), y_lower-y_upper)
        outside_top    = QtCore.QRectF(shade.left(), shade.top(), shade.width(), y_upper-shade.top())
        outside_bottom = QtCore.QRectF(shade.left(), y_lower, shade.width(), shade.bottom()-y_lower)

        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(150,150,150))  # inside (selected)
        p.drawRect(inside)
        p.setBrush(QtGui.QColor(230,230,230))  # outside (dim)
        p.drawRect(outside_top)
        p.drawRect(outside_bottom)

        # shaft (actual stack line) - thin and dark
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(20,20,20))
        p.drawRect(track)

        # snap points (optional, faint)
        if self._snap_points:
            pen = QtGui.QPen(QtGui.QColor(180,180,180))
            pen.setWidth(1)
            p.setPen(pen)
            for sp in self._snap_points:
                y = self._val_to_y(sp, track)
                p.drawLine(QtCore.QPointF(track.left(), y), QtCore.QPointF(track.right(), y))

        # current indicator line (subtle)
        y_cur = self._val_to_y(self._current, track)
        pen = QtGui.QPen(QtGui.QColor(120, 170, 220))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawLine(QtCore.QPointF(track.left()-12, y_cur), QtCore.QPointF(track.right()+24, y_cur))

        # bounds and current handle
        self._draw_bound_right(p, track, y_lower, is_upper=False)  # lower marker (triangle up under the line)
        self._draw_bound_right(p, track, y_upper, is_upper=True)   # upper marker (triangle down above the line)
        self._draw_current_tag_left(p, track, y_cur, QtGui.QColor(30,144,255))       # current tag on the left

    def mousePressEvent(self, ev):
        if ev.button() != QtCore.Qt.LeftButton:
            return
        r, track = self.rect(), self._track_rect()
        y = ev.pos().y()
        # hit test: prioritize current, then lower/upper
        if self._hit_diamond(y, track, self._current):
            self._drag_target = self.Thumb.CURRENT
        elif self._hit_thumb(y, track, self._lower):
            self._drag_target = self.Thumb.LOWER
        elif self._hit_thumb(y, track, self._upper):
            self._drag_target = self.Thumb.UPPER
        else:
            # click empty area → move current
            self.setCurrent(self._y_to_val(y, track))
            self._drag_target = self.Thumb.CURRENT
        self._shift_slip = ev.modifiers() & QtCore.Qt.ShiftModifier
        self._drag_offset = 0
        self.setCursor(QtCore.Qt.ClosedHandCursor)

    def mouseMoveEvent(self, ev):
        if self._drag_target == self.Thumb.NONE:
            return
        track = self._track_rect()
        v = self._y_to_val(ev.pos().y(), track)
        v = self._apply_snap(v)
        if self._drag_target == self.Thumb.CURRENT:
            self.setCurrent(v)
        elif self._drag_target == self.Thumb.LOWER:
            if self._shift_slip:
                # move both,保持폭
                span = self._upper - self._lower
                v = min(v, self._max - span)
                self.setLower(v)
                self.setUpper(v + span)
            else:
                self.setLower(v)
        elif self._drag_target == self.Thumb.UPPER:
            if self._shift_slip:
                span = self._upper - self._lower
                v = max(v, self._min + span)
                self.setUpper(v)
                self.setLower(v - span)
            else:
                self.setUpper(v)

    def mouseReleaseEvent(self, ev):
        self._drag_target = self.Thumb.NONE
        self._shift_slip = False
        self.unsetCursor()

    def wheelEvent(self, ev):
        delta = ev.angleDelta().y()
        step = self._page if (ev.modifiers() & QtCore.Qt.ControlModifier) else self._step
        self.setCurrent(self._current + (step if delta > 0 else -step))

    def keyPressEvent(self, ev):
        k = ev.key()
        if   k == QtCore.Qt.Key_Up:    self.setCurrent(self._current + self._step)
        elif k == QtCore.Qt.Key_Down:  self.setCurrent(self._current - self._step)
        elif k == QtCore.Qt.Key_PageUp:   self.setCurrent(self._current + self._page)
        elif k == QtCore.Qt.Key_PageDown: self.setCurrent(self._current - self._page)
        elif k == QtCore.Qt.Key_Home:  self.setCurrent(self._min)
        elif k == QtCore.Qt.Key_End:   self.setCurrent(self._max)
        elif k == QtCore.Qt.Key_L:     self.setLower(self._current)
        elif k == QtCore.Qt.Key_U:     self.setUpper(self._current)
        else:
            super().keyPressEvent(ev)

    # ---------- helpers ----------
    def _coerce(self, v):
        return max(self._min, min(int(v), self._max))

    def _val_to_y(self, v, track):
        # top=max, bottom=min (세로 슬라이더 관성)
        frac = (v - self._min) / max(1, (self._max - self._min))
        return track.bottom() - frac * track.height()

    def _y_to_val(self, y, track):
        frac = (track.bottom() - y) / max(1, track.height())
        v = round(self._min + frac * (self._max - self._min))
        return self._coerce(v)

    def _track_rect(self):
        r = self.rect().adjusted(self._margin_left, 8, -self._margin_right, -8)
        cx = r.center().x()
        return QtCore.QRectF(cx - self._shaft_width/2.0, r.top(), self._shaft_width, r.height())

    def _draw_thumb(self, p, track, y, color):
        # legacy thumb (unused now); keep for reference
        w = track.width()
        path = QtGui.QPainterPath()
        r = QtCore.QRectF(track.left()-3, y-7, w+6, 14)
        path.addRoundedRect(r, 3, 3)
        p.setPen(QtGui.QPen(QtGui.QColor(80,80,80)))
        p.setBrush(QtGui.QBrush(color))
        p.drawPath(path)

    def _draw_current_tag_left(self, p, track, y, color):
        # pentagon tag on the left of the track, pointing right into the track
        tip_extra = 2  # extend tip into the track
        tip_x = track.left() + tip_extra
        rect_w = 22
        half_h = 8
        poly = QtGui.QPolygonF([
            QtCore.QPointF(tip_x - rect_w, y - half_h),
            QtCore.QPointF(tip_x - 10,      y - half_h),
            QtCore.QPointF(tip_x,          y),
            QtCore.QPointF(tip_x - 10,      y + half_h),
            QtCore.QPointF(tip_x - rect_w, y + half_h),
        ])
        pen = QtGui.QPen(QtGui.QColor(10,10,10))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(QtGui.QBrush(color))
        p.drawPolygon(poly)

    def _draw_bound_right(self, p, track, y, is_upper):
        # right-side marker: short horizontal guide line + triangle above/below indicating limit
        line_len = 28
        x0 = track.right()
        x1 = x0 + line_len
        pen = QtGui.QPen(QtGui.QColor(80,80,80))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(QtCore.QPointF(x0, y), QtCore.QPointF(x1, y))

        tri_size = 10
        cx = x0 + line_len * 0.5
        if is_upper:
            # triangle pointing down, above the line
            poly = QtGui.QPolygonF([
                QtCore.QPointF(cx, y),
                QtCore.QPointF(cx - tri_size, y - tri_size),
                QtCore.QPointF(cx + tri_size, y - tri_size),
            ])
        else:
            # triangle pointing up, below the line
            poly = QtGui.QPolygonF([
                QtCore.QPointF(cx, y),
                QtCore.QPointF(cx - tri_size, y + tri_size),
                QtCore.QPointF(cx + tri_size, y + tri_size),
            ])
        pen2 = QtGui.QPen(QtGui.QColor(160,20,20))
        pen2.setWidth(2)
        p.setPen(pen2)
        p.setBrush(QtGui.QBrush(QtGui.QColor(220,60,60)))
        p.drawPolygon(poly)

    def _hit_thumb(self, y, track, value):
        yy = self._val_to_y(value, track)
        return abs(y - yy) <= 8

    def _hit_diamond(self, y, track, value):
        yy = self._val_to_y(value, track)
        return abs(y - yy) <= 10

    def _apply_snap(self, v):
        if not self._snap_points or self._snap_tol <= 0:
            return v
        # 가장 가까운 스냅 포인트가 tol 이내면 붙이기
        best = None
        best_d = 1e9
        for sp in self._snap_points:
            d = abs(sp - v)
            if d < best_d:
                best_d, best = d, sp
        return best if best is not None and best_d <= self._snap_tol else v
