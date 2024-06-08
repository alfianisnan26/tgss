from tgss.internal.config import Config
from telethon import TelegramClient
from telethon import functions, types
import sys
import random
import asyncio
import logging

async def login(sub_session):
    async with TelegramClient(Config.SESSION() + "_" + sub_session, Config.API_ID(), Config.API_HASH()) as client:
        ping_id = random.randint(-sys.maxsize - 1, sys.maxsize)
        result = await client(functions.PingRequest(
            ping_id=ping_id
        ))

        logging.info(f"Login: {result.stringify()}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sub_session = sys.argv[1]

        if sub_session == "server":
            pass
        elif sub_session == "worker":
            pass
        else:
            logging.error("Login: Invalid Sub Session")
            exit(-1)

        asyncio.run(login(sub_session))
    else:
        logging.error("Login: Invalid Command")