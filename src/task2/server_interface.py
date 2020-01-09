from connection import Action, Connector
from database import ServerData
import json


def to_json(obj):
    return json.dumps(obj, separators=(",", ":"))


class ServerInterface:
    opened_connection = None
    server_data = None
        
    def __new__(cls,name=None,players_num=1):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ServerInterface, cls).__new__(cls)
        if name:
            if cls.instance.opened_connection:
                cls.instance.opened_connection.close()
            cls.instance.opened_connection = Connector()
            cls.instance.opened_connection.connect()
            
            if players_num:
                data=to_json({"name": name})
            else:
                data=to_json({"name": name,"players_num":players_num})
                
            cls.instance.opened_connection.send(
                Action.LOGIN, data)
            msg = cls.instance.opened_connection.receive()       
            
            ServerData() #Create an instance and update it in __new__
            
        return cls.instance
    
    def getInstance():
        return 
        
        
    def close_connection(self):
        if self.opened_connection:
            self.opened_connection.send(Action.LOGOUT)
            msg = self.opened_connection.receive()
            self.opened_connection.close()
            return msg

    def get_map_by_level(self, level):
        if self.opened_connection:
            if level in [0, 1, 10]:
                self.opened_connection.send(
                    Action.MAP, to_json({"layer": level}))
                msg = self.opened_connection.receive()
                # msg[0] result check need
                status_result = msg[0]
                return ''.join(msg[1:])

    def __del__(self):
        self.close_connection()
