from tgss.internal.config import Config
from telethon import TelegramClient
import asyncio
import sys
from tgss.internal.tg import TG
from tgss.internal.service import Service
from tgss.internal.ffmpeg import FFMPEG
from tgss.internal.db import DB
from tgss.quart import app
from quart import Quart
import subprocess

ffmpeg = FFMPEG(Config.DEBUG())
db = DB(Config.SQLITE_URL())

async def worker():
    async with TelegramClient(Config.SESSION() + "_worker", Config.API_ID(), Config.API_HASH()) as client:
        tg = TG(client=client)
       
        svc = Service(
            db,
            tg,
            ffmpeg,
            stream_endpoint=Config.STREAM_ENDPOINT(),
            default_count_frame=Config.FRAME_COUNT(),
            max_workers=Config.THREAD_MAX_WORKERS(),
            ss_export_dir=Config.SS_EXPORT_DIR(),
            max_retries=Config.MAX_RETRIES(),
            debug=Config.DEBUG(),
            is_partial_retry=Config.SS_PARTIAL_RETRY(),
            is_use_last_message_id=Config.USE_LAST_MESSAGE_ID()
            )

        

        message_id = None
        limit = None

        if len(sys.argv) > 1:
            message_id = int(sys.argv[1])
        if len(sys.argv) > 2:
            limit = int(sys.argv[2])

        # await svc.start_ss_worker(Config.DIALOG_ID(), Config.BOT_ID(), message_id, limit, Config.SS_EXPORT_DIR())
        await svc.start_ss_worker_direct(Config.DIALOG_ID(), limit=limit, message_id=message_id)

if __name__ == "__main__":
    asyncio.run(worker())