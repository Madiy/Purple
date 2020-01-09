import server_interface 

import utils 

class ServerData(object):
    server_interface = None
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ServerData, cls).__new__(cls)
            cls.instance.server_interface = server_interface.ServerInterface()
            cls.instance.update()
        return cls.instance
    
    def update(self):
        map_graph_json = self.server_interface.get_map_by_level(0)
        objects_map_graph_json = self.server_interface.get_map_by_level(1)
        self.buildings = utils.buildings_from_json_string(objects_map_graph_json)
        self.graph = utils.graph_from_json_string(map_graph_json)    
    
    def getGraph(self):
        return self.graph
    
    def getBuildings(self):
        return self.buildings