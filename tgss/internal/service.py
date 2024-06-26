from datetime import datetime
from math import ceil, floor
from mimetypes import guess_type
from tgss.internal.tg import TG
import tgss.internal.utils as utils
import os
import asyncio
from tgss.internal.async_manager import AsyncManager
import logging
from tgss.internal.db import DB
from tgss.internal.model import ConsumerMessage, Video, WorkerSession, Filter
import traceback
from telethon.tl.types import Message
from tgss.internal.cache import AsyncCache
from tgss.internal.ss_manager import ScreenshotManager

class Service:
    def __init__(self, db:DB, tg:TG, sm:ScreenshotManager=None, stream_host='http://localhost:8080', default_count_frame=10, default_frame_rate=30, max_workers=5, ss_export_dir = 'ss', max_retries=3, debug=False, is_partial_retry=True, is_use_last_message_id=True, cache:AsyncCache=AsyncCache(), default_chunk_size=1024*1024, cool_down_retry=10):
        self.cool_down_retry = cool_down_retry
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tg:TG = tg
        self.db:DB = db
        self.sm:ScreenshotManager=sm
        self.stream_endpoint = stream_host + "/stream?message_id={message_id}&dialog_id={dialog_id}"
        self.default_count_frame = default_count_frame
        self.default_frame_rate = default_frame_rate
        self.max_workers = max_workers
        self.ss_export_dir = ss_export_dir
        self.max_retries = max_retries
        self.debug = debug
        self.is_partial_retry = is_partial_retry
        self.is_use_last_message_id = is_use_last_message_id
        self.cache = cache
        self.default_chunk_size = default_chunk_size
    
    async def get_last_video_message(self, dialog_id):
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        if not dialog:
            return None
        
        self.logger.debug(f"get_last_video_message: get dialog by id on last_vide_message: {dialog} [{dialog_id}]")
        
        msg = await self.tg.get_video_message(dialog)
        
        output = {
            'id': msg.id,
            'url': None,
            "peer_id": None,
            "dialog_id": dialog_id,
        }

        
        if hasattr(msg.peer_id, 'channel_id'):
            id = msg.peer_id.channel_id
            url = f"https://t.me/c/{id}/{msg.id}"
            output['url'] = url
            output['peer_id'] = id

        return output
        

    async def get_available_dialogs(self):
        msgs = await self.tg.get_available_dialogs()

        output_msgs = []
        for msg in msgs:
            output = {
                'id': msg.id, 
                "channel_id": None, 
                "user_id": None,
                'name':msg.name,
                'last_message_path': f'/dialogs/last_message?dialog_id={msg.id}',
            } 
        
            if hasattr(msg.dialog.peer,"channel_id"):
                output["channel_id"] = msg.dialog.peer.channel_id
            elif hasattr(msg.dialog.peer,"user_id"):
                output["channel_id"] = msg.dialog.peer.user_id
                
            output_msgs.append(output)
            
        return output_msgs

    async def get_my_info(self):
        return await self.tg.get_my_info()
          
    async def __consumer(self, msg:ConsumerMessage):
            start_time = datetime.now()
            
            self.logger.info(f"__consumer: Start to process {msg}")
            
            video = msg.video
            is_retryable = False
            
            try:
                video.status = Video.status_processing
                self.db.update_video(video)
            except Exception as e:
                self.logger.error(f"__consumer: Failed to upsert video with error: {e} \n {video}")
                return
            
            
            stream_url = self.stream_endpoint.format(
                message_id=video.message_id,
                dialog_id=msg.dialog_id,
                )
            

            if msg.video.bitrate:
                stream_url = f"{stream_url}&chunk_size={msg.video.bitrate}"
                            
            try:
                worker = self.sm.prepare(
                    stream_url,
                    sub_path=str(video.id)
                )
                
                ok, msgs = await worker.run()
            
                
                if ok:
                    self.logger.info(f"__consumer: Worker run success of {video.id}")
                    video.status = Video.status_ready
                    video.set_ocr([msg.get_ocr() for msg in msgs.values()])
                else:
                    self.logger.warning(f"__consumer: Worker run partially success of {video.id}")
                    is_retryable = True
                    video.status = Video.status_partially_ready
                    
                    
            except Exception as e:
                self.logger.error(f"__consumer: Worker run failed of {video.id} with error {e}")
                is_retryable = True
                video.status = Video.status_failed
            
            # close the video clip
            worker.clip.close()
            
            if is_retryable:
                self.logger.warning(f"__consumer: Will retry the message of {video.id} with cooldown of {self.cool_down_retry}")
                await asyncio.sleep(self.cool_down_retry)
                ret = msg.retry()
                if ret:
                    self.logger.warning(f"__consumer: Retry the message of {video.id} with credit of {ret}")
            
            end_time = datetime.now()
            video.processing_time = float((end_time - start_time).total_seconds())
            self.db.update_video(video)
            
    def __producer(self, video:Video, session: WorkerSession, is_update_last_message_id:bool=True):
        
        available_preview = self.get_previews(video.id) 
        available_video = utils.get_first(self.db.get_videos(video.id_only(), filter=Filter(limit=1)))
        if available_video:
            specific_status = available_video.status in [Video.status_failed, Video.status_waiting, Video.status_processing]
            partial_status = ((len(available_preview) < self.default_count_frame) or available_video.status == Video.status_partially_ready) and self.is_partial_retry
            if specific_status or partial_status: 
                video = available_video
                self.logger.warning(f"__producer: Video {video.id} will be re-run to process because of specific_status: {specific_status} [{available_video.status}], partial_status: {partial_status} [{len(available_preview)}]")
            else:
                self.logger.warning(f"__producer: Video skipped: {available_video}\n{available_preview}")
                return None
        
        if is_update_last_message_id:
            session.last_scan_message_id = video.message_id
            
        self.db.update_worker_session(session)
        
        video.status = Video.status_waiting
        video.created_at = datetime.now().isoformat()
        self.db.upsert_video(video)
        
        self.logger.info(f"__producer: Queue video to process: {video.id}")
        return ConsumerMessage(
            video=video,
            available_frame=len(available_preview),
        )
              
    async def start_ss_worker_direct(self, dialog_id, message_id=None, limit=None):
        is_update_last_message_id = True
        
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
            if message_id == None and self.is_use_last_message_id:
                message_id = session.last_scan_message_id
            else:
                is_update_last_message_id = False
                
        self.logger.debug(f"start_ss_worker_direct: Success obtaining session: {session}")

        utils.mkdir_nerr(self.ss_export_dir)
        
        am = AsyncManager(self.__consumer, queue_size=self.max_workers*2, consumer_size=self.max_workers)
        asyncio.create_task(am.run())
        
        self.logger.debug(f"start_ss_worker_direct: Starting to getting messages")

        async for msg in self.tg.get_all_video_message(dialog, start_from=message_id, limit=limit):
            ref = msg
            
            if type(msg) is not Message:
                continue
            
            try:
                video = Video(dialog_id=dialog_id)
                video.from_message(msg)
                
                ref = video
                
                msg = self.__producer(video, session, is_update_last_message_id)
                if msg:
                    msg.retries = self.max_retries
                    msg.retry_func = lambda msg: asyncio.create_task(am.send(msg))
                    msg.dialog_id = dialog_id
                    msg.attempt()
                    
            except Exception as e:
                if self.debug:
                    traceback.print_tb(e.__traceback__)
                self.logger.error(f"start_ss_worker_direct: Failed on produce video queue: {e}\n{ref}")
        
        
        await am.stop()
        self.logger.info("start_ss_worker_direct: Process Finished")
        
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
                    preview_files.append(filename)

            return preview_files
        except Exception as e:
            self.logger.debug(f"get_previews: Preview list of {id} caught an error: {e}")
            return []
        
    def get_video_list(self, ref:Video, filter:Filter):
        if not filter.limit:
            filter.limit = 50
        if not filter.offset:
            filter.offset = 0
        
        return self.db.get_videos(ref, filter)
    
    def get_session_list(self, ref:WorkerSession, filter:Filter):
        if not filter.limit:
            filter.limit = 50
        if not filter.offset:
            filter.offset = 0
            
        return self.db.get_worker_sessions(ref, filter)
    
    def switch_video_favorite(self, video_id, value=None):
        video:Video = utils.get_first(self.db.get_videos(ref=Video(id=video_id), filter=Filter(limit=1)))
        if not video:
            self.logger.debug(f"switch_video_favorite: not found {video_id} {type(video_id)} {value}")
            return None, 404
        
        if value:
            video.flag_favorited = value
        else:
            if video.is_favorited():
                video.flag_favorited = False
            else:
                video.flag_favorited = True
        
        self.db.update_video(new=Video(
            id=video.id,
            flag_favorited=video.flag_favorited
        ))
        
        return video.flag_favorited, None
    
    async def transmit_file(self, dialog_id, message_id, chunk_size, range_header):  
        
        if not chunk_size or chunk_size == 0:
            chunk_size = self.default_chunk_size
            
        if dialog_id == None or message_id == None:
            self.logger.error(f"transmit_file: no dialog_id or message_id [{dialog_id},{message_id}]")
            return None, None, 400
               
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        if dialog == None:
            self.logger.error(f"transmit_file: no dialog [{dialog_id}]")
            return None, None, 404
            
        message = await self.tg.get_video_message(dialog, message_id=message_id)
        if message == None:
            self.logger.error("transmit_file: no message")
            return None, None, 404
    
        
        file_name, file_size, mime_type = TG.get_file_properties(message)
        if file_size == None:
            self.logger.error("transmit_file: no file size")
            return None, None, 400
        
        if file_name == None:
            file_name = "video.mp4"
            mime_type = guess_type(file_name)
            
        
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
        
        
        self.logger.info(f"Service.transmit_file: request of dialog_id: {dialog_id}, message_id: {message_id}, chunk_size: {chunk_size}")

        return self.tg.build_file_generator(message, file_size, until_bytes, from_bytes, chunk_size=chunk_size), headers, 206 if range_header else 200
    
    def get_videos_for_slideshow(self, limit: int, offset: int, is_skip_favorited: bool = False) -> list[Video]:
        statuses = [
            Video.status_downloaded,
            Video.status_downloading,
            Video.status_partially_ready,
            Video.status_ready,
        ]
        return self.db.get_videos_for_slideshow(statuses=statuses, limit=limit, offset=offset, is_skip_favorited=is_skip_favorited)