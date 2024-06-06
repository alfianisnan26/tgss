from dotenv import load_dotenv
import os

class Config:
    def init():
        load_dotenv()

    def API_HASH():
        return os.getenv("API_HASH")

    def API_ID():
        return os.getenv("API_ID")

    def PHONE():
        return os.getenv("PHONE")

    def SECRET_KEY():
        return os.getenv("SECRET_KEY")
    
    def FILES_DIRECTORY():
        return os.getenv("FILES_DIRECTORY")

    def DIALOG_ID():
        return int(os.getenv("DIALOG_ID"))

    def BOT_ID():
        return int(os.getenv("BOT_ID"))

    def FRAME_COUNT():
        return int(os.getenv("FRAME_COUNT"))

    def SESSION():
        return os.getenv("SESSION")