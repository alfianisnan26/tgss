from tgss.internal.config import Config
from telethon import TelegramClient
import asyncio
import sys
from tgss.internal.tg import TG
from tgss.internal.service import Service
from tgss.internal.ffmpeg import FFMPEG

ffmpeg = FFMPEG()

async def main():
    async with TelegramClient(Config.SESSION() + "_worker", Config.API_ID(), Config.API_HASH()) as client:
        tg = TG(client=client)
        svc = Service(tg, ffmpeg, stream_endpoint=Config.STREAM_ENDPOINT(), default_count_frame=Config.FRAME_COUNT())

        message_id = None
        is_single = False

        if len(sys.argv) > 1:
            message_id = int(sys.argv[1])
        if len(sys.argv) > 2:
            limit = int(sys.argv[2])

        # await svc.start_ss_worker(Config.DIALOG_ID(), Config.BOT_ID(), message_id, limit, Config.SS_EXPORT_DIR())
        await svc.start_ss_worker_direct(Config.DIALOG_ID(), limit=limit, export_path=Config.SS_EXPORT_DIR())

if __name__ == "__main__":
    Config.init()

    asyncio.run(main())