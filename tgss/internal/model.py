class Video:
    def __init__(self, id:int=None, file_id:int=None, message_id:int=None, dialog_id:int=None, name:str=None, size:int=None, height:float=None, width:float=None, bitrate:int=None, duration:float=None, status:str=None):
        self.id = id
        self.file_id = file_id
        self.message_id = message_id
        self.dialog_id = dialog_id
        self.name = name
        self.size = size
        self.height = height
        self.width = width
        self.bitrate = bitrate
        self.duration = duration
        self.status = status

class WorkerSession:
    def __init__(self, id:int=None, user_id:int=None, dialog_id:int=None, last_scan_message_id:int=None):
        self.id = id
        self.user_id = user_id
        self.dialog_id = dialog_id
        self.last_scan_message_id = last_scan_message_id

class Filter:
    def __init__(self, sort_by=None, sort_direction='ASC', limit=10, offset=0):
        self.sort_by = sort_by
        self.sort_direction = sort_direction
        self.limit = limit
        self.offset = offset