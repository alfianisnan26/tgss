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
    
    def DIALOG_ID():
        return int(os.getenv("DIALOG_ID"))

    def FRAME_COUNT():
        return int(os.getenv("FRAME_COUNT"))

    def SESSION():
        return os.getenv("SESSION")

    def SS_EXPORT_DIR():
        return os.getenv("SS_EXPORT_DIR")
    
    def SERVER_PORT():
        return os.getenv("SERVER_PORT")
    
    def STREAM_ENDPOINT():
        return os.getenv("STREAM_ENDPOINT")

    def THREAD_MAX_WORKERS():
        return int(os.getenv("THREAD_MAX_WORKERS"))

    def SQLITE_URL():
        return os.getenv("SQLITE_URL")
    
    def DEBUG():
        return os.getenv("DEBUG") == "true"
    
    def MAX_RETRIES():
        return int(os.getenv("MAX_RETRIES"))
    
    def SS_PARTIAL_RETRY():
        return os.getenv("SS_PARTIAL_RETRY") == "true"
    
    def USE_RELOADER():
        return os.getenv("USE_RELOADER") == "true"
    
    def USE_LAST_MESSAGE_ID():
        return os.getenv("USE_LAST_MESSAGE_ID") == "true"