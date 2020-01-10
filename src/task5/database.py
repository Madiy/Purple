import server_interface 
import json
import utils 

class ServerData(object):
    server_interface = None
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ServerData, cls).__new__(cls)
            cls.instance.server_interface = server_interface.ServerInterface()
            cls.instance.fullUpdate()
        return cls.instance
    
    def fullUpdate(self):
        self.update()
        map_graph_json = self.server_interface.get_map_by_level(0)
        self.graph = utils.graph_from_json_string(map_graph_json)
    
    def update(self):

        objects_map_graph_json = self.server_interface.get_map_by_level(1)
        self.buildings = utils.buildings_from_json_string(objects_map_graph_json)
        self.player_info = json.loads(self.server_interface.getPlayerInfo())
        self.game_info = self.server_interface.gameInfo()        
    
    def getGraph(self):
        return self.graph
    
    def getBuildings(self):
        return self.buildings
    
    def setBuildings(self,buildings):
        self.buildings =  buildings
    
    def getPlayerInfo(self):
        return self.player_info
    
    def getGameInfo(self):
        return self.game_info
    
        