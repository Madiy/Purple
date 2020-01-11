import sys
import os.path
import server_interface
import json
import networkx as nx
import enum
from PyQt5.QtCore import QThread,QObject, pyqtSignal, QRunnable, pyqtSlot
import database
import time
import traceback
import math
import datetime
from functools import reduce

GoodsTypes = ['product','armor']
    

class BotSignals(QObject):
    update = pyqtSignal()
    move = pyqtSignal(int,int,int)
    turn = pyqtSignal()
    
class TrainTask():
    def __init__(self,train_info):
        self.path = None
        self.path_len = 0
        self.goods_type = None
        self.priority = 1
        self.predicted_value=0
        self.database = database.ServerData()
        self.graph = self.database.getGraph()
        self.train_info = train_info
        self.endpoints = self.database.getBuildings()    
        self.wait_counter = 0
        self.is_complited = False
        self.is_need_to_back = True
        self.old_speed = 0
        self.shortest_paths_to_endpoints = []
        
    def makeTask(self,goods_type,priority=1):
        if self.goods_type == goods_type:
            self.priority = priority
        else:
            self.goods_type = goods_type
            self.priority = priority
            self.getShortestPathForGoods(goods_type)
            for endpoint in self.endpoints['posts']:
                if endpoint['point_idx'] == self.selected_path[-1]:
                    self.predicted_value = endpoint[GoodsTypes[goods_type-1]]
                    if self.predicted_value > self.train_info['goods_capacity']:
                        self.predicted_value=self.train_info['goods_capacity']
            point,edge = self.getTrainPosition(self.train_info['line_idx'],self.train_info['position'],self.train_info['speed'])
            if self.selected_path[0] == point and (self.selected_path[1] == edge.points[0] or self.selected_path[1] == edge.points[1]):
                self.selected_path.remove(self.selected_path[0])
                
    def getTrainPosition(self,line_idx,position,speed):
        edges=self.graph.edges
        for edge in edges:
            if edge.idx==line_idx:
                if position == 0:
                    return edge.points[0],edge
                elif position == edge.weight:
                    return edge.points[1],edge
                else:
                    if speed<0:
                        index = 1
                    else:
                        index = 0
                    return edge.points[index],edge
                
    def getPathByEdges(self,path):
        path_by_edges=[]
        for i in range(len(path)):
            line=(path[i],path[i+1])
            edges=self.graph.edges
            for edge in edges:
                points=edge.points
                if points[0]==line[0]:
                    if points[1]==line[1]:
                        path_by_edges.append([edge.idx,1])
                        return path_by_edges
                        #continue
                elif points[1]==line[0]:
                    if points[0]==line[1]:
                        path_by_edges.append([edge.idx,-1])
                        return path_by_edges
                        #continue        
                        
    def getShortestPathForGoods(self,goods_type):
        goods_type_name = GoodsTypes[goods_type-1]
        able_endpoint = []
        for endpoint in self.endpoints['posts']:
            if endpoint['type'] == goods_type+1:
                able_endpoint.append(endpoint)
        self.getShortestPathByEndpoints(able_endpoint)
        
    def getShortestPathByEndpoints(self,endpoints):
        shortest_paths = []
        self.shortest_paths_to_endpoints = []
        nxgraph = self.graph.nxgraph.copy()
        position=self.train_info['position']
        line_idx=self.train_info['line_idx']
        speed=self.train_info['speed'] 
        self.train_point_idx,_ = self.getTrainPosition(line_idx,position,speed)
        layer1= self.database.getBuildings()
        posts = layer1['posts']
        stations_neaded_to_dodge = []
        neaded_magazine_type = self.goods_type+1
        for post in posts:
            if (post['type'] == 2 and  neaded_magazine_type == 3) or (post['type'] == 3 and  neaded_magazine_type == 2):
                stations_neaded_to_dodge.append(post['point_idx'])
        stations_count = len(stations_neaded_to_dodge)
        for edge in self.graph.edges:
            points = edge.points
            i=0
            while i < stations_count:
                station_idx=stations_neaded_to_dodge[i]
                if points[0] == station_idx or points[1] == station_idx:
                    nxgraph.remove_edge(points[0],points[1])
                    stations_neaded_to_dodge.remove(station_idx)
                    stations_count-=1
                    i-=1
                i+=1
        
        for endpoint  in endpoints:
            path = nx.dijkstra_path(nxgraph,self.train_point_idx,int(endpoint["point_idx"]),"weight")
            path_length=nx.dijkstra_path_length(nxgraph,self.train_point_idx,int(endpoint["point_idx"]),"weight")
            shortest_paths.append([path,path_length])
        self.selected_path = None
        self.selected_path_len = 999999999
        self.shortest_paths_to_endpoints = shortest_paths
        for path,path_len in shortest_paths:
            if self.selected_path_len > path_len:
                self.selected_path_len = path_len
                self.selected_path = path        
            
    def isInNotSameDirection(self,number1,number2,distance):
        if (number1 >= 0 and  distance<0 and number2<=0 ) or (number1 <= 0 and  distance>0 and number2>=0  ) :
            return True
        return False
    
    def isDangerousToRide(self):
        position=self.train_info['position']
        line_idx=self.train_info['line_idx']
        speed=self.train_info['speed'] 
        layer1 = self.database.getBuildings()
        all_trains = layer1['trains']        
        for train in all_trains:
            distance = train['position']-position
            if train['line_idx'] == line_idx and 3 >= math.fabs(distance)  > 0  and self.isInNotSameDirection(speed,train['speed'],distance) :
                if self.wait_counter < 2 and speed != 0:
                    self.wait_counter += 1
                else:
                    self.resetPath(train,line_idx,position,speed)
                return True
        return False

    def isDangerousToRide_new(self):
        position=self.train_info['position']
        line_idx=self.train_info['line_idx']
        speed=self.train_info['speed'] 
        layer1 = self.database.getBuildings()
        all_trains = layer1['trains']
        for train in all_trains:
            if (
                train["line_idx"] == line_idx
                and 0 < math.fabs(train['position'] - position) <= 3
                and self.isDirectionToCrash(speed, position, train["speed"], train["position"])
                and self.resetPath(train,line_idx,position,speed)
            ):
                # distance = math.fabs(train['position'] - position)
                # if 0 < distance <= 3 and self.isDirectionToCrash(speed, position, train["speed"], train["position"]):
                # if self.resetPath(train,line_idx,position,speed):
                self.wait_counter += 1
            

    def isDirectionToCrash(self, v1, p1, v2, p2):
        if p1 > p2:
            v1, v2 = v2, v1
        return v1 > 0 and v2 < 0
            
    def step(self):
        if self.isDangerousToRide():
            return self.train_info['line_idx'],self.train_info['position'],self.train_info['speed']
        else:
            self.rideByPath()
        return self.train_info['line_idx'],self.train_info['position'],self.train_info['speed']
        
    def callToReturn(self,priority=1):
        self.priority=priority
        position=self.train_info['position']
        line_idx=self.train_info['line_idx']
        speed=self.train_info['speed']
        nearest_point,current_position_by_edges = self.getTrainPosition(line_idx,position,speed)
        
        town = self.database.getPlayerInfo()['town']
        self.getShortestPathByEndpoints([town])
        next_point = self.selected_path[0]
        if next_point == nearest_point:
            self.selected_path.remove(next_point)
            next_point = self.selected_path[0]

        
        nearest_edge,speed = self.getNearestEdge(nearest_point)
        
        server_interface.ServerInterface().moveTrain( nearest_edge.idx, speed, self.train_info['idx'])
        self.calculateNextPosition(nearest_edge,nearest_point,speed)
        self.old_speed=speed
    
    def goToNearestPostOrWait(self):
        pass #Just stay and wait cause this effective now ( Yes,yes - it is Kostil )
    
    def rideByPath(self):
        self.wait_counter = 0
        position=self.train_info['position']
        line_idx=self.train_info['line_idx']
        speed=self.train_info['speed']
        nearest_point,current_position_by_edges = self.getTrainPosition(line_idx,position,speed)
        if (nearest_point == current_position_by_edges.points[0] and position == 0) or(nearest_point == current_position_by_edges.points[1] and position == current_position_by_edges.weight):
                if len(self.selected_path)!=0 and self.selected_path[0] == nearest_point:
                    self.selected_path.remove(nearest_point)
                    
                if len(self.selected_path)==0:
                    town = self.database.getPlayerInfo()['town']
                    if town['point_idx']!=nearest_point :
                        if self.train_info['goods'] == self.train_info['goods_capacity'] :
                            self.callToReturn(self.priority)
                        else:
                            self.goToNearestPostOrWait()
                    else :
                        self.is_complited = True
                    return
                nearest_edge,speed = self.getNearestEdge(nearest_point)
                server_interface.ServerInterface().moveTrain( nearest_edge.idx, speed, self.train_info['idx'])
                self.calculateNextPosition(nearest_edge,nearest_point,speed)
                self.old_speed=speed
                return
            
    def calculateNextPosition(self,nearest_edge,nearest_point,speed):
        self.train_info['speed'] = speed                
        old_line_idx = self.train_info['line_idx']
        old_position = self.train_info['position']
        if old_line_idx != nearest_edge.idx:
            # if nearest_edge.points[0]==nearest_point:
            #     self.train_info['position'] = 0
            # else:
            #     self.train_info['position'] = nearest_edge.weight
            self.train_info['line_idx'] = nearest_edge.idx
            return
        # self.train_info['position']+=speed
            
    def getNearestEdge(self,current_point):
        next_point = self.selected_path[0]
            
        edges = self.graph.edges
        for edge in edges:
            points=edge.points
            if points[0]==current_point:
                if points[1]==next_point:
                    return edge,1
            elif points[1]==current_point:
                if points[0]==next_point:
                    return edge,-1
        if self.train_info['goods']!=0:
            self.callToReturn(self.priority)
        else:
            self.makeTask(self.goods_type)   
    
    def resetPath(self,dangerous_train,line_idx,position,speed):
        nearest_backstep_point,current_edge = self.getTrainPosition(line_idx,position,speed*(-1))
        self.train_point_idx = self.getTrainPosition(line_idx,position,speed)
        
        endpoint = self.selected_path[-1]
        nxgraph = self.graph.nxgraph.copy()
        nxgraph.remove_edge(current_edge.points[0],current_edge.points[1])
        self.selected_path = nx.dijkstra_path(nxgraph,nearest_backstep_point,endpoint,"length")
        if self.selected_path[0] != nearest_backstep_point:
            self.selected_path = [nearest_backstep_point] + self.selected_path
        additional_path_len = 0
        if current_edge.points[0] == nearest_backstep_point:
            additional_path_len = position
        else:
            additional_path_len=current_edge.weight-position
        self.selected_path_len=nx.dijkstra_path_length(nxgraph,nearest_backstep_point,endpoint,"length") + additional_path_len

        if not self.selected_path:
            return False

        self.rideByPath()
        return True
        #speed = -1*speed
        #   nearest_edge,speed = self.getNearestEdge(nearest_point)
        #   nearest_point,current_position_by_edges = self.getTrainPosition(line_idx,position,speed)        
        
        #server_interface.ServerInterface().moveTrain( line_idx,speed, self.train_info['idx'])
        #   self.calculateNextPosition(nearest_edge,nearest_point,speed)
        #self.train_info['line_idx']=line_idx
        #self.train_info['position']+=speed
        #self.train_info['speed'] = speed
        #self.old_speed=speed
        #return        
             
        
    
