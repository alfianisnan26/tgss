from config import Config
from telethon import TelegramClient
import asyncio
import telethon
import utils
import subprocess
import os
import sys
from tg import TG
from service import Service
from ffmpeg import FFMPEG

ffmpeg = FFMPEG()

async def main(app:str):
    async with TelegramClient(Config.SESSION(), Config.API_ID(), Config.API_HASH()) as client:
        tg = TG(client=client)
        svc = Service(tg, ffmpeg)

        if app == "dialogs":
            await svc.show_available_dialogs()
        elif app == "me":
            await svc.show_my_info()
        else:
            message_id = None
            is_single = False

            if len(sys.argv) > 2:
                message_id = int(sys.argv[2])
            if len(sys.argv) > 3:
                is_single = sys.argv[3] == "single"

            await svc.start_ss_worker(Config.DIALOG_ID(), message_id, is_single)

if __name__ == "__main__":
    Config.init()

    app:str = None # default

    if len(sys.argv) > 1:
        app = sys.argv[1]

    asyncio.run(main(app))
