from datetime import datetime
from math import ceil, floor
from mimetypes import guess_type
from telethon.client import TelegramClient
from telethon.types import InputMessagesFilterVideo
import telethon
import asyncio
import logging

class TG:
    def __init__(self, client:TelegramClient):
        self.client:TelegramClient = client
    
    async def get_available_dialogs(self):
        return await self.client.get_dialogs()

    async def get_my_info(self):
        return await self.client.get_me()

    async def get_dialog_by_id(self, id):
        for dialog in await self.get_available_dialogs():
            if dialog.id == id:
                return dialog

    async def get_all_video_message(self, dialog, start_from = None, limit = None) -> telethon.tl.patched.Message:
        filter = InputMessagesFilterVideo

        if start_from != None and limit == 1:
            msg = await self.client.get_messages(dialog, ids=start_from, filter=filter)
            yield msg

        async for msg in self.client.iter_messages(dialog, min_id=start_from if start_from != None else 0, filter=filter, limit = limit):
            yield msg
            
    async def get_first_reply_message(self, dialog, msg:telethon.tl.patched.Message):
        msgs = await self.client.get_messages(dialog, min_id=msg.id)
        for msg in msgs:
            return msg
        
        return None

    async def forward_and_get_reply_msg(self, dialog, msg:telethon.tl.patched.Message, retries = 5, delay = 1):
        fwd_msg = await msg.forward_to(dialog)

        for retry in range(retries):
            msg = await self.get_first_reply_message(dialog, fwd_msg)
            if msg != None:
                return msg

            logging.warn("Retrying:", retry, "For:", fwd_msg.id)
            await asyncio.sleep(delay)
            
    def build_file_generator(self, message, file_size, until_bytes, from_bytes):
        chunk_size = 1024 * 1024
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