class MyTrain():
    def __init__(self,train_info):
        self.train_info = train_info
        self.task = None
        
    def step(self):
        if self.task and not self.train_info['cooldown']:
            self.train_info['line_idx'],self.train_info['position'],self.train_info['speed'] = self.task.step()
            if self.task.is_complited:
                self.task = None
                
    def updateInfo(self,new_info):
        self.tain_info = new_info
        if self.task:
            self.task.train_info = self.tain_info
       
        
        
        
    
class Bot(QThread):
        
    def __init__(self,si,db,observerable_drawer,parent=None):
        super(Bot,self).__init__()        
        self.graph=None
        self.layer1_dict=None
        self.layer2_dict=None
        self.player_info=None
        self.town = None
        self.town_lines=[]
        self.si=si
        self.path=None
        self.selected_strategy=-1
        self.strategy=None
        self.database = db
        self.drawer = observerable_drawer
        self.signals = BotSignals()
        self.trains = []
        self.able_trains = []
        self.mins = [None, None]
        
    def findAbleTrains(self):
        self.able_trains = []
        for train in self.trains:
            if train.task:
                continue
            self.able_trains.append(train)
        
    
    def searchForExtraTasks(self):
        if  self.town['product'] < self.calculateMinGoodsValue(1):
            self.setExtraTasks(1)
        if  self.town['armor'] < self.calculateMinGoodsValue(2):
            self.setExtraTasks(2)        
    
    def setRegularTasks(self):
        predicted_product = self.town['product'] - self.calculateMinGoodsValue(2)
        predicted_armor = self.town['armor'] - self.calculateMinGoodsValue(1)
        for able_train in self.able_trains:
            if predicted_armor > predicted_product:
                able_train.task = TrainTask(able_train.train_info)  
                able_train.task.makeTask(1,1)                       
                predicted_product+=able_train.task.predicted_value
            else:
                able_train.task = TrainTask(able_train.train_info)
                able_train.task.makeTask(2,1)
                predicted_armor+=able_train.task.predicted_value                
        
    
    def setExtraTasks(self,goods_type):
        for train in self.trains:
            if not train.task:
                train.task = TrainTask(train.train_info)
                train.task.makeTask(goods_type,2)
                return
            if train.task.priority != 2 :
                if not train.train_info['goods']:
                    train.task.makeTask(goods_type,2)
                else:
                    train.task.callToReturn(2)
                return
                
    def calculateMinGoodsValue(self,goods_type):
        if self.mins[goods_type - 1] is None:
            to_full = min(train.train_info["goods_capacity"] for train in self.trains)    
            N = -1
            for point, replenishment in ((post["point_idx"], post["replenishment"]) for post in self.layer2_dict["posts"] if post["type"] == goods_type + 1):
                N = max(
                    N,
                    nx.dijkstra_path_length(
                        self.graph.nxgraph, self.town["point_idx"], point, "weight") * 2 + math.ceil(to_full / replenishment
                    )
                )
            if goods_type == 1:
                self.mins[goods_type - 1] = N * (3 + self.population)
            else:
                self.mins[goods_type - 1] = N * 2
        return self.mins[goods_type - 1]
        
    def updateData(self):  
        self.signals.update.emit()      
        self.updateInfo()
    
    def turn(self):
        self.si.turn() 
        print('5_4:',datetime.datetime.now() - self.begin_loop_time)        
        self.database.update()

        print('5_5:',datetime.datetime.now() - self.begin_loop_time)        
        self.drawer.notify()

        print('5_9:',datetime.datetime.now() - self.begin_loop_time)        
    
    @pyqtSlot()      
    def run(self):
        self.loop()
        
    def loop(self):
        while True:      
            self.begin_loop_time = datetime.datetime.now()
            self.updateData()
            print('1:',datetime.datetime.now() - self.begin_loop_time)
            self.searchForExtraTasks()
            print('2:',datetime.datetime.now() - self.begin_loop_time)
            self.findAbleTrains()
            print('3:',datetime.datetime.now() - self.begin_loop_time)
            self.setRegularTasks()
            print('4:',datetime.datetime.now() - self.begin_loop_time)
            for train in self.trains:
                train.step()
                #for train_info in self.player_info['trains']:
                train_info_idx = train.train_info['idx']
                    #if train_info_idx == train.train_info['idx']:
                layer1 = self.database.getBuildings()
                all_trains = layer1['trains']
                for train_main_data in all_trains:
                    if train_main_data['idx'] == train_info_idx:
                        train_main_data['speed'] = train.train_info['speed']
                        # train_main_data['position'] = train.train_info['position']
                        train_main_data['line_idx'] = train.train_info['line_idx']
                        break
                self.database.setBuildings(layer1)
            print('5:',datetime.datetime.now() - self.begin_loop_time)
            self.turn()  
            print('6:',datetime.datetime.now() - self.begin_loop_time)
    
    def updateInfo(self):
        
        self.graph=self.database.getGraph()
        self.layer1_dict=self.graph
        self.layer2_dict=self.database.getBuildings()
        self.player_info=self.database.getPlayerInfo().copy()
        self.town = self.player_info['town']
        trains_updated = self.player_info['trains'].copy()
        self.armor = self.player_info['town']['armor']
        self.product = self.player_info['town']['product']
        self.population = self.player_info['town']['population']
        print(f'product={self.product},armor={self.armor},population = {self.population}')
        if not self.town_lines:
            edges=self.graph.edges
            point = self.town['point_idx']
            for edge in edges:
                if edge.points[0] == point:
                    self.town_lines.append([edge.idx,0])
                elif edge.points[1] == point:
                    self.town_lines.append([edge.idx,edge.weight])                      
                      
        trains_count=len(self.trains)
        trains_updated_count = len(trains_updated)

        for train in self.trains:
            train_idx=train.train_info['idx']
            for train_updated in trains_updated:
                if train_updated['idx']==train_idx:
                    train.updateInfo(train_updated)
                    train.train_info = train_updated
                    trains_updated.remove(train_updated)
                    break
            print(train.train_info)
        for train_updated in trains_updated:
            self.trains.append(MyTrain(train_updated))

        print("")
          
        #self.tryToUpgrade(armor,product,population)
        
                 
        #for train_updated in trains_updated:
        #    self.trains.append(MyTrain(train_updated))
            
    def tryToUpgrade(self,armor,product,population):
        for train in self.trains:
            train_line =  self.train.train_info['line_idx']
            train_position = self.train.train_info['position']
            for town_line in self.town_lines:
                if train_line == town_line[0] and train_position == town_line[1]:
                    if self.train.train_info['next_level_price']!=None and armor > self.train.train_info['next_level_price'] \
                    and (armor - self.mins[1] > self.train.train_info['next_level_price'] \
                            or (population == 0 or product == 0 )) :
                        self.si.upgrade(trains = [self.train.train_info['idx']])      
                        armor=-self.train.train_info['next_level_price']
        summory_trains_capacity = 0 
        for train in self.trains:
            summory_trains_capacity+=train.train_info['goods_capacity']
            
        if summory_trains_capacity * 1.3 > self.player_info['town']['product_capacity']:
            if self.player_info['town']['next_level_price']!=None and armor > self.player_info['town']['next_level_price'] \
               and (armor - self.mins[1] > self.player_info['town']['next_level_price'] \
                    or (population == 0 or product == 0 )) :
                armor=-self.player_info['town']['next_level_price']
                self.si.upgrade(posts = [self.player_info['town']['idx']])    