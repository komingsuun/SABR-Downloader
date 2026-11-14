from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class TimelineWidget(QWidget):
    range_changed = Signal(float, float)   # start_sec, end_sec

    HANDLE_HIT = 10          # px
    MIN_CLIP = 0.2           # detik
    STRIP_HEIGHT = 64
    RULER_HEIGHT = 26

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 0.0
        self.start_sec = 0.0
        self.end_sec = 0.0
        self._thumbs: list[QPixmap] = []
        self._dragging: str | None = None
        self._hover: str | None = None

        self.setMinimumHeight(self.STRIP_HEIGHT + self.RULER_HEIGHT + 6)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    # ---------- public API ----------
    def set_duration(self, duration: float):
        self.duration = max(0.0, float(duration))
        if self.end_sec <= self.start_sec or self.end_sec > self.duration:
            self.end_sec = self.duration
        self.update()

    def set_range(self, start_sec: float, end_sec: float):
        start = max(0.0, min(float(start_sec), self.duration))
        end = max(0.0, min(float(end_sec), self.duration))
        if end - start < self.MIN_CLIP:
            end = min(self.duration, start + self.MIN_CLIP)
        self.start_sec, self.end_sec = start, end
        self.update()

    def start_seconds(self) -> float:
        return self.start_sec

    def end_seconds(self) -> float:
        return self.end_sec

    def set_thumbnail_at(self, index: int, image: QImage):
        while len(self._thumbs) <= index:
            self._thumbs.append(QPixmap())
        self._thumbs[index] = QPixmap.fromImage(image)
        self.update()

    def set_thumbnails_count(self, count: int):
        # pre-allocate slot kosong
        if count <= 0:
            self._thumbs = []
        else:
            while len(self._thumbs) < count:
                self._thumbs.append(QPixmap())
        self.update()

    def clear_thumbnails(self):
        self._thumbs = []
        self.update()

    # ---------- geometry helpers ----------
    def _strip_rect(self) -> QRect:
        return QRect(0, 0, self.width(), self.STRIP_HEIGHT)

    def _ruler_rect(self) -> QRect:
        return QRect(0, self.STRIP_HEIGHT + 4, self.width(), self.RULER_HEIGHT)

    def _x_to_sec(self, x: int) -> float:
        if self.width() <= 0:
            return 0.0
        ratio = max(0.0, min(1.0, x / self.width()))
        return ratio * self.duration

    def _sec_to_x(self, sec: float) -> int:
        if self.duration <= 0:
            return 0
        return int(max(0.0, min(1.0, sec / self.duration)) * self.width())

    def _hit_handle(self, pos) -> str | None:
        if self.duration <= 0:
            return None
        xs = self._sec_to_x(self.start_sec)
        xe = self._sec_to_x(self.end_sec)
        if abs(pos.x() - xs) <= self.HANDLE_HIT:
            return "start"
        if abs(pos.x() - xe) <= self.HANDLE_HIT:
            return "end"
        return None

    # ---------- events ----------
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        hit = self._hit_handle(event.position().toPoint())
        if hit:
            self._dragging = hit
            self.setCursor(Qt.SizeHorCursor)
            event.accept()
            return
        # klik di strip → pindahkan handle terdekat
        sec = self._x_to_sec(int(event.position().x()))
        if abs(sec - self.start_sec) < abs(sec - self.end_sec):
            self._dragging = "start"
        else:
            self._dragging = "end"
        self._apply_drag(sec)
        self.setCursor(Qt.SizeHorCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._dragging:
            self._apply_drag(self._x_to_sec(pos.x()))
            event.accept()
            return
        hit = self._hit_handle(pos)
        if hit != self._hover:
            self._hover = hit
            self.setCursor(Qt.SizeHorCursor if hit else Qt.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = None
            self.setCursor(Qt.ArrowCursor)
            self.range_changed.emit(self.start_sec, self.end_sec)
            event.accept()

    def keyPressEvent(self, event):
        step = 1.0 if event.modifiers() & Qt.ShiftModifier else 0.1
        if event.key() == Qt.Key_Left:
            self.set_range(self.start_sec - step, self.end_sec)
            self.range_changed.emit(self.start_sec, self.end_sec)
        elif event.key() == Qt.Key_Right:
            self.set_range(self.start_sec + step, self.end_sec)
            self.range_changed.emit(self.start_sec, self.end_sec)
        else:
            super().keyPressEvent(event)

    def _apply_drag(self, sec: float):
        if self._dragging == "start":
            new_start = max(0.0, min(sec, self.end_sec - self.MIN_CLIP))
            self.start_sec = new_start
        elif self._dragging == "end":
            new_end = min(self.duration, max(sec, self.start_sec + self.MIN_CLIP))
            self.end_sec = new_end
        self.update()

    # ---------- painting ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#0f172a"))

        strip = self._strip_rect()
        ruler = self._ruler_rect()

        # strip thumbnail
        if self._thumbs and self.duration > 0:
            n = len(self._thumbs)
            cell_w = strip.width() / n
            for i, pix in enumerate(self._thumbs):
                x = int(i * cell_w)
                w = int(cell_w) + 1
                cell = QRect(x, strip.top(), w, strip.height())
                if pix.isNull():
                    painter.fillRect(cell, QColor("#1e293b"))
                else:
                    scaled = pix.scaled(
                        cell.size(),
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation,
                    )
                    # crop center
                    sx = max(0, (scaled.width() - cell.width()) // 2)
                    sy = max(0, (scaled.height() - cell.height()) // 2)
                    painter.drawPixmap(cell, scaled, QRect(sx, sy, cell.width(), cell.height()))
        else:
            painter.fillRect(strip, QColor("#1e293b"))

        if self.duration <= 0:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(strip, Qt.AlignCenter, "Pilih file video untuk melihat timeline")
            painter.end()
            return

        # overlay di luar seleksi (gelap)
        xs = self._sec_to_x(self.start_sec)
        xe = self._sec_to_x(self.end_sec)
        painter.fillRect(QRect(0, strip.top(), xs, strip.height()), QColor(0, 0, 0, 140))
        painter.fillRect(QRect(xe, strip.top(), strip.width() - xe, strip.height()), QColor(0, 0, 0, 140))

        # garis seleksi
        painter.setPen(QPen(QColor("#38bdf8"), 2))
        painter.drawLine(xs, strip.top(), xs, strip.bottom())
        painter.drawLine(xe, strip.top(), xe, strip.bottom())

        # handle (kotak kecil di atas & bawah garis)
        handle_w = 6
        painter.fillRect(QRect(xs - handle_w // 2, strip.top(), handle_w, 10), QColor("#0ea5e9"))
        painter.fillRect(QRect(xe - handle_w // 2, strip.top(), handle_w, 10), QColor("#0ea5e9"))

        # ruler
        painter.fillRect(ruler, QColor("#0b1220"))
        painter.setPen(QColor("#334155"))
        painter.drawLine(0, ruler.top(), ruler.width(), ruler.top())

        # tick + label (10 tick)
        font = QFont("Consolas", 8)
        painter.setFont(font)
        tick_count = 10
        for i in range(tick_count + 1):
            ratio = i / tick_count
            x = int(ratio * ruler.width())
            t = ratio * self.duration
            painter.setPen(QColor("#475569"))
            painter.drawLine(x, ruler.top(), x, ruler.top() + 5)
            painter.setPen(QColor("#94a3b8"))
            label = self._fmt_time(t)
            painter.drawText(x + 3, ruler.top() + 18, label)

        # label start & end di bawah handle
        painter.setPen(QColor("#38bdf8"))
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.drawText(xs + 4, ruler.bottom() - 2, self._fmt_time(self.start_sec))
        painter.drawText(xe - 50, ruler.bottom() - 2, self._fmt_time(self.end_sec))

        # durasi klip di tengah seleksi
        painter.setPen(QColor("#e2e8f0"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        clip_len = self.end_sec - self.start_sec
        mid_x = (xs + xe) // 2
        painter.drawText(
            QRect(mid_x - 60, strip.top() + strip.height() - 22, 120, 18),
            Qt.AlignCenter,
            f"klip: {self._fmt_time(clip_len)}",
        )

        painter.end()

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = max(0.0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        if h:
            return f"{h}:{m:02d}:{s:05.2f}"
        return f"{m}:{s:05.2f}"