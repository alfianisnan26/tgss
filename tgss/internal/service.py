from datetime import datetime
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
from tgss.internal.model import ConsumerMessage, Video, WorkerSession, Filter
import traceback
from telethon.tl.types import Message

class Service:
    def __init__(self, db:DB, tg:TG, ffmpeg: FFMPEG, stream_endpoint='http://localhost:8080/stream/{message_id}', default_count_frame=10, default_frame_rate=30, max_workers=5, ss_export_dir = 'ss'):
        self.tg:TG = tg
        self.db:DB = db
        self.ffmpeg = ffmpeg
        self.stream_endpoint = stream_endpoint
        self.default_count_frame = default_count_frame
        self.default_frame_rate = default_frame_rate
        self.max_workers = max_workers
        self.ss_export_dir = ss_export_dir
    

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
        me = await self.get_my_info()

        session = WorkerSession(user_id=me.id, dialog_id=dialog_id)
        available_session = utils.get_first(self.db.get_worker_sessions(session, Filter(
            limit=1,
        )))

        if not available_session:
            self.db.insert_worker_session(session)
        else:
            session = available_session
            if message_id == None:
                message_id = session.last_scan_message_id

        utils.mkdir_nerr(export_path)

        def process_message(msg:ConsumerMessage):
            video = msg.video
            
            logging.info(f"Start to process {video}")

            try:
                video.status = Video.status_processing
                self.db.update_video(video.id_only())
            except Exception as e:
                logging.error(f"Failed to upsert video with error: {e} \n {video}")
                return
            
            path = os.path.join(export_path, str(video.id))
            utils.mkdir_nerr(path)
            
            stream_url = self.stream_endpoint.format(message_id=video.message_id)
            
            try:
                frame_rate = FFMPEG.get_frame_rate(stream_url)
            except:
                frame_rate = self.default_count_frame
            
            frame_skip, start_frame = FFMPEG.calculate_frame_skipped(frame_rate, duration=video.duration, count_frame=self.default_count_frame, available_frame=msg.available_frame)
            logging.debug(f"frame analyzed | frame_rate: {frame_rate} | frame_skip: {frame_skip} | start_frame: {start_frame}")
            
            try:
                
                self.ffmpeg.generate_ss(stream_url, path, frame_skip=frame_skip,frame_rate=frame_rate, start_frame=start_frame, start_number=msg.available_frame)
                
                video.status = Video.status_ready
                
                logging.info(f"Process video {video.id} completed!")
            except Exception as e:
                video.status = Video.status_failed
                
                logging.error(f"Process video {video.id} failed :(\n{e}")
            
            self.db.update_video(video.id_only())
            
            
        
        tm = ThreadManager(process_message, queue_size=self.max_workers*2, consumer_size=self.max_workers)
        tm.run()

        async for msg in self.tg.get_all_video_message(dialog, start_from=message_id, limit=limit):
            if type(msg) is not Message:
                continue
            
            try:
                video = Video(dialog_id=dialog_id)
                video.from_message(msg)
                
                available_preview = self.get_previews(video.id) 
                available_video = utils.get_first(self.db.get_videos(video.id_only(), filter=Filter(limit=1)))
                if available_video:
                    if available_video.status in [Video.status_failed, Video.status_unknown, Video.status_processing] or len(available_preview or []) < self.default_count_frame: 
                        video = available_video
                    else:
                        logging.warn(f"Video skipped: {available_video}\n{available_preview}")
                        continue
                
                session.last_scan_message_id = video.message_id
                self.db.update_worker_session(session)
                
                video.status = Video.status_waiting
                video.created_at = datetime.now().isoformat()
                self.db.upsert_video(video)
                
                logging.info(f"Queue video to process: {video.id}")
                tm.send(ConsumerMessage(
                    video=video,
                    available_frame=len(available_preview),
                ))
                
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                logging.error(f"Failed on produce video queue: {e}\n{msg}\n{video}")
            

        tm.stop()
        logging.info("Process Finished")
        
    def get_previews(self, id) -> list[str]:
        try:
            ss_export_dir = self.ss_export_dir  # Get the SS export directory from the config

            # Construct the directory path for the previews
            previews_dir = os.path.join(ss_export_dir, str(id))

            # Initialize an empty list to store the file paths
            preview_files = []

            # Iterate over the files in the directory
            for filename in os.listdir(previews_dir):
                # Check if the file has the prefix "file" and ends with ".png"
                if filename.endswith(".png"):
                    # Construct the full file path and append it to the list
                    preview_files.append(os.path.join(previews_dir, filename))

            return preview_files
        except Exception as e:
            logging.warn(f"Preview list of {id} caught an error: {e}")
            return []
    
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