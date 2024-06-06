from telethon.client import TelegramClient
from telethon.types import InputMessagesFilterVideo
import telethon

class TG:
    def __init__(self, client:TelegramClient):
        self.client:TelegramClient = client

    async def available_dialogs(self):
        return await self.client.get_dialogs()

    async def get_my_info(self):
        return await self.client.get_me()

    async def get_dialog_by_id(self, id):
        for dialog in await self.available_dialogs():
            if dialog.id == id:
                return dialog

    async def get_all_video_message(self, dialog, start_from = None, is_single = False) -> telethon.tl.patched.Message:
        filter = InputMessagesFilterVideo

        if start_from != None and is_single:
            msg = await self.client.get_messages(dialog, ids=start_from, filter=filter)
            yield msg

        async for msg in self.client.iter_messages(dialog, min_id=start_from if start_from != None else 0, filter=filter):
            yield msg

    async def forward_and_get_reply_msg(self, dialog, msg:telethon.tl.patched.Message, retries = 5, delay = 1):
        pass