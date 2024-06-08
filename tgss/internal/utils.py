import re
import os
import aiofiles
from telethon.types import Message

def extract_links(string):
    # Define the regular expression pattern to match URLs
    url_pattern = r'https?://[^\s]+'

    # Find all matches of URLs in the string
    matches = re.findall(url_pattern, string)

    # Return the extracted links
    return matches

class Link:
    def __init__(self):
        self.download_url = ""
        self.watch_url = ""

def extract_dl_stream_link(string):
    links = extract_links(string)

    link = Link()

    for url in links:
        if '/dl/' in url:
            link.download_url = url
        elif '/watch/' in url:
            link.watch_url = url

    return link

def mkdir_nerr(dir):
    try:
        os.mkdir(dir)
    except Exception as e:
        pass

def get_first(arr):
    if len(arr) < 1:
        return None
    
    return arr[0]

def calculate_bitrate(duration_seconds, size_bytes):
    # Convert size to bits
    size_bits = size_bytes * 8
    
    # Calculate bitrate
    bitrate = size_bits / duration_seconds
    
    return bitrate

async def async_rename_file(self, current_file_path, new_file_path):
    try:
        async with aiofiles.os.rename(current_file_path, new_file_path):
            self.logger.debug(f"rename_file: File renamed from {current_file_path} to {new_file_path}")
    except FileNotFoundError:
        self.logger.error("rename_file: File not found.")
    except Exception as e:
        self.logger.error(f"rename_file: An error occurred: {e}")