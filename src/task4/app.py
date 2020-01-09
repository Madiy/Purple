import sys
import os.path
import json
import networkx as nx

from bot import Bot
from PyQt5.QtWidgets import (QWidget, QApplication, QLabel, QFileDialog,
                             QPushButton, QLineEdit, QGridLayout, QSplitter,
                             QVBoxLayout, QHBoxLayout, QDesktopWidget)
from PyQt5.QtGui import QPainter, QBrush, QPen
from PyQt5.QtCore import Qt, QPoint,QTimer,QThreadPool
from server_interface import ServerInterface
from utils import graph_from_json_string
from utils import buildings_from_json_string
from graph_drawer import GraphDrawer, buildings_to_type
from drawer_utils import CustomLabel
from database import ServerData


class Application(QWidget):
    def __init__(self):
        super().__init__()
        self.database = None
        self.bot=None
        self.threadpool = QThreadPool()
        self.server_interface = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Graph visualization')
        self.resize(1200, 600)
        self.toCenter()

        name_label = QLabel("Enter name:", self)
        name_label.resize(name_label.sizeHint())
        self.nameEdit = QLineEdit("Duran", self)
        self.nameEdit.setObjectName("Nickname")
        self.nameEdit.resize(self.nameEdit.sizeHint())
        self.nameEdit.setToolTip('Select Nickname')

        self.error_label = QLabel("", self)
        self.error_label.resize(name_label.sizeHint())
        self.error_label.hide()
        enter_game_button = QPushButton('Enter', self)
        enter_game_button.resize(enter_game_button.sizeHint())

        home_button = QPushButton('Home', self)
        home_button.resize(home_button.sizeHint())

        weight_visibler_button = QPushButton('Show/Hide weight', self)
        weight_visibler_button.resize(weight_visibler_button.sizeHint())

        load_status_layout = QVBoxLayout()
        load_status_layout.setSpacing(0)
        load_status_layout.addWidget(self.nameEdit)
        load_status_layout.addWidget(self.error_label)

        tools_grid = QGridLayout()
        tools_grid.setHorizontalSpacing(10)
        tools_grid.setVerticalSpacing(5)
        tools_grid.addWidget(name_label, 1, 0)
        tools_grid.addLayout(load_status_layout, 1, 1)
        tools_grid.addWidget(enter_game_button, 1, 2)

        tools_grid.addWidget(home_button, 2, 0)
        tools_grid.addWidget(weight_visibler_button, 2, 2)

        graph_drawer = GraphDrawer()
        graph_drawer.resize(500, 800)
        self.graphWidget = graph_drawer
        verticalLayout = QSplitter()

        verticalLayout.addWidget(self.graphWidget)
        verticalLayout.addWidget(LegendDrawer(self))
        verticalLayout.SetMinimumSize = (800, 670)
        tools_grid.addWidget(verticalLayout, 3, 0, 3, 3)
        tools_grid.SetMinimumSize = (900, 680)
        self.setLayout(tools_grid)

        home_button.clicked.connect(self.graphWidget.cameraToHome)
        enter_game_button.clicked.connect(self.enterTheGame)
        weight_visibler_button.clicked.connect(self.changeWeightVisibility)
        self.show()

    def changeWeightVisibility(self):
        if self.graphWidget.graph:
            self.graphWidget.setWeightLabelsVisible(
                not self.graphWidget.is_visible_weight)

    def toCenter(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def nameValidation(self, name):
        return len(name) > 0

    def enterTheGame(self):
        self.error_label.hide()
        self.name = self.nameEdit.text()
        if not self.nameValidation(self.name):
            return
        self.server_interface = ServerInterface(self.nameEdit.text())
        self.database = ServerData()
        self.updateData()
        self.graphWidget.setGraph(self.database.getGraph())        
        self.bot=Bot(self.server_interface, self.database,self)        
        self.bot.start()
        
    def updateData(self):
        try:
            self.graphWidget.setWeightLabelsVisible(False)
            self.graphWidget.setPlayerInfo(self.database.getPlayerInfo())     
            self.graphWidget.setBuildings(self.database.getBuildings()) 
            self.graphWidget.update()
        except TypeError as error_:
            self.error_label(str(error_))        
        
    def notify(self):
        self.updateData()
          
        
    
    def calculateBotLogic(self):
        graph=self.graphWidget.graph
        if graph:
            if self.bot.makeActions():
                self.timer.setInterval(0)
        else:
            self.timer.setInterval(0)

        

class LegendDrawer(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.points = []
        self.labels = []
        self.main_window = main_window
        self.r = 25
        self.initLabels()
        self.show()

    def paintEvent(self, e):
        painter = QPainter()
        painter.begin(self)
        painter.setPen(QPen(Qt.darkGray, 5))
        painter.drawLine(QPoint(0, 0), QPoint(0, self.size().height()))
        painter.setPen(QPen(Qt.black, 1))
        i = 0
        for building_type in buildings_to_type.values():
            point = self.points[i]
            x = point.x()
            y = point.y()
            color = building_type.color
            painter.setBrush(QBrush(color))
            painter.drawEllipse(x - self.r, y - self.r, 2 * self.r, 2 * self.r)
            i += 1
        painter.end()

    def initLabels(self):
        spacing = 10
        delta_x = self.r + spacing
        delta_y = delta_x + self.r  # if you change delta_x set delta_y = 2*self.r+spacing
        i = 0
        for building_type in buildings_to_type.values():
            y = (i + 1) * delta_y
            self.points.append(QPoint(delta_x, y))
            self.labels.append(
                CustomLabel(
                    building_type.__name__,
                    self))
            self.labels[i].move(2 * delta_x, y - self.labels[i].height() / 2)
            self.labels[i].show()
            i += 1


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Application()
    sys.exit(app.exec_())
