import os
import subprocess
class FFMPEG:
    def __init__(self):
        pass

    def generate_ss(self, link, dir, frame_rate=30, frame_skip=1200):
        ffmpeg_cmd = [
            'ffmpeg',
            '-hide_banner',
            '-i', link,
            '-vf', f"select='not(mod(n\,{frame_skip}))',setpts='N/({frame_rate}*TB)'",
            '-q:v', '2',
            os.path.join(dir, "%d.png")
        ]

        subprocess.run(ffmpeg_cmd)