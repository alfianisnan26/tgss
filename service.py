from tg import TG
from ffmpeg import FFMPEG
from telethon.types import InputMessagesFilterVideo

class Service:
    def __init__(self, tg:TG, ffmpeg: FFMPEG):
        self.tg:TG = tg

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

    async def start_ss_worker(self, dialog_id, message_id=None, is_single=False):
        async for msg in self.tg.get_all_video_message(dialog_id=dialog_id, start_from=message_id, is_single=is_single):
            print(msg.id) # print video info

        # async for msg in client.iter_messages(dialog, filter=InputMessagesFilterVideo):
        #     message:telethon.tl.patched.Message = msg

        #     new_msg:telethon.tl.patched.Message = await message.forward_to(bot)

        #     attemps = 5
        #     reply = None
        #     sleep_time = 1

        #     while (attemps > 0):
        #         replies = await client.get_messages(bot, filter=InputReplyToMessage(new_msg.id))
        #         if len(replies) > 0:
        #             reply = replies[0]
        #             if reply.id != new_msg.id:
        #                 break

        #         await asyncio.sleep(sleep_time)

        #         print(f"attemps: {attemps}")
        #         attemps -= 1
        #         if attemps <= 0:
        #             return

        #     link = utils.extract_dl_stream_link(reply.message)

        #     frame_rate = 30
        #     module = frame_rate * Config.FRAME_COUNT()

        #     try:
        #         os.mkdir(f'ss/{message.video.id}')
        #     except Exception as e:
        #         print(e)

        #     print(link.download_url)
            
        #     ffmpeg_cmd = [
        #         'ffmpeg',
        #         '-hide_banner',
        #         '-i', link.download_url,
        #         '-vf', f"select='not(mod(n\,{module}))',setpts='N/({frame_rate}*TB)'",
        #         '-q:v', '2',
        #         f'ss/{message.video.id}/%03d.jpg'
        #     ]

        #     subprocess.run(ffmpeg_cmd)
        #     break