import os
import subprocess
import av
import numpy as np
import logging


class FFMPEG:
    def __init__(self):
        pass

    def generate_ss(self, link, dir, frame_skip=1200, frame_rate=30):
        ffmpeg_cmd = [
            'ffmpeg',
            '-hide_banner',
            '-i', link,
            '-vf', f"select='not(mod(n\\,{frame_skip}))',setpts='N/({frame_rate}*TB)'",
            '-q:v', '2',
            os.path.join(dir, "%d.png")
        ]

        try:
            # Run the command and capture output
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            logging.debug(result.stdout)  # Print standard output if needed
        except subprocess.CalledProcessError as e:
            # Print the error output
            logging.error(f"Error occurred: {e}")
            logging.error(f"Standard output:\n{e.stdout}")
            logging.error(f"Standard error:\n{e.stderr}")
        
    def get_video_info(self, link):
        container = av.open(link)
        stream = container.streams.video[0]
        
        logging.debug(stream)

        # Get video information
        if hasattr(stream, 'rate'):
            frame_rate = stream.rate  # Frame rate as a Fraction
        else:
            frame_rate = 30
        duration = stream.duration * stream.time_base  # Duration in seconds
        width = stream.codec_context.width  # Video width
        height = stream.codec_context.height  # Video height

        video_info = {
            'frame_rate': frame_rate,
            'duration': duration,
            'width': width,
            'height': height
        }
        
        return video_info
    
    def calculate_frame_skipped(frame_rate, duration, count_frame=10):
        total_frames = frame_rate * duration
        ideal_interval = duration / count_frame
        actual_interval = total_frames / count_frame
        frame_skipped = actual_interval - 1
        return int(frame_skipped)
        