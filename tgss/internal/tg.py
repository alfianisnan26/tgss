from datetime import datetime
from math import ceil, floor
from mimetypes import guess_type
from telethon.client import TelegramClient
from telethon.types import InputMessagesFilterVideo
import telethon
import asyncio
import logging
from tgss.internal.cache import AsyncCache

class TG:
    __cache_ttl_dialogs = 30 * 60 # 30 minutes
    __cache_ttl_videos = 15 * 60 # 15 minutes
    __cache_ttl_get_my_info = 24 * 60 * 60 # A day
    
    def __gen_cache_key(module, id=None):
        return f"tg:{module}{f":{id}" if id else ""}"
    
    def __init__(self, client:TelegramClient, cache:AsyncCache=AsyncCache()):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client:TelegramClient = client
        self.cache = cache
    
    async def get_available_dialogs(self):
        self.logger.debug(f"get_available_dialogs: Get available dialogs")
         
        return await self.cache.fallback(
            key=TG.__gen_cache_key('dialogs'),
            fallback_func=self.client.get_dialogs,
            ttl=TG.__cache_ttl_dialogs,
        )

    async def get_my_info(self):
        return await self.cache.fallback(
            key=TG.__gen_cache_key('my_info'),
            fallback_func=self.client.get_me,
            ttl=TG.__cache_ttl_get_my_info
        )

    async def get_dialog_by_id(self, id):
        self.logger.debug(f"get_dialog_by_id: Get dialog by id {id}")
        for dialog in await self.get_available_dialogs():
            if dialog.id == id:
                return dialog
            
    async def get_video_message(self, dialog, message_id=None):
        async def get_message():
            return await self.client.get_messages(dialog, ids=message_id, filter=filter)
        
        return await self.cache.fallback(
            key=TG.__gen_cache_key(f"video:id:{message_id}" if message_id else f"video:dialog:{dialog.id}"),
            fallback_func=get_message,
            ttl=TG.__cache_ttl_videos,
        )

    async def get_all_video_message(self, dialog, start_from = None, limit = None):
        self.logger.debug(f"get_all_video_message: Get all video message")
        
        filter = InputMessagesFilterVideo
        
        if limit == 1:
            yield await self.get_video_message(dialog, start_from)

        async for msg in self.client.iter_messages(dialog, min_id=start_from if start_from != None else 0, filter=filter, limit = limit):
            yield msg
            
    def build_file_generator(self, message, file_size, until_bytes, from_bytes, chunk_size=None):     
        until_bytes = min(until_bytes, file_size - 1)

        offset = from_bytes - (from_bytes % chunk_size)
        first_part_cut = from_bytes - offset
        last_part_cut = until_bytes % chunk_size + 1
        
        part_count = ceil(until_bytes / chunk_size) - floor(offset / chunk_size)
        
        async def file_generator():
            current_part = 1
            async for chunk in self.client.iter_download(message, offset=offset, chunk_size=chunk_size, stride=chunk_size, file_size=file_size):
                
                if not chunk:
                    break
                elif part_count == 1:
                    yield chunk[first_part_cut:last_part_cut]
                elif current_part == 1:
                    yield chunk[first_part_cut:]
                elif current_part == part_count:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk

                current_part += 1

                if current_part > part_count:
                    break
        
        return file_generator
    
    def get_file_properties(message: telethon.tl.patched.Message):
        file_name = message.file.name
        file_size = message.file.size or 0
        mime_type = message.file.mime_type
        
        if not file_name:
            attributes = {
                'video': 'mp4',
                'audio': 'mp3',
                'voice': 'ogg',
                'photo': 'jpg',
                'video_note': 'mp4'
            }

            for attribute in attributes:
                media = getattr(message, attribute, None)
                if media:
                    file_type, file_format = attribute, attributes[attribute]
                    break
            
            if not media:
                return None, None, None

            date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f'{file_type}-{date}.{file_format}'
        
        if not mime_type:
            mime_type = guess_type(file_name)[0] or 'application/octet-stream'
        
        return file_name, file_size, mime_type
