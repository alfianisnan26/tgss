import json
import os
import subprocess
import av
import numpy as np
import logging


class FFMPEG:
    def __init__(self, debug=False, max_res=720):
        self.debug = debug
        self.max_res = max_res
        
    def __execute(self, cmd):
        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
        
        for stdout_line in iter(popen.stdout.readline, ""):
            yield stdout_line 
            
        popen.stdout.close()
        return_code = popen.wait()
        
        if return_code:            
            raise subprocess.CalledProcessError(return_code, cmd)
    
    def get_frame_rate(video_path):
        # Run ffprobe command to get video information as JSON
        ffprobe_command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=avg_frame_rate', '-of', 'json', video_path]
        result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Parse JSON output to get frame rate
        if result.returncode == 0:
            info = json.loads(result.stdout)
            frame_rate = eval(info['streams'][0]['avg_frame_rate'])
            return frame_rate
        else:
            raise subprocess.CalledProcessError(result.returncode)

        
    def generate_ss(self, link, dir, frame_skip=1200, frame_rate=30, start_number=0, start_frame=0):
        ffmpeg_cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-i', link,
            '-start_number', str(start_number),
            '-vf', ','.join([
                    f"scale='if(gt(a,1),{self.max_res},-2)':'if(gt(a,1),-2,{self.max_res})'",
                    "drawtext=fontfile=/path/to/font.ttf:fontcolor=white:fontsize=24:text='%{pts\\:hms}':x=10:y=10",
                    f"select='gte(n\\,{start_frame})'",
                    f"select='not(mod(n\\,{frame_skip}))'",
                    f"setpts='N/({frame_rate}*TB)'",
                ]),
            '-q:v', '2',
            os.path.join(dir, "%d.png")
        ]
        
        logging.debug(f"ffmpeg command: {ffmpeg_cmd}")

        
        for stdout in self.__execute(ffmpeg_cmd):
            logging.debug(stdout)
            
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
    
    def calculate_frame_skipped(frame_rate, duration, count_frame=10, available_frame=0):
        total_frames = frame_rate * duration
        actual_interval = total_frames / count_frame
        frame_skipped = actual_interval - 1
        
        return int(frame_skipped), frame_skipped * available_frame
        