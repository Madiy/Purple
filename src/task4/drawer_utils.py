from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt


class CustomLabel(QLabel):
    def __init__(self, text, parent, background_color=None):
        super().__init__(text, parent)
        if background_color:
            self.setStyleSheet(
                f"QLabel {{background-color: {background_color};}}")

    def setFontSize(self, font_size):
        font = self.font()
        font.setPointSize(font_size)
        self.setFont(font)
        self.resize(self.sizeHint())


class Point(QWidget):
    radius = 50

    def __init__(self, idx, parent=None, font_size=None):
        super().__init__(parent)

        self.town_idx = idx
        self._building = None
        self.font_coefficient = 1.5
        self.idx_label = CustomLabel(str(idx), self)
        self._scale = 0
        self._thickness = 2
        self.show()

    @property
    def thickness(self):
        return int(self.scale * self._thickness)

    @property
    def outer_radius(self):
        return int(self.scale * self.radius) + 1

    @property
    def inner_radius(self):
        return int(self.scale * self.radius * 0.8) + 1

    @property
    def font_size(self):
        return int(self.scale * 1 / len(str(self.town_idx)) * self.radius * 0.8 * self.font_coefficient) + 1

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self.resize((self.outer_radius + self.thickness + 1) * 2, (self.outer_radius + self.thickness + 1) * 2)

    def paintEvent(self, e):
        inner_radius = self.inner_radius
        outer_radius = self.outer_radius
        font_size = self.font_size

        painter = QPainter()
        painter.begin(self)

        painter.setPen(QPen(Qt.black, self.thickness))

        painter.drawEllipse(self.thickness, self.thickness, 2 * outer_radius, 2 * outer_radius)

        painter.setBrush(self._building.color)

        diff = outer_radius - inner_radius
        painter.drawEllipse(diff + self.thickness, diff + self.thickness, 2 * inner_radius, 2 * inner_radius)

        self.idx_label.setFontSize(font_size)
        self.idx_label.move(outer_radius - self.idx_label.width() // 2, outer_radius - self.idx_label.height() // 2)

        painter.end()

    def setBuilding(self, building):
        self._building = building
        self.updateTip()

    def updateTip(self):
        self.setToolTip(str(self._building))
