from math import ceil, floor
from tgss.internal.tg import TG
from tgss.internal.ffmpeg import FFMPEG
from telethon.types import InputMessagesFilterVideo
import tgss.internal.utils as utils
import os
from PIL import Image
import asyncio
import concurrent.futures
from tgss.internal.thread import ThreadManager
import logging
from tgss.internal.db import DB

class Service:
    def __init__(self, db:DB, tg:TG, ffmpeg: FFMPEG, stream_endpoint='http://localhost:8080/stream/{message_id}', default_count_frame=10, default_frame_rate=30, max_workers=5):
        self.tg:TG = tg
        self.db:DB = db
        self.ffmpeg = ffmpeg
        self.stream_endpoint = stream_endpoint
        self.default_count_frame = default_count_frame
        self.default_frame_rate = default_frame_rate
        self.max_workers = max_workers
    

    def print_message_info(msg):
        logging.info("ID:", msg.id)

    async def get_last_video_message(self, dialog_id):
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        async for msg in self.tg.get_all_video_message(dialog, limit=1):

            output = {
                'id': msg.id,
                'url': None,
                "peer_id": None,
                "dialog_id": dialog_id,
                "dialog_name": dialog.name,
            }

            
            if hasattr(msg.peer_id, 'channel_id'):
                id = msg.peer_id.channel_id
                url = f"https://t.me/c/{id}/{msg.id}"
                output['url'] = url
                output['peer_id'] = id

            return output
        

    async def get_available_dialogs(self):
        return await self.tg.get_available_dialogs()

    async def get_my_info(self):
        return await self.tg.get_my_info()
    

    async def start_ss_worker(self, dialog_id, bot_id, message_id=None, limit=None, export_path = ''):
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        bot = await self.tg.get_dialog_by_id(bot_id)

        utils.mkdir_nerr(export_path)

        async for msg in self.tg.get_all_video_message(dialog=dialog, start_from=message_id, limit=limit):
            rep_msg = await self.tg.forward_and_get_reply_msg(dialog=bot, msg=msg)
            if rep_msg == None:
                logging.error("Failed to get replied forwarded message")
                return
            
            links = utils.extract_dl_stream_link(rep_msg.message)

            path = os.path.join(export_path, str(msg.id))

            utils.mkdir_nerr(path)
            
            self.ffmpeg.generate_ss(links.download_url, path)
            
    async def start_ss_worker_direct(self, dialog_id, message_id=None, limit=None, export_path=''):
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        utils.mkdir_nerr(export_path)
        
        def process_message(msg):
            path = os.path.join(export_path, str(msg.id))
            utils.mkdir_nerr(path)
            stream_url = self.stream_endpoint.format(message_id=msg.id)
            duration = TG.get_video_duration_from_message(msg)
            frame_skip = FFMPEG.calculate_frame_skipped(self.default_frame_rate, duration=duration, count_frame=self.default_count_frame)
            self.ffmpeg.generate_ss(stream_url, path, frame_skip=frame_skip)
        
        
        tm = ThreadManager(process_message, queue_size=self.max_workers*2, consumer_size=self.max_workers)
        tm.run()

        async for msg in self.tg.get_all_video_message(dialog, start_from=message_id, limit=limit):
            tm.send(msg)

        tm.stop()
        logging.info("Process Finished")
    
    async def transmit_file(self, dialog_id, message_id, range_header):
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        message = None
        async for msg in self.tg.get_all_video_message(dialog, message_id, limit=1):
            message = msg
            break
        
        if message == None:
            return None, None, 404
    
        
        file_name, file_size, mime_type = TG.get_file_properties(message)
        if file_name == None:
            return None, None, 400
        
        if range_header:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        else:
            from_bytes = 0
            until_bytes = file_size - 1
            
        if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
            return None, None, 416

        headers = {
                "Content-Type": f"{mime_type}",
                "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
                "Content-Length": str(until_bytes - from_bytes + 1),
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "Accept-Ranges": "bytes",
            }

        return self.tg.build_file_generator(message, file_size, until_bytes, from_bytes), headers, 206 if range_header else 200