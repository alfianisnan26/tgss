from datetime import datetime
import logging
from flask import json
import telethon
import copy
from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeVideo
from tgss.internal import utils
class Video:
    status_waiting = 0
    status_processing = 2
    status_ready = 3
    status_downloading = 4
    status_downloaded = 5
    status_removed = 6
    status_failed = 7
    status_partially_ready = 8
    
    def __init__(self, 
                 id:int=None,
                 message_id:int=None, 
                 dialog_id:int=None, 
                 name:str=None,
                 size:int=None, 
                 height:float=None, 
                 width:float=None, 
                 bitrate:int=None, 
                 duration:float=None, 
                 
                 created_at:datetime=None,
                 video_date:datetime=None,
                 
                 status:int=None,
                 flag_favorited:bool=None,
                 ):

        self.id = id
        self.message_id = message_id
        self.dialog_id = dialog_id
        self.name = name
        self.size = size
        self.height = height
        self.width = width
        self.bitrate = bitrate
        self.duration = duration
        self.status = status
        self.created_at = created_at
        self.video_date = video_date
        self.flag_favorited = None if flag_favorited == None else (1 if flag_favorited else 0)
    
    def is_favorited(self):
        return self.flag_favorited == 1

    
    def id_only(self):
        return Video(id=self.id)
    

    def from_message(self, msg:telethon.tl.patched.Message):
        self.message_id = msg.id
        self.id = msg.video.id
        self.size = msg.video.size
        self.video_date = msg.video.date.isoformat()
    
    
        try:
            for _attr in msg.video.attributes:
                attr_type = type(_attr)
                if attr_type == DocumentAttributeVideo:
                    attr:DocumentAttributeVideo = _attr
                    
                    if hasattr(attr, 'duration'): self.duration = attr.duration      
                    if hasattr(attr, 'width'): self.width = attr.width
                    if hasattr(attr, 'height'): self.height = attr.height
                    
                    
                if attr_type == DocumentAttributeFilename:
                    attr:DocumentAttributeFilename = _attr
                    
                    self.name = attr.file_name
        except:
            logging.error("duration attribute not found")
            
        if self.duration != None and self.size != None:
             self.bitrate = int(utils.calculate_bitrate(self.duration, self.size))
            
    def to_dict(self):
        return {
            "id": self.id,
            "message_id": self.message_id,
            "dialog_id": self.dialog_id,
            "name": self.name,
            "size": self.size,
            "height": self.height,
            "width": self.width,
            "bitrate": self.bitrate,
            "duration": self.duration,
            "status": self.status,
            "created_at": self.created_at,
            "video_date": self.video_date,
            "flag_favorited": self.is_favorited()
        }
        
    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)
        
        
class WorkerSession:
    def __init__(self, id:int=None, user_id:int=None, dialog_id:int=None, last_scan_message_id:int=None):
        self.id = id
        self.user_id = user_id
        self.dialog_id = dialog_id
        self.last_scan_message_id = last_scan_message_id

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "dialog_id": self.dialog_id,
            "last_scan_message_id": self.last_scan_message_id,
        }
    
class Filter:
    def __init__(self, sort_by=None, sort_direction='ASC', limit=10, offset=0):
        self.sort_by = sort_by
        self.sort_direction = sort_direction
        self.limit = limit
        self.offset = offset

class ConsumerMessage:
    def __init__(self, video:Video, retry_func=None, available_frame:int=0, retries:int=0) -> None:
        self.video = video
        self.available_frame = available_frame
        self.retries = retries + 1
        self.retry_func = retry_func
    
    def retry(self):
        if self.retries > 0:
            self.retries -= 1
            if self.retry_func:
                self.retry_func(self)
            return self.retries
        
        return None
    
    def attempt(self):self.retry()
    
    def __str__(self) -> str:
        return json.dumps({
                "video": self.video.to_dict(),
                "retries": self.retries,
            }, indent=4)
        
        
       