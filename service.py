from tg import TG
from ffmpeg import FFMPEG
from telethon.types import InputMessagesFilterVideo
import utils
import os
import utils
class Service:
    def __init__(self, tg:TG, ffmpeg: FFMPEG):
        self.tg:TG = tg
        self.ffmpeg = ffmpeg

    def print_message_info(msg):
        print("ID:", msg.id)

    async def show_last_video_message(self, dialog_id):
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        async for msg in self.tg.get_all_video_message(dialog, limit=1):
            Service.print_message_info(msg)
            break
        

    async def show_available_dialogs(self):
        dialogs = await self.tg.available_dialogs()

        max_id_len = 0

        for dialog in dialogs:
            max_id_len = max(len(str(dialog.id)), max_id_len)

        for dialog in dialogs:
            print(f"{dialog.id:>{max_id_len}} | {dialog.name}")

    async def show_my_info(self):
        info = await self.tg.get_my_info()

        print("id\t\t:", info.id)
        print("first_name\t:", info.first_name)
        print("last_name\t:", info.last_name)
        print("username\t:", info.username)
        print("phone\t\t:", info.phone)

    async def start_ss_worker(self, dialog_id, bot_id, message_id=None, is_single=False, export_path = ''):
        dialog = await self.tg.get_dialog_by_id(dialog_id)
        bot = await self.tg.get_dialog_by_id(bot_id)

        utils.mkdir_nerr(export_path)

        async for msg in self.tg.get_all_video_message(dialog=dialog, start_from=message_id, is_single=is_single):
            rep_msg = await self.tg.forward_and_get_reply_msg(dialog=bot, msg=msg)
            if rep_msg == None:
                print("Failed to get replied forwarded message")
                return
            
            links = utils.extract_dl_stream_link(rep_msg.message)

            path = os.path.join(export_path, str(msg.id))

            utils.mkdir_nerr(path)
            
            self.ffmpeg.generate_ss(links.download_url, path)