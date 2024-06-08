import asyncio
import logging
from asyncio import Queue, QueueEmpty
import traceback

class AsyncManager:
    def __init__(self, consumer_func, queue_size=5, consumer_size=3):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.queue_size = queue_size
        self.consumer_size = consumer_size
        self.consumer_func = consumer_func

    async def consumer(self, pipeline:Queue, stop_event, consumer_id, consumer_func):
        self.logger.debug(f"consumer: Consumer [{consumer_id}] is running...")
        while not stop_event.is_set() or not pipeline.empty():
            try:
                message = pipeline.get_nowait()
                if message is not None:
                    self.logger.debug(f"consumer: Consumer [{consumer_id}] start to process the queue")
                    await consumer_func(message)
                    self.logger.debug(f"consumer: Consumer [{consumer_id}] finished processing the queue")
            except asyncio.CancelledError:
                self.logger.debug(f"consumer: Consumer [{consumer_id}] is breaking caused by cancelled")
                break
            except QueueEmpty:
                self.logger.debug(f"consumer: Consumer [{consumer_id}] ignore empty queue")
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                self.logger.error(f"consumer: Consumer [{consumer_id}] has error: {e}")
                
            await asyncio.sleep(1)

        self.logger.debug(f"consumer: Consumer [{consumer_id}] received event. Exiting")

    async def run(self):
        self.pipeline = Queue(maxsize=self.queue_size)
        self.stop_event = asyncio.Event()

        self.consumers = []
        for i in range(self.consumer_size):  
            consumer_task = asyncio.create_task(
                self.consumer(self.pipeline, self.stop_event, i, self.consumer_func)
            )
            self.consumers.append(consumer_task)

        self.logger.debug("run: waiting all coroutine finished")
        await asyncio.gather(*self.consumers)

    async def send(self, msg):
        await self.pipeline.put(msg)

    async def stop(self):
        self.logger.debug("stop: Asyncio set event to stop")
        self.stop_event.set()
        
        # wait for all consumers_task stopped
        
        self.logger.debug("stop: Waiting for all consumers to finish...")
        await asyncio.gather(*self.consumers, return_exceptions=True)
        self.logger.debug("stop: All consumers finished. AsyncManager stopped.")

