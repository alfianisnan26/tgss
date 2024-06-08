import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from moviepy.editor import VideoFileClip
import imageio

class IntervalMessage:
    def __init__(self, i, interval, lock) -> None:
        self.__i = i
        self.__interval = interval
        self.__ok = False
        self.__lock = lock
        
    async def set_ok(self):
        async with self.__lock:
            self.__ok = True
        
    def is_ok(self):
        return self.__ok
    
    def get_index(self):
        return self.__i
    
    def get_interval(self):
        return self.__interval
    
class ScreenshotWorker:
    def __init__(self, manager, clip, count=10, sub_path=None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.manager = manager
        self.clip = clip
        
        if sub_path:
            self.output_dir = os.path.join(manager.output_dir, sub_path)
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                self.logger.debug(f"__init__: Created output directory: {self.output_dir}")
        else:
            self.output_dir = manager.output_dir
        
        self.__lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor(max_workers=manager.max_workers)
        
        self.intervals = {i: IntervalMessage(i,int(i * self.clip.duration / (count + 1)), self.__lock) for i in range(1, count + 1)}    
    
    async def run(self):
        for i in range(self.manager.max_retries):
            self.logger.info(f"generate: Starting to spawn process {i}...")
            
            await self.__run_workers()
            
            self.logger.debug(f'generate: finish to run_workers')
            if len(self.__not_ready_intervals()) == 0:
                break
            
            self.logger.warning(f"generate: Will retry the process. retries: {self.manager.max_retries-i}")
            
            
        not_ready = self.__not_ready_intervals()
        self.logger.info(f"generate: Process finished. Success {len(self.intervals) - len(not_ready)} out of {len(self.intervals)}")
        return len(not_ready) == 0
    
    def __not_ready_intervals(self):
        return [self.intervals[i] for i in self.intervals if not self.intervals[i].is_ok()]
    
    async def __run_workers(self):
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(self.executor, self.__wrap_process, self.clip, interval)
            for interval in self.__not_ready_intervals()
        ]
        await asyncio.gather(*tasks)

    def __wrap_process(self, clip, interval):
        asyncio.run(self.__process(clip, interval))

    async def __process(self, clip, interval_msg:IntervalMessage):
        interval = interval_msg.get_interval()
        index = interval_msg.get_index()
        
        try:
            hours, remainder = divmod(interval, 3600)
            minutes, seconds = divmod(remainder, 60)
            timestamp = "{:03}_{:02}:{:02}:{:02f}".format(index, int(hours), int(minutes), seconds)
            
            output_path = os.path.join(self.output_dir, f"{timestamp}.png")
            
            if not os.path.exists(output_path):
                self.logger.debug(f"__process: Extracting frame at time interval: {interval}")
                
                frame = clip.get_frame(interval)
                imageio.imwrite(output_path, frame)
                self.logger.info(f"__process: Screenshot saved at: {output_path}")
            else:
                self.logger.warning(f"__process: Screenshot already available at: {output_path}")
            
            await interval_msg.set_ok()
                
        except Exception as e:
            self.logger.error(f"__process: Error occurred while saving screenshot: {str(e)}")

class ScreenshotManager:
    def __init__(self, output_dir, max_workers=4, max_retries=3, cache=None, clip_cache_ttl=120, default_count=10):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.output_dir = output_dir
        self.cache = cache
        self.clip_cache_ttl = clip_cache_ttl
        self.default_count = default_count
        
        if not os.path.exists(self.output_dir):
            os.makedirs(output_dir)
            self.logger.debug(f"__init__: Created output directory: {output_dir}")
        
        
    def prepare(self, url, count=None, sub_path=None):
        self.logger.info("generate: Starting to generate preview screenshots...")
        if not count:
            count = self.default_count
            
        return ScreenshotWorker(
            clip=VideoFileClip(url),
            manager=self,
            count=count,
            sub_path=sub_path,
        )

if __name__ == "__main__":
    # Set up logging configuration
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    
    # Example usage
    video_file_path = "http://localhost:8080/stream?message_id=18957&dialog_id=-1001960028823&chunk_size=1056784"  # Replace with your video file path
    output_directory = "ss"
    number_of_screenshots = 10
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        logging.info(f"Created output directory: {output_directory}")
    
    sm = ScreenshotManager(output_dir=output_directory).prepare(url=video_file_path,count=number_of_screenshots,sub_path='sample')
    # Run the coroutine in the event loop
    asyncio.run(sm.run())
