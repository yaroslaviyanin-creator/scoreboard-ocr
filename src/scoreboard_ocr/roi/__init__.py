"""ROI (Region of Interest) — graphical interactive rectangle for defining OCR zones."""

import logging
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor, QBrush, QFont

logger = logging.getLogger(__name__)


class ROIRect(QGraphicsRectItem):
    """
    Interactive ROI rectangle on the video scene.
    Supports: move, resize (bottom-right corner), double-click for settings.
    """

    def __init__(self, x: float, y: float, w: float, h: float, name: str = "Zone"):
        super().__init__(0, 0, w, h)
        self.setPos(x, y)
        self.id = str(id(self))
        self.name = name
        self.mode = "Standard"
        self.params: dict = {
            "blur": 5,
            "thresh": 130,
            "morph": 1,
            "sens": 35,
            "tilt": 0,
        }

        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setPen(QPen(QColor(255, 0, 0), 2))
        self.setBrush(QBrush(QColor(255, 0, 0, 40)))

        self.text_item = QGraphicsTextItem(self.name, self)
        self.text_item.setDefaultTextColor(QColor(255, 255, 255))
        self.text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.text_item.setPos(0, -25)

        self._resizing = False

    def update_label(self) -> None:
        """Update the text label above the rectangle."""
        self.text_item.setPlainText(self.name)

    def hoverMoveEvent(self, event) -> None:
        """Show resize cursor when near bottom-right corner."""
        p = event.pos()
        r = self.rect()
        if p.x() > r.width() - 15 and p.y() > r.height() - 15:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Begin resize if bottom-right corner is clicked."""
        p = event.pos()
        r = self.rect()
        if p.x() > r.width() - 15 and p.y() > r.height() - 15:
            self._resizing = True
            event.accept()
        else:
            self._resizing = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Handle resize or move."""
        if self._resizing:
            self.prepareGeometryChange()
            new_w = max(20, event.pos().x())
            new_h = max(20, event.pos().y())
            self.setRect(0, 0, new_w, new_h)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._resizing = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Open settings dialog on double-click."""
        from .roi_settings_dialog import ROISettingsDialog
        self._dialog = ROISettingsDialog(self)
        self._dialog.show()
