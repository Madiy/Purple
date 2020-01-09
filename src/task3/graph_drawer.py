from PyQt5.QtWidgets import (QWidget, QLabel,
                             QLineEdit )
from PyQt5.QtGui import QPainter, QBrush, QPen,QImage
from PyQt5.QtCore import Qt, QPoint
from data_models import Crossroad, Town, Market, Warehouse
from drawer_utils import CustomLabel, Point
import os

buildings_to_type = {
    0: Crossroad,
    1: Town,
    2: Market,
    3: Warehouse
}


class GraphDrawer(QWidget):
    def __init__(self):
        super().__init__()
        self.graph = None
        self.buildings = None
        self.padding = 50
        self.idx_to_widget = {}
        self.idx_to_building = {}
        self.edges_to_weights = {}
        self.zoom = 1
        self.delta = QPoint(0, 0)
        self.start = self.delta
        self.is_visible_weight = False
        self.pressing = False
        self.initUI()

    def initUI(self):
        directory = os.path.dirname(os.path.abspath(__file__))   
        self.train_image=QImage(os.path.join(directory, "train.png"))        
        self.show()

    def cameraToHome(self):
        if self.graph:
            self.zoom = 1
            self.delta = QPoint(0, 0)
            self.start = self.delta
            self.update()

    # TODO, change
    def initLabels(self):
        Point.radius = self.pointRadius
        for point in self.graph.points:
            building = Crossroad(point.idx)
            self.idx_to_building[point.idx] = building
            self.idx_to_widget[point.idx] = Point(point.idx, self)
            self.idx_to_widget[point.idx].setBuilding(building)
        color = self.palette().color(self.backgroundRole()).name()
        for edge in self.graph.edges:
            self.edges_to_weights[edge.idx] = CustomLabel(
                str(edge.weight), self, color)
            self.edges_to_weights[edge.idx].lower()
            self.edges_to_weights[edge.idx].show()

    def deleteLabels(self):
        for widget in self.idx_to_widget.values():
            widget.setParent(None)
        self.idx_to_widget.clear()
        for label in self.edges_to_weights.values():
            label.setParent(None)
        self.edges_to_weights.clear()

    def setWeightLabelsVisible(self, flag):
        self.is_visible_weight = flag
        for label in self.edges_to_weights.values():
            label.setVisible(flag)
        self.update()

    @property
    def pointRadius(self):
        return min(
            int(self.padding * 1.9),
            int(self.graph.shortest_edge / 2 * min(self.height(), self.width()))
        ) // 2

    def setGraph(self, graph):
        self.graph = graph
        self.deleteLabels()
        self.initLabels()
        self.is_visible_weight = True
        self.update()
        
    def setPlayerInfo(self,player_info):
        self.player_info = player_info

    # TODO, maybe later don't recreate new building, if type wasn't be changed
    # TODO create objects outside
    def setBuildings(self, buildings):
        self.buildings = buildings
        for building in self.buildings['posts']:
            idx = building['point_idx']
            if idx in self.idx_to_widget:
                building_type = buildings_to_type[building['type']]
                new_building = building_type.from_dict(building)
                self.idx_to_widget[idx].setBuilding(new_building)
                self.idx_to_building[idx] = new_building

    def paintEvent(self, e):
        if self.graph:
            painter = QPainter()
            painter.begin(self)
            painter.scale(self.zoom, self.zoom)
            painter.translate(self.delta)

            self.delta.setX = self.start.x()
            self.delta.setY = self.start.y()

            # how scale normalized coordinates
            map_x = self.width() - 2 * self.padding
            map_y = self.height() - 2 * self.padding
            pos = self.graph.pos

            # choose suitable font size
            weight_font_size = int(1 / self.graph.biggest_idx_len * self.pointRadius * self.zoom) + 1

            painter.setPen(QPen(Qt.black, 1))
            
            train=self.player_info['trains'][0]
            train_line_idx=train['line_idx']
            train_position=train['position']
                        
            for edge in self.graph.edges:
                p1, p2 = edge.points
                x1, y1, x2, y2 = (
                    pos[p1][0] * map_x + self.padding,
                    pos[p1][1] * map_y + self.padding,
                    pos[p2][0] * map_x + self.padding,
                    pos[p2][1] * map_y + self.padding
                )
                painter.drawLine(x1, y1, x2, y2)
                if edge.idx == train_line_idx:
                                    train_x=x1 + (x2 - x1) * (train_position/10)-self.train_image.size().width()
                                    train_y=y1 + (y2 - y1) * (train_position/10)-self.train_image.size().height()/2
                                
                lbl = self.edges_to_weights[edge.idx]
                lbl.setFontSize(weight_font_size)
                lbl.move(
                    self.zoom * (x1 + (x2 - x1) // 2 + self.delta.x()) - lbl.width() // 2,
                    self.zoom * (y1 + (y2 - y1) // 2 + self.delta.y()) - lbl.height() // 2
                )

            for idx, (x, y) in pos.items():
                x = int(x * map_x) + self.padding
                y = int(y * map_y) + self.padding

                building = self.idx_to_widget[idx]
                building.scale = self.zoom
                building.move(self.zoom * (x + self.delta.x()) - building.width() // 2,
                              self.zoom * (y + self.delta.y()) - building.height() // 2)

            painter.drawImage(QPoint(train_x,train_y),self.train_image)
            painter.end()

    def wheelEvent(self, event):
        self.zoom += event.angleDelta().y() / 2880
        self.update()

    def mousePressEvent(self, QMouseEvent):
        self.start = QMouseEvent.pos() - self.delta
        self.pressing = True

    def mouseMoveEvent(self, QMouseEvent):
        if self.pressing:
            end = QMouseEvent.pos()
            self.delta = (end - self.start)
            self.update()

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False

    def resizeEvent(self, a0) -> None:
        if self.graph:
            Point.radius = self.pointRadius
